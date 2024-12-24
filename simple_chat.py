import gradio as gr
import os
import logging
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 检查 API 密钥
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    logger.error("未找到 GEMINI_API_KEY 环境变量，请设置 .env 文件")
    sys.exit(1)
else:
    logger.info("成功读取 GEMINI_API_KEY")

# 配置 Gemini
genai.configure(api_key=api_key)

# 初始化模型和会话
try:
    model = genai.GenerativeModel(model_name="gemini-2.0-flash-experimental")
    chat_session = model.start_chat(history=[])
    logger.info("模型和会话初始化成功")
except Exception as e:
    logger.error(f"模型初始化失败: {e}", exc_info=True)
    sys.exit(1)

def chat(message: str, history: list) -> list:
    """处理对话"""
    try:
        logger.info(f"收到用户消息: {message}")
        if not message:
            return history
        response = chat_session.send_message(message)
        if not response or not response.text:
            logger.error("模型没有返回响应")
            history.append({"role":"assistant", "content":"模型没有返回响应，请重试。"})
            return history
        response_text = response.text
        logger.info(f"模型回复: {response_text}")
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_text})
        return history
    except Exception as e:
        logger.error(f"对话过程中发生错误: {e}", exc_info=True)
        history.append({"role":"assistant", "content":f"对话过程中发生错误：{e}，请查看后台日志"})
        return history

# 创建 Gradio 界面
if __name__ == "__main__":
    with gr.Blocks() as demo:
        gr.ChatInterface(
            fn=chat,
            title="Gemini 2.0 Flash Experimental Chat",
            description="这是一个使用 gemini-2.0-flash-experimental 模型的简单对话界面"
        )
    demo.launch(server_name="127.0.0.1", server_port=5880, share=False)