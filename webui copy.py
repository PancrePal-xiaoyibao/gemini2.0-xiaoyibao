import gradio as gr
import os
import logging
import sys
from datetime import datetime
from config import config
import main
from mange_filelist import list_all_files, delete_file, clear_all_cache
import google.generativeai as genai
from dotenv import load_dotenv

# 设置日志文件路径
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"webui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# 配置根日志记录器
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# 创建文件处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logger.info(f"日志文件路径：{log_file}")

# 加载环境变量
load_dotenv()

def check_proxy(proxy_url: str, timeout: int = 5) -> bool:
    """检查代理是否可用"""
    try:
        import requests
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        response = requests.get('https://api.gradio.app', 
                              proxies=proxies, 
                              timeout=timeout,
                              verify=False)  # 临时禁用SSL验证
        return response.status_code == 200
    except Exception as e:
        logger.error(f"代理检查失败: {e}")
        return False

def setup_gemini():
    """初始化Gemini配置"""
    try:
        # 获取API密钥
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.error("未找到GEMINI_API_KEY环境变量")
            raise ValueError("请设置GEMINI_API_KEY环境变量")

        # 获取代理配置
        proxy_config = config.get_proxy_config()
        if proxy_config.get('enabled'):
            proxy_url = proxy_config['http']
            if check_proxy(proxy_url):
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
                logger.info("已启用代理配置")
            else:
                logger.warning("代理服务器不可用，将使用直接连接")
                os.environ.pop('HTTP_PROXY', None)
                os.environ.pop('HTTPS_PROXY', None)

        # 配置Gemini
        genai.configure(api_key=api_key)
        
        # 获取模型配置
        model_config = config.get_model_config()
        
        # 初始化聊天模型
        chat_config = model_config.get('chat', {})
        chat_model = genai.GenerativeModel(
            model_name=chat_config.get('model_name', 'gemini-2.0-flash-exp'),
            generation_config=genai.GenerationConfig(
                temperature=chat_config.get('temperature', 0.7),
                max_output_tokens=chat_config.get('max_output_tokens', 2048),
            )
        )
        
        # 初始化视觉模型
        vision_config = model_config.get('vision', {})
        vision_model = genai.GenerativeModel(
            model_name=vision_config.get('model_name', 'gemini-2.0-flash-exp'),
            generation_config=genai.GenerationConfig(
                temperature=vision_config.get('temperature', 0.7),
                max_output_tokens=vision_config.get('max_output_tokens', 2048),
            )
        )
        
        logger.info("Gemini模型初始化成功")
        return chat_model, vision_model
        
    except Exception as e:
        logger.error(f"Gemini初始化失败: {e}")
        raise

# 初始化配置
ui_config = config.get_ui_config()
prompts = config.get_prompts()

try:
    # 初始化Gemini模型
    chat_model, vision_model = setup_gemini()
except Exception as e:
    logger.error(f"系统初始化失败: {e}")
    raise

# 对话历史
chat_history = []

def chat(message: str, history: list) -> tuple[str, list]:
    """处理普通对话"""
    try:
        logger.debug(f"chat函数被调用")
        logger.info(f"开始处理普通对话，输入消息：{message}")
        logger.debug(f"当前历史记录：{history}")
        
        if not message:
            logger.warning("输入消息为空")
            return "", history
        
        # 初始化历史记录
        if history is None:
            logger.debug("初始化历史记录")
            history = []
            
        model_config = config.get_model_config()['chat']
        logger.info(f"使用模型配置：{model_config}")
        
        # 使用初始化好的聊天模型
        response = chat_model.generate_content(prompts['chat'] + "\n\n用户问题：" + message)
        response_text = response.text
        logger.info(f"收到回复：{response_text}")
        
        # 更新对话历史
        history.append((message, response_text))
        logger.debug(f"更新后的历史记录：{history}")
        return "", history
        
    except Exception as e:
        error_msg = f"处理对话时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if history is None:
            history = []
        history.append((message, error_msg))
        return "", history

