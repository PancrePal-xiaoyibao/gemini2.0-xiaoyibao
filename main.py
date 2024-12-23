# -*- coding: utf-8 -*-
import os
import google.generativeai as genai
import io
import httpx
from dotenv import load_dotenv
import logging

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

# 初始化配置
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
if not os.getenv("GEMINI_API_KEY"):
    print("错误：未找到 GEMINI_API_KEY 环境变量")
    print("请确保已经创建 .env 文件并设置了正确的 API 密钥")
    exit(1)
    
# 初始化对话历史
chat_history = []

def clear_memory():
    """清除对话记忆的函数。"""
    global chat_history
    chat_history = []  # 清空对话历史
    print("对话记忆已清除。")

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def upload_pdf_and_cache(pdf_url):
    """上传PDF文档并创建缓存，并生成概要总结。"""
    logging.info("开始上传PDF文档...")
    logging.info(f"PDF文档URL: {pdf_url}")
    try:
        # 检查是否是 URL 还是本地文件路径
        if pdf_url.startswith(('http://', 'https://')):
            # 从 URL 上传
            doc_data = io.BytesIO(httpx.get(pdf_url).content)
            # 使用 upload_file 上传 PDF
            document = genai.upload_file(doc_data, mime_type='application/pdf')
        else:
            # 从本地文件上传
            with open(pdf_url, 'rb') as f:
                document = genai.upload_file(f, mime_type='application/pdf')

        # 修正顺序：先创建模型，再获取模型名称
        model = genai.GenerativeModel("gemini-1.5-flash-002")  # PDF处理专用模型
        model_name = model.model_name

        # 生成概要总结
        summary_response = model.generate_content(["请用中文给我这份PDF文件的概要总结（不超过500字），结构清晰，条理分明，重点提示和结论优先呈现。", document])
        print("概要总结：")
        print(summary_response.text)

        # 创建缓存内容对象
        cache = genai.caching.CachedContent.create(
            model=model_name,
            system_instruction="You are an expert analyzing transcripts.",
            contents=[document],
        )

        logging.info("PDF文档上传成功，并生成缓存。")
        return cache, summary_response.text  # 返回缓存和概要总结
    except Exception as e:
        print(f"上传PDF文档时出错: {e}")
        return None, None

def generate_content_from_cache(cache, prompt):
    """从缓存生成内容。"""
    model = genai.GenerativeModel.from_cached_content(cache)
    response = model.generate_content(prompt)
    return response

def show_menu():
    """显示主菜单"""
    print("\n=== 医疗报告解读系统 ===")
    print("1. 图片解读")
    print("2. 检验报告解读")
    print("3. 问答对话")
    print("4. 退出")
    return input("请选择功能（1-4）：").strip()

def get_local_image():
    """获取本地图片路径"""
    while True:
        path = input("请输入本地报告的图片路径（输入'取消'返回）：").strip()
        if path.lower() == '取消':
            return None
        if os.path.exists(path):
            return path
        print("文件不存在，请重新输入")

