# -*- coding: utf-8 -*-
import os
import google.generativeai as genai
import io
import httpx
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 初始化对话历史
chat_history = []

def clear_memory():
    """清除对话记忆的函数。"""
    global chat_history
    chat_history = []  # 清空对话历史
    print("对话记忆已清除。")

def upload_to_gemini(path, mime_type=None):
    """上传文件到Gemini。"""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"已上传文件 '{file.display_name}' 到: {file.uri}")
    return file

def get_local_image():
    """获取本地图片路径"""
    while True:
        image_path = input("请输入图片路径（输入'q'退出）: ")
        if image_path.lower() == 'q':
            return None
        if os.path.exists(image_path):
            return image_path
        print("文件不存在，请重新输入。")

def analyze_image(image_path, image_type="病理"):
    """处理图片分析的核心逻辑"""
    try:
        # 设置模型参数
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # 根据图片类型设置提示词
        if image_type == "病理":
            prompt = """你现在是一位专业的病理科医生，请仔细分析这张病理图片：
            1. 这是什么类型的病理切片？
            2. 有什么异常或特殊的发现？
            3. 这些发现对诊断有什么意义？
            4. 需要注意哪些重要的细节？
            请用通俗易懂的语言解释。"""
        else:
            prompt = "请分析这张医学图像，指出关键的发现和可能的诊断意义。"

        # 上传并分析图片
        image = upload_to_gemini(image_path)
        response = model.generate_content([prompt, image])
        print("\n分析结果：")
        print(response.text)
        
    except Exception as e:
        print(f"分析过程中出现错误：{str(e)}")

def show_menu():
    """显示主菜单"""
    print("\n=== 医疗报告智能解读助手 ===")
    print("1. 病理图片分析")
    print("2. 清除对话历史")
    print("3. 退出程序")
    return input("请选择功能（输入数字）: ")

def handle_image_analysis():
    """处理图片解读功能"""
    while True:
        image_path = get_local_image()
        if not image_path:
            break
        
        print("\n选择图片类型：")
        print("1. 病理切片")
        print("2. 其他医学图像")
        choice = input("请选择（默认为病理切片）: ")
        
        image_type = "病理" if choice != "2" else "其他"
        analyze_image(image_path, image_type)

def main():
    """主程序"""
    while True:
        choice = show_menu()
        
        if choice == "1":
            handle_image_analysis()
        elif choice == "2":
            clear_memory()
        elif choice == "3":
            print("感谢使用！再见！")
            break
        else:
            print("无效的选择，请重试。")

if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("GEMINI_API_KEY"):
        print("错误：未找到 GEMINI_API_KEY 环境变量")
        print("请确保已经创建 .env 文件并设置了正确的 API 密钥")
        exit(1)
    
    main()