def analyze_image_chat(image, image_type: str, message: str, history: list) -> list:
    """处理图片分析和对话"""
    try:
        logger.debug(f"analyze_image_chat函数被调用")
        logger.info(f"开始处理图片分析，类型：{image_type}，消息：{message}")
        
        if image is None:
            logger.warning("未上传图片")
            history.append({"role": "assistant", "content": "请先上传图片"})
            return history
        
        # 保存图片到临时文件
        temp_path = os.path.join(config.get_upload_path(), "temp_image.jpg")
        image.save(temp_path)
        logger.info(f"图片已保存到：{temp_path}")
        
        # 获取图片类型的配置
        image_config = config.get_image_type_prompt(image_type)
        if image_config is None:
            error_msg = f"不支持的图片类型: {image_type}"
            logger.error(error_msg)
            history.append({"role": "assistant", "content": error_msg})
            return history
        
        # 使用初始化好的视觉模型
        # 上传图片到Gemini
        image_file = main.upload_to_gemini(temp_path, mime_type=image_config['mime_type'])
        logger.info("图片已上传到Gemini")
        
        # 分析图片
        if not message:
            # 首次分析图片，使用特定类型的提示词
            prompt = image_config['system_prompt']
            logger.info(f"使用图片分析提示词：{prompt}")
            response = vision_model.generate_content([image_file, prompt])
        else:
            # 继续对话，保持图片上下文
            logger.info(f"继续对话，消息：{message}")
            response = vision_model.generate_content([image_file, message])
        
        response_text = response.text
        logger.info(f"收到回复：{response_text}")
        
        if not message:
            history.append({"role": "assistant", "content": response_text})
        else:
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response_text})
        return history
            
    except Exception as e:
        error_msg = f"分析图片时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        history.append({"role": "assistant", "content": error_msg})
        return history

def analyze_report_chat(pdf_file, message: str, history: list) -> list:
    """处理报告分析和对话"""
    try:
        logger.debug(f"analyze_report_chat函数被调用")
        logger.info(f"开始处理报告分析，消息：{message}")
        
        if pdf_file is None and not message:
            logger.warning("未上传报告")
            history.append({"role": "assistant", "content": "请先上传报告"})
            return history
            
        model_config = config.get_model_config()['pdf']
        logger.info(f"使用模型配置：{model_config}")
        
        model = genai.GenerativeModel(
            model_config['model_name'],
            generation_config=genai.types.GenerationConfig(
                temperature=model_config['temperature'],
                max_output_tokens=model_config['max_output_tokens']
            )
        )
            
        if pdf_file is not None:
            # 保存PDF到临时文件
            temp_path = os.path.join(config.get_upload_path(), "temp_report.pdf")
            with open(temp_path, "wb") as f:
                f.write(pdf_file.read())
            logger.info(f"报告已保存到：{temp_path}")
            
            # 分析报告
            cache = main.upload_pdf_and_cache(temp_path)
            result = main.generate_content_from_cache(cache, prompts['report_analysis'])
            logger.info(f"收到回复：{result}")
            history.append({"role": "assistant", "content": result})
        else:
            # 继续对话
            logger.info(f"继续对话，消息：{message}")
            response = model.generate_content(message)
            response_text = response.text
            logger.info(f"收到回复：{response_text}")
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response_text})
        return history
        
    except Exception as e:
        error_msg = f"分析报告时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        history.append({"role": "assistant", "content": error_msg})
        return history

def manage_files_ui() -> str:
    """文件管理界面"""
    try:
        logger.debug(f"manage_files_ui函数被调用")
        logger.info("开始获取文件列表")
        
        files = list_all_files()
        if not files:
            logger.info("文件列表为空")
            return "当前没有已上传的文件"
            
        result = "=== 已上传文件列表 ===\n"
        for i, (file_type, file) in enumerate(files, 1):
            result += f"{i}. 文件名: {file.display_name}\n"
            result += f"   文件URI: {file.uri}\n"
            result += f"   类型: {file_type}\n"
            result += "-" * 50 + "\n"
        logger.info("文件列表获取成功")
        return result
        
    except Exception as e:
        error_msg = f"获取文件列表时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

def delete_file_ui(file_name: str) -> str:
    """删除文件"""
    try:
        logger.debug(f"delete_file_ui函数被调用")
        logger.info(f"开始删除文件：{file_name}")
        
        files = list_all_files()
        for file_type, file in files:
            if file.display_name == file_name:
                if delete_file(file_type, file):
                    logger.info(f"删除成功：{file_name}")
                    return f"成功删除文件: {file_name}"
                else:
                    logger.error(f"删除失败：{file_name}")
                    return f"删除文件失败: {file_name}"
        logger.info(f"文件不存在：{file_name}")
        return f"未找到文件: {file_name}"
        
    except Exception as e:
        error_msg = f"删除文件时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