def analyze_image(image_path, image_type="病理"):
    """处理图片分析的核心逻辑"""
    logging.info("开始处理图片...")
    logging.info(f"图片路径: {image_path}")
    # 添加文件类型检查
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    file_extension = os.path.splitext(image_path)[1].lower()
    if file_extension not in allowed_extensions:
        return {"success": False, "error": "不支持的文件格式，请使用 JPG 或 PNG 格式的图片"}
        
    analysis_prompts = {
        "病理": {
            "system_prompt": "你是一位专业的病理科医生，请仔细分析该病理切片图像：\n1. 组织结构特征\n2. 细胞形态特点\n3. 可能的病理诊断\n4. 需要注意的特殊发现",
            "mime_type": "image/jpeg"
        },
        "CT": {
            "system_prompt": "你是一位专业的放射科医生，请仔细分析该CT图像：\n1. 扫描部位和范围\n2. 密度特征分析\n3. 病变位置和大小\n4. 与周围组织的关系\n5. 可能的诊断意见",
            "mime_type": "image/jpeg"
        },
        "MRI": {
            "system_prompt": "你是一位专业的放射科医生，请仔细分析该MRI图像：\n1. 扫描序列和部位\n2. 信号特征分析\n3. 病变范围和特点\n4. 与周围组织的关系\n5. 可能的诊断意见",
            "mime_type": "image/jpeg"
        },
         "血液": {
            "system_prompt": "你是一位专业的血液科医生，请仔细分析该血液检测报告：\n1. 血常规指标异常\n2. 凝血指标异常\n3. 淋巴细胞，中性粒细胞异常\n4. 凝血指标异常\n5. 可能的诊断意见",
            "mime_type": "image/jpeg"
        },
         "肝功能": {
            "system_prompt": "你是一位专业的医学医生，请仔细分析该肝功能检测报告：\n1. 谷丙转氨酶\n2. 谷草转氨酶\n3. 谷丙转氨酶\n4. 谷草转氨酶\n5. 可能的诊断意见",
            "mime_type": "image/jpeg"
        }           
    }

    try:
        logging.info("开始分析图片...")
        prompt_config = analysis_prompts.get(image_type, analysis_prompts["病理"])
        image_file = upload_to_gemini(image_path, mime_type=prompt_config["mime_type"])
        
        analysis_message = {
            "role": "user",
            "parts": [
                image_file,
                prompt_config["system_prompt"]
            ]
        }
        
        response = chat_session.send_message(analysis_message)
        logging.info(f"分析结果: {response.text}")
        return {"success": True, "analysis": response.text}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_report_analysis():
    """处理PDF报告解读功能"""
    logging.info("开始进行报告解读...")
    print("\n=== 报告解读 ===")
    report_types = ["基因检测报告", "病理组化报告","其它PDF文档"]
    print("支持的报告类型：")
    for i, t in enumerate(report_types, 1):
        print(f"{i}. {t}")
    
    type_choice = input(f"请选择报告类型（1-{len(report_types)}）：").strip()
    if not type_choice.isdigit() or int(type_choice) not in range(1, len(report_types) + 1):
        print("无效的选择")
        return
    
    upload_choice = input("请选择上传方式（1. 输入URL 2. 本地文件上传）：").strip()
    
    pdf_url = None
    if upload_choice == "1":
        pdf_url = input("请输入PDF报告的URL（确保包含http://或https://）：").strip()
        if not pdf_url.startswith(('http://', 'https://')):
            print("无效的URL，请确保以http://或https://开头")
            return
    elif upload_choice == "2":
        pdf_path = input("请输入本地PDF文件的路径：").strip()
        if not os.path.exists(pdf_path):
            print("文件不存在，请检查路径")
            return
        # 这里可以直接使用本地文件路径
        pdf_url = pdf_path
    else:
        print("无效的选择")
        return
    
    print("\n正在处理PDF报告...")
    cache, summary = upload_pdf_and_cache(pdf_url)
    if cache:
        while True:
            print("\n=== 报告解读对话 ===")
            print("1. 查看报告概要")
            print("2. 提出具体问题")
            print("3. 返回主菜单")
            
            chat_choice = input("请选择（1-3）：").strip()
            
            if chat_choice == "1":
                print("\n报告概要：")
                print(summary)
            elif chat_choice == "2":
                question = input("\n请输入您的具体问题：").strip()
                if question.lower() in ['退出', 'exit', 'quit']:
                    break
                result = generate_content_from_cache(cache, question)
                print("\n回答：")
                print(result.text)
            elif chat_choice == "3":
                break
            else:
                print("无效的选择，请重新输入")

            # 提示用户是否继续对话
            continue_dialogue = input("是否继续围绕报告解析内容进行对话？（y/n 或 是/否）：").strip().lower()
            if continue_dialogue in ['否', 'n']:  # 支持输入否或n
                break
    else:
        print("报告处理失败")

def handle_image_analysis():
    """处理图片解读功能"""
    print("\n=== 图片解读 ===")
    image_types = ["病理", "CT", "MRI", "血液", "肝功能"]
    print("支持的报告类型：")
    for i, t in enumerate(image_types, 1):
        print(f"{i}. {t}")
    
    type_choice = input("请选择报告类型（1-5）：").strip()
    if not type_choice.isdigit() or int(type_choice) not in range(1, len(image_types) + 1):
        print("无效的选择")
        return
    
    image_type = image_types[int(type_choice) - 1]
    image_path = get_local_image()
    if not image_path:
        return
    
    print(f"\n正在分析{image_type}图片...")
    result = analyze_image(image_path, image_type)
    if result["success"]:
        print("\n分析结果：")
        print(result["analysis"])
        while True:
            continue_dialogue = input("是否继续围绕图片解析内容进行对话？（y/n 或 是/否）：").strip().lower()
            if continue_dialogue in ['否', 'n']:  # 支持输入否或n
                break
            elif continue_dialogue in ['是', 'y']:
                user_question = input("请输入您的问题：").strip()
                response = chat_session.send_message(user_question)
                print("\n回答：")
                print(response.text)
            else:
                print("无效的选择，请输入'是'或'否'。")
    else:
        print(f"分析失败：{result['error']}")

def main():
    """主程序"""
    while True:
        choice = show_menu()
        if choice == "1":
            handle_image_analysis()
        elif choice == "2":
            handle_report_analysis()
        elif choice == "3":
            user_input = input("\n请输入您的问题：")
            response = chat_session.send_message(f"{prompt}\n{user_input}")
            print("\n回答：")
            print(response.text)
        elif choice == "4":
            print("感谢使用，再见！")
            break
        else:
            print("无效的选择，请重新输入")

if __name__ == "__main__":
    # 清理缓存
    # genai.caching.clear_all()  # 清除所有缓存
    
    prompt = "你是一位专业的胰腺癌医生，可以解读报告，以通俗易懂的方式，帮助病人解释复杂的属于，提示关键信息，以及未来和治疗相关的内容提示.如果告有术语，请先解释下这个术语和指标的定义，意义，以及和病情相关的提示。"
    
    # 创建全局模型配置和实例
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    
    # 初始化全局模型
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",  # 主程序使用的模型
        generation_config=generation_config,
    )

    # 定义初始聊天历史
    initial_history = []
    
    # 初始化聊天会话
    chat_session = model.start_chat(history=initial_history)
    logging.info("聊天会话已启动。")
    
    # 运行主程序
    main()