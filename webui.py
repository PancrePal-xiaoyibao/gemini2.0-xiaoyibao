import gradio as gr
import os
from config import config
import main
from mange_filelist import list_all_files, delete_file, clear_all_cache
import google.generativeai as genai

# 初始化配置
ui_config = config.get_ui_config()
system_config = config.get_system_config()
prompts = config.get_prompts()

# 对话历史
chat_history = []

def chat(message: str, history: list) -> str:
    """处理普通对话"""
    try:
        model_config = config.get_model_config()['chat']
        model = genai.GenerativeModel(
            model_config['model_name'],
            generation_config=genai.types.GenerationConfig(
                temperature=model_config['temperature'],
                max_output_tokens=model_config['max_output_tokens']
            )
        )
        
        # 添加系统提示词
        prompt = prompts['chat'] + "\n\n用户问题：" + message
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"发生错误: {str(e)}"

def analyze_image_chat(image, image_type: str, message: str, history: list) -> str:
    """处理图片分析和对话"""
    try:
        if image is None:
            return "请先上传图片"
        
        # 保存图片到临时文件
        temp_path = os.path.join(config.get_upload_path(), "temp_image.jpg")
        image.save(temp_path)
        
        # 获取图片类型的配置
        image_config = config.get_image_type_prompt(image_type)
        if image_config is None:
            return f"不支持的图片类型: {image_type}"
        
        # 获取模型配置
        model_config = config.get_model_config()['vision']
        model = genai.GenerativeModel(
            model_config['model_name'],
            generation_config=genai.types.GenerationConfig(
                temperature=model_config['temperature'],
                max_output_tokens=model_config['max_output_tokens']
            )
        )
        
        # 上传图片到Gemini
        image_file = main.upload_to_gemini(temp_path, mime_type=image_config['mime_type'])
        
        # 分析图片
        if not message:
            # 首次分析图片，使用特定类型的提示词
            prompt = image_config['system_prompt']
            response = model.generate_content([image_file, prompt])
        else:
            # 继续对话，保持图片上下文
            response = model.generate_content([image_file, message])
            
        return response.text
    except Exception as e:
        return f"分析图片时发生错误: {str(e)}"

def analyze_report_chat(pdf_file, message: str, history: list) -> str:
    """处理报告分析和对话"""
    try:
        if pdf_file is None and not message:
            return "请先上传PDF报告"
            
        model_config = config.get_model_config()['pdf']
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
            
            # 分析报告
            cache = main.upload_pdf_and_cache(temp_path)
            result = main.generate_content_from_cache(cache, prompts['report_analysis'])
        else:
            # 继续对话
            response = model.generate_content(message)
            result = response.text
            
        return result
    except Exception as e:
        return f"分析报告时发生错误: {str(e)}"

def manage_files_ui() -> str:
    """文件管理界面"""
    try:
        files = list_all_files()
        if not files:
            return "当前没有已上传的文件"
            
        result = "=== 已上传文件列表 ===\n"
        for i, (file_type, file) in enumerate(files, 1):
            result += f"{i}. 文件名: {file.display_name}\n"
            result += f"   文件URI: {file.uri}\n"
            result += f"   类型: {file_type}\n"
            result += "-" * 50 + "\n"
        return result
    except Exception as e:
        return f"获取文件列表时发生错误: {str(e)}"

def delete_file_ui(file_name: str) -> str:
    """删除文件"""
    try:
        files = list_all_files()
        for file_type, file in files:
            if file.display_name == file_name:
                if delete_file(file_type, file):
                    return f"成功删除文件: {file_name}"
                else:
                    return f"删除文件失败: {file_name}"
        return f"未找到文件: {file_name}"
    except Exception as e:
        return f"删除文件时发生错误: {str(e)}"

def clear_cache_ui() -> str:
    """清理缓存"""
    try:
        if clear_all_cache():
            return "成功清理所有缓存"
        else:
            return "清理缓存失败"
    except Exception as e:
        return f"清理缓存时发生错误: {str(e)}"

# 创建Gradio界面
with gr.Blocks(css=f"body {{ background-color: {ui_config['theme_color']}; }}") as demo:
    gr.Markdown(f"# {ui_config['title']}")
    
    with gr.Tab(ui_config['chat_title']):
        chatbot = gr.Chatbot(type="messages")
        chat_msg = gr.Textbox(label="输入消息")
        chat_clear = gr.Button("清除对话")
        
        chat_msg.submit(chat, [chat_msg, chatbot], [chatbot])
        chat_clear.click(lambda: None, None, chatbot, queue=False)
        
    with gr.Tab(ui_config['image_title']):
        with gr.Row():
            with gr.Column():
                image_input = gr.Image(type="pil", label="上传医学图片")
                image_type = gr.Radio(
                    choices=list(config.get_image_types().keys()),
                    value="病理",
                    label="选择图片类型",
                    info="请选择要分析的医学图片或报告类型"
                )
            with gr.Column():
                image_chatbot = gr.Chatbot(label="分析结果与对话", type="messages")
                image_msg = gr.Textbox(label="输入问题", placeholder="请输入您的问题...")
                with gr.Row():
                    image_submit = gr.Button("分析图片")
                    image_clear = gr.Button("清除对话")
        
        # 绑定事件
        image_submit.click(
            analyze_image_chat,
            inputs=[image_input, image_type, image_msg, image_chatbot],
            outputs=[image_chatbot]
        )
        image_msg.submit(
            analyze_image_chat,
            inputs=[image_input, image_type, image_msg, image_chatbot],
            outputs=[image_chatbot]
        )
        image_clear.click(lambda: None, None, image_chatbot, queue=False)
        
    with gr.Tab(ui_config['report_title']):
        with gr.Row():
            with gr.Column():
                pdf_input = gr.File(
                    label="上传医疗报告",
                    file_types=[".pdf"],
                    type="filepath"
                )
            with gr.Column():
                report_chatbot = gr.Chatbot(label="报告分析与对话", type="messages")
                report_msg = gr.Textbox(label="输入问题", placeholder="请输入您的问题...")
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
        list_files_btn = gr.Button("列出文件")
        file_list = gr.Textbox(label="文件列表", interactive=False)
        delete_input = gr.Textbox(label="输入要删除的文件名")
        delete_btn = gr.Button("删除文件")
        clear_cache_btn = gr.Button("清理缓存")
        
        list_files_btn.click(manage_files_ui, outputs=[file_list])
        delete_btn.click(delete_file_ui, [delete_input], [file_list])
        clear_cache_btn.click(clear_cache_ui, outputs=[file_list])

if __name__ == "__main__":
    # 确保上传和缓存目录存在
    os.makedirs(config.get_upload_path(), exist_ok=True)
    os.makedirs(config.get_cache_path(), exist_ok=True)
    
    # 启动Gradio应用
    demo.launch(server_port=7070, server_name="0.0.0.0", share=True)