def clear_cache_ui() -> str:
    """清理缓存"""
    try:
        logger.debug(f"clear_cache_ui函数被调用")
        logger.info("开始清理缓存")
        
        if clear_all_cache():
            logger.info("清理缓存成功")
            return "成功清理所有缓存"
        else:
            logger.error("清理缓存失败")
            return "清理缓存失败"
        
    except Exception as e:
        error_msg = f"清理缓存时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

# 创建Gradio界面
with gr.Blocks(css=f"body {{ background-color: {ui_config['theme_color']}; }}") as demo:
    gr.Markdown(f"# {ui_config['title']}")
    
    with gr.Tab(ui_config["chat_title"]):
        chat_interface = gr.ChatInterface(
            fn=chat,
            title="医疗问答助手",
            description="我是一位专业的医生，可以用通俗易懂的方式解答医学相关的问题",
            examples=["什么是高血压？", "糖尿病的早期症状有哪些？"]
        )

    with gr.Tab(ui_config["image_title"]):
        with gr.Row():
            with gr.Column():
                image_input = gr.Image(type="filepath", label="上传图片")
                image_type = gr.Dropdown(
                    choices=list(prompts["analysis_prompts"].keys()),
                    value=list(prompts["analysis_prompts"].keys())[0],
                    label="图片类型"
                )
                image_msg = gr.Textbox(
                    placeholder="请输入您的问题（可选）", 
                    label="问题",
                    lines=2
                )
                with gr.Row():
                    image_submit = gr.Button("分析图片")
                    image_chat_submit = gr.Button("发送消息")
            
            image_chatbot = gr.Chatbot(
                value=[], 
                label="分析结果与对话",
                height=600,
                show_label=True
            )
        
        # 绑定事件
        def analyze_image_wrapper(image, image_type, message, history):
            if not image:
                return history + [{"role": "assistant", "content": "请先上传图片"}]
            return analyze_image_chat(image, image_type, message, history)
        
        image_submit.click(
            analyze_image_wrapper,
            inputs=[image_input, image_type, image_msg, image_chatbot],
            outputs=[image_chatbot]
        )
        image_chat_submit.click(
            analyze_image_wrapper,
            inputs=[image_input, image_type, image_msg, image_chatbot],
            outputs=[image_chatbot]
        )

    with gr.Tab(ui_config['report_title']):
        with gr.Row():
            with gr.Column():
                pdf_input = gr.File(
                    label="上传医疗报告",
                    file_types=[".pdf"],
                    type="filepath"
                )
            with gr.Column():
                report_chatbot = gr.Chatbot(
                    label="报告分析与对话",
                    type="messages",
                    height=400,
                    show_label=True
                )
                report_msg = gr.Textbox(
                    label="输入问题",
                    placeholder="请输入您的问题...",
                    lines=2
                )
                with gr.Row():
                    report_submit = gr.Button("分析报告")
                    report_clear = gr.Button("清除对话")
        
        # 绑定事件
        report_submit.click(
            analyze_report_chat,
            inputs=[pdf_input, report_msg, report_chatbot],
            outputs=[report_chatbot]
        )
        report_msg.submit(
            analyze_report_chat,
            inputs=[pdf_input, report_msg, report_chatbot],
            outputs=[report_chatbot]
        )
        report_clear.click(lambda: None, None, report_chatbot, queue=False)
        
    with gr.Tab(ui_config['file_title']):
        with gr.Column():
            file_list = gr.Textbox(
                label="文件列表",
                value=manage_files_ui(),
                lines=10,
                max_lines=20
            )
            with gr.Row():
                file_name = gr.Textbox(
                    label="文件名",
                    placeholder="输入要删除的文件名"
                )
                delete_btn = gr.Button("删除文件")
                refresh_btn = gr.Button("刷新列表")
                clear_cache_btn = gr.Button("清理缓存")
            
            delete_btn.click(delete_file_ui, [file_name], [file_list])
            refresh_btn.click(manage_files_ui, None, [file_list])
            clear_cache_btn.click(clear_cache_ui, None, [file_list])
            
    # 创建必要的目录
    os.makedirs(config.get_upload_path(), exist_ok=True)
    os.makedirs(config.get_cache_path(), exist_ok=True)
    
    logger.info("Gradio Web UI 初始化完成")
    
    # 启动Gradio应用
    demo.launch(server_port=7070, server_name="0.0.0.0", share=True)

if __name__ == "__main__":
    # 确保上传和缓存目录存在
    os.makedirs(config.get_upload_path(), exist_ok=True)
    os.makedirs(config.get_cache_path(), exist_ok=True)
