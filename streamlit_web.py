import streamlit as st
import os
import logging
from datetime import datetime, timedelta
from PIL import Image
import google.generativeai as genai
from config import config
import main
from mange_filelist import list_all_files, delete_file, clear_all_cache

# 设置页面配置
st.set_page_config(
    page_title=config.get_ui_config().get('title', '小胰宝Gemini2.0功能测试Demo医疗助手'),
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 从config获取logger
logger = logging.getLogger(__name__)

def check_password():
    """检查用户密码"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
        
    if not st.session_state.password_correct:
        # 首次访问或密码错误时显示输入框
        st.markdown("""
        <style>
            .stAlert {
                display: none !important;
            }
            .css-1p05t8e {
                padding-top: 2rem;
            }
            .stButton > button {
                background-color: #9C27B0 !important;
                color: white !important;
            }
            .stButton > button:hover {
                background-color: #7B1FA2 !important;
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("### 登录系统")
            st.markdown("欢迎使用小胰宝医疗助手，请输入密码登录。")
            password = st.text_input("请输入密码", type="password", key="password")
            
            if password:
                if st.button("提交", key="submit_button", use_container_width=True) or password:
                    if password == config.get_login_password():
                        st.session_state.password_correct = True
                        st.session_state.password_expiry = datetime.now() + timedelta(days=config.get_password_expiry_days())
                        st.rerun()
                    else:
                        st.error("密码错误，请重试！")
        return False
    
    # 检查密码是否过期
    if hasattr(st.session_state, 'password_expiry'):
        if datetime.now() > st.session_state.password_expiry:
            st.session_state.password_correct = False
            return False
    
    return True

# 检查密码
if not check_password():
    st.stop()

# 初始化模型的函数
def setup_gemini():
    """初始化Gemini配置"""
    try:
        # 获取API密钥
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.error("未找到GEMINI_API_KEY环境变量")
            raise ValueError("请设置GEMINI_API_KEY环境变量")

        # 配置Gemini
        genai.configure(api_key=api_key)
        
        # 获取模型配置
        model_config = config.get_model_config()
        
        # 初始化聊天模型
        chat_config = model_config.get('chat', {}) # 获取聊天模型配置
        chat_model = genai.GenerativeModel(  # 创建聊天模型
            model_name=chat_config.get('model_name', 'gemini-2.0-flash-exp'),  # 也可以使用gemini-pro模型
            generation_config=genai.GenerationConfig(
                temperature=chat_config.get('temperature', 0.7),
                max_output_tokens=chat_config.get('max_output_tokens', 2048),
            )
        )
        logger.info("聊天模型初始化成功")
        
        # 初始化视觉模型
        vision_config = model_config.get('vision', {})
        vision_model = genai.GenerativeModel(
            model_name=vision_config.get('model_name', 'gemini-pro-vision'),  # 使用gemini-pro-vision模型
            generation_config=genai.GenerationConfig(
                temperature=vision_config.get('temperature', 0.7),
                max_output_tokens=vision_config.get('max_output_tokens', 2048),
            )
        )
        logger.info("视觉模型初始化成功")
        
        return chat_model, vision_model
        
    except Exception as e:
        error_msg = f"初始化Gemini时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)

# 初始化模型的函数
def initialize_models():
    if 'chat_model' not in st.session_state:
        chat_model, vision_model = setup_gemini()  # 调用之前定义的模型初始化函数
        st.session_state.chat_model = chat_model
        st.session_state.vision_model = vision_model
        st.session_state.chat_session = chat_model.start_chat(history=[])

# 在应用启动时调用初始化函数
initialize_models()

# 从配置中获取 UI 设置
ui_config = config.get_ui_config()
prompts = config.get_prompts()

# --- 定义功能函数 ---

def chat_function(message: str, history: list) -> list:
    """处理普通对话"""
    try:
        logger.info(f"开始处理普通对话，输入消息：{message}")
        if not message:
            return history
            
        if not st.session_state.chat_session:
            error_msg = "聊天会话未初始化"
            logger.error(error_msg)
            history.append({"role": "assistant", "content": error_msg})
            return history

        response = st.session_state.chat_session.send_message(prompts['chat'] + "\n\n用户问题：" + message)

        if not response or not response.text:
            logger.error("模型没有返回响应")
            history.append({"role":"assistant", "content":"模型没有返回响应，请重试。"})
            return history
            
        response_text = response.text
        logger.info(f"收到回复：{response_text}")
        history.append({"role":"user", "content":message})
        history.append({"role":"assistant", "content":response_text})
        return history
    except Exception as e:
        error_msg = f"处理对话时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        history.append({"role":"assistant", "content":f"对话过程中发生错误：{e}，请查看后台日志"})
        return history

def analyze_image_chat(image, image_file, image_type: str, message: str, history: list) -> list:
    """处理图片分析和对话"""
    try:
        logger.info(f"开始处理图片分析，类型：{image_type}，消息：{message}")
        if not image:
            history.append({"role": "assistant", "content": "请先上传图片"})
            return history
        
        # 保存图片到临时文件,,使用原始文件名
        original_filename = image_file.name
        temp_path = os.path.join(config.get_upload_path(), original_filename)
        image.save(temp_path)
        logger.info(f"图片已保存到：{temp_path}")

         # 获取图片类型的配置
        image_config = config.get_image_type_prompt(image_type)
        if image_config is None:
            error_msg = f"不支持的图片类型: {image_type}"
            logger.error(error_msg)
            history.append({"role": "assistant", "content": error_msg})
            return history
        
         # 上传图片到Gemini
        image_file = main.upload_to_gemini(temp_path, mime_type=image_config['mime_type'])
        logger.info("图片已上传到Gemini")

        if not message:
            prompt = image_config['system_prompt']
            response = st.session_state.vision_model.generate_content([image_file, prompt])
        else:
            response = st.session_state.vision_model.generate_content([image_file, message])
            
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
        logger.info(f"开始处理报告分析，消息：{message}")
        
        # 检查是否有PDF文件上传
        if pdf_file is None and not message:
            history.append({"role": "assistant", "content": "请先上传报告"})
            return history
        
        # 如果有新的PDF文件上传
        if pdf_file is not None:
            logger.info("处理新上传的PDF文件")
            # 保存PDF到临时文件
            temp_path = os.path.join(config.get_upload_path(), "temp_report.pdf")
            with open(temp_path, "wb") as f:
                f.write(pdf_file.read())
            logger.info(f"报告已保存到：{temp_path}")
            
            # 分析报告并创建缓存
            result = main.upload_pdf_and_cache(temp_path)
            if result is None or len(result) != 2:
                raise Exception("报告分析失败")
                
            cache, summary = result
            logger.info(f"获取到的概要总结：{summary}")
            
            # 保存缓存到session_state
            st.session_state.report_cache = cache
            
            # 初始化新的对话历史
            history = []
            history.append({"role": "assistant", "content": summary})
            return history
            
        # 处理后续对话
        elif message and hasattr(st.session_state, 'report_cache'):
            logger.info(f"处理后续对话，消息：{message}")
            
            # 构建完整的对话历史
            chat_history = []
            for msg in history:
                if msg["role"] == "user":
                    chat_history.append(f"用户: {msg['content']}")
                else:
                    chat_history.append(f"助手: {msg['content']}")
            
            # 构建提示
            prompt = f"""基于报告内容回答以下问题。如果问题超出报告范围，请明确说明。

对话历史：
{chr(10).join(chat_history)}

用户新问题：{message}"""
            
            # 使用缓存生成回答
            response = main.generate_content_from_cache(st.session_state.report_cache, prompt)
            if not response or not response.text:
                raise Exception("模型没有返回响应")
                
            response_text = response.text
            logger.info(f"收到回复：{response_text}")
            
            # 更新对话历史
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response_text})
            
        else:
            logger.warning("没有上传报告或保存的报告内容")
            history.append({"role": "assistant", "content": "请先上传报告再进行对话"})
        
        return history
        
    except Exception as e:
        error_msg = f"分析报告时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        history.append({"role": "assistant", "content": error_msg})
        return history

def manage_files_ui() -> str:
    """文件管理界面"""
    try:
        logger.info("开始获取文件列表")
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
        error_msg = f"获取文件列表时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

def delete_file_ui(file_name: str) -> str:
    """删除文件"""
    try:
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

# --- Streamlit UI ---

st.markdown(
    f"<style>body {{ background-color: {ui_config.get('theme_color', '#ffffff')}; }}</style>", 
    unsafe_allow_html=True
)
st.title(ui_config.get('title', '小胰宝助手'))

# 确保目录存在
os.makedirs(config.get_upload_path(), exist_ok=True)
os.makedirs(config.get_cache_path(), exist_ok=True)

# 添加自定义 CSS 样式
st.markdown("""
<style>
/* 聊天消息容器样式 */
.stChatMessage {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* 用户消息样式 */
.stChatMessage[data-testid="user-message"] {
    background-color: #E3F2FD;
    border-left: 4px solid #2196F3;
}

/* 助手消息样式 */
.stChatMessage[data-testid="assistant-message"] {
    background-color: #F5F5F5;
    border-left: 4px solid #4CAF50;
}

/* 消息文本样式 */
.stMarkdown {
    font-size: 1rem;
    line-height: 1.5;
}

/* 输入框样式 */
.stTextInput input {
    border-radius: 20px;
    padding: 0.5rem 1rem;
    border: 2px solid #E0E0E0;
}

.stTextInput input:focus {
    border-color: #2196F3;
    box-shadow: 0 0 0 2px rgba(33,150,243,0.2);
}

/* 按钮样式 */
.stButton > button {
    border-radius: 20px;
    padding: 0.5rem 1.5rem;
    background-color: #2196F3;
    color: white;
    border: none;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    background-color: #1976D2;
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

/* 文件上传区域样式 */
.stUploadButton {
    border: 2px dashed #E0E0E0;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    background-color: #FAFAFA;
}

.stUploadButton:hover {
    border-color: #2196F3;
    background-color: #F5F5F5;
}

/* 标签页样式 */
.stTabs [data-baseweb="tab-list"] {
    gap: 2rem;
}

.stTabs [data-baseweb="tab"] {
    padding: 1rem 2rem;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    background-color: rgba(33,150,243,0.1);
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)

# 使用标签页
tabs = st.tabs([
    ui_config['chat_title'],
    ui_config['image_title'],
    ui_config['report_title'],
    ui_config['file_title']
])


# --- 普通对话���签 ---
with tabs[0]:
     # 初始化会话状态
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # 显示聊天历史
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # 获取用户输入
    query = st.chat_input("有什么问题吗？")
        
    # 处理用户输入
    if query:
        # 添加用户消息到会话状态
        with st.chat_message("user"):
            st.markdown(query)
        
        # 调用聊天函数，更新会话状态
        updated_history = chat_function(query, st.session_state.chat_messages)
        st.session_state.chat_messages = updated_history
        
        # 显示助手消息
        if st.session_state.chat_messages and st.session_state.chat_messages[-1]["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(st.session_state.chat_messages[-1]["content"])


# --- 图片分析标签 ---
with tabs[1]:
    if "image_chat_messages" not in st.session_state:
        st.session_state.image_chat_messages = []

    # 创建两列布局
    col1, col2 = st.columns([6, 4])
    
    # 左侧列：图片上传和分析区域
    with col1:
        with st.container():
            # 图上组
            st.markdown("### 图片分析区域")
            image_file = st.file_uploader(
                "上传图片",
                type=config.get_system_config().get('supported_image_types', ['png', 'jpg', 'jpeg', 'bmp'])
            )
            
            # 图片显示和类型选择
            if image_file:



                image = Image.open(image_file)
                st.image(image, caption="上传的图片", use_container_width=True)
                image_type = st.selectbox("图片类型", list(prompts["analysis_prompts"].keys()))
                
                # 分析按钮组
                col_analyze, col_clear = st.columns([1, 1])
                with col_analyze:
                    if st.button("分析图片", key="analyze_image_btn", use_container_width=True):
                        with st.spinner("分析中..."):
                            updated_history = analyze_image_chat(
                                image,
                                image_file,
                                image_type,
                                "",
                                st.session_state.image_chat_messages
                            )
                            st.session_state.image_chat_messages = updated_history
                with col_clear:
                    if st.button("清除图片", key="clear_image_btn", use_container_width=True):
                        st.session_state.image_chat_messages = []
                        st.rerun()

    # 右侧列：对话历史
    with col2:
        st.markdown("### 对话历史")
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.image_chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

    # 底部：统一的对话输入区域
    st.markdown("---")
    with st.container():
        # 创建一个固定在底部的输入区域
        image_msg = st.text_input(
            "问题",
            placeholder="请输入您的问题...",
            key="image_chat_input",
            on_change=None  # 用于触发回车事件
        )
        
        # 使用columns确保按钮对齐且宽度合适
        cols = st.columns([4, 1])
        with cols[1]:
            send_clicked = st.button(
                "发送",
                use_container_width=True,
                type="primary"
            )
        
        # 检查是否按下回车键或点击发送按钮
        if (image_msg and image_msg != st.session_state.get('previous_msg', '')) or send_clicked:
            if image and image_msg:
                with st.spinner("处理中..."):
                    updated_history = analyze_image_chat(
                        image,
                        image_file,
                        image_type,
                        image_msg,
                        st.session_state.image_chat_messages
                    )
                    st.session_state.image_chat_messages = updated_history
                    # 保存当前消息用于比较
                    st.session_state.previous_msg = image_msg
                    # 使用 rerun 来清空输入框
                    if 'image_chat_input' in st.session_state:
                        del st.session_state.image_chat_input
                    st.rerun()
            else:
                st.warning("请确保已上传图片并输入问题")

# 添加自定义CSS样式
st.markdown("""
<style>
/* 图片分析页面样式 */
.image-analysis-container {
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 1rem;
    margin-bottom: 1rem;
}

/* 对话输入区域样式 */
.chat-input-container {
    position: sticky;
    bottom: 0;
    background-color: white;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
    z-index: 100;
}

/* 按钮样式 */
.stButton > button {
    border-radius: 20px;
    padding: 0.5rem 1rem;
    width: 100%;
}

/* 主要按钮样式 */
.stButton.primary > button {
    background-color: #2196F3;
    color: white;
}

/* 聊天消息样式 */
.chat-message {
    padding: 0.5rem 1rem;
    margin: 0.5rem 0;
    border-radius: 8px;
}

.user-message {
    background-color: #E3F2FD;
}

.assistant-message {
    background-color: #F5F5F5;
}

/* 图片上传区域样式 */
.uploadedFile {
    border: 2px dashed #E0E0E0;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)


# --- 报告分析标签 ---
with tabs[2]:
    if "report_chat_messages" not in st.session_state:
        st.session_state.report_chat_messages = []

    # 创建两列布局
    col1, col2 = st.columns([6, 4])
    
    # 左侧列：报告上传和分析区域
    with col1:
        with st.container():
            st.markdown("### 报告分析区域")
            pdf_file = st.file_uploader("上传医疗报告", type=["pdf"])
            
            if pdf_file:
                # 显示PDF文件名
                st.markdown(f"**已上传文件：** {pdf_file.name}")
                
                # 分析按钮组
                col_analyze, col_clear = st.columns([1, 1])
                with col_analyze:
                    if st.button("分析报告", key="analyze_report_btn", use_container_width=True):
                        with st.spinner("分析中..."):
                            updated_history = analyze_report_chat(pdf_file, "", st.session_state.report_chat_messages)
                            st.session_state.report_chat_messages = updated_history
                with col_clear:
                    if st.button("清除报告", key="clear_report_btn", use_container_width=True):
                        st.session_state.report_chat_messages = []
                        st.rerun()

    # 右侧列：对话历史
    with col2:
        st.markdown("### 对话历史")
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.report_chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

    # 底部：统一的对话输入区域
    st.markdown("---")
    with st.container():
        # 创建一个固定在底部的输入区域
        report_msg = st.text_input(
            "问题",
            placeholder="请输入您的问题...",
            key="report_chat_input"
        )
        
        # 使用columns确保按钮对齐且宽度合适
        cols = st.columns([4, 1])
        with cols[1]:
            send_clicked = st.button(
                "发送",
                key="send_report_msg_btn",
                use_container_width=True,
                type="primary"
            )
        
        # 检查是否按下回车键或点击发送按钮
        if (report_msg and report_msg != st.session_state.get('previous_report_msg', '')) or send_clicked:
            if pdf_file or report_msg:
                with st.spinner("处理中..."):
                    updated_history = analyze_report_chat(
                        pdf_file,
                        report_msg,
                        st.session_state.report_chat_messages
                    )
                    st.session_state.report_chat_messages = updated_history
                    # 保存当前消息用于比较
                    st.session_state.previous_report_msg = report_msg
                    # 使用 rerun 来清空输入框
                    if 'report_chat_input' in st.session_state:
                        del st.session_state.report_chat_input
                    st.rerun()
            else:
                st.warning("请先上传报告或输入问题")

# 更新CSS样式，使用紫色色调
st.markdown("""
<style>
/* 主题颜色 - 紫色系 */
:root {
    --primary-color: #9C27B0;
    --primary-light: #E1BEE7;
    --primary-dark: #7B1FA2;
    --accent-color: #BA68C8;
}

/* 按钮样式 */
.stButton > button {
    border-radius: 20px;
    padding: 0.5rem 1rem;
    width: 100%;
    background-color: var(--primary-color) !important;
    color: white !important;
}

.stButton > button:hover {
    background-color: var(--primary-dark) !important;
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

/* 聊天消息样式 */
.stChatMessage[data-testid="user-message"] {
    background-color: var(--primary-light);
    border-left: 4px solid var(--primary-color);
}

.stChatMessage[data-testid="assistant-message"] {
    background-color: #F3E5F5;
    border-left: 4px solid var(--accent-color);
}

/* 输入框样式 */
.stTextInput input {
    border-radius: 20px;
    border: 2px solid var(--primary-light);
}

.stTextInput input:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(156,39,176,0.2);
}

/* 上传区域样式 */
.uploadedFile {
    border: 2px dashed var(--primary-light);
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}

/* 容器样式 */
.chat-container {
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(156,39,176,0.1);
    padding: 1rem;
    margin-bottom: 1rem;
}

/* 分割线样式 */
hr {
    border-color: var(--primary-light);
}

/* 标题样式 */
h3 {
    margin: 1rem 0 !important;
    color: var(--primary-dark) !important;
    font-size: 1.2rem !important;
}

/* 列对齐样式 */
[data-testid="column"] {
    display: flex !important;
    align-items: center !important;
    padding: 0 0.25rem !important;
}

/* 去除 Streamlit 默认的列间距 */
[data-testid="column"] > div {
    width: 100% !important;
}

/* toast 消息样式 */
.stToast {
    background-color: var(--primary-light) !important;
    color: var(--primary-dark) !important;
    border-radius: 4px !important;
}
</style>
""", unsafe_allow_html=True)


# --- 文件管理标签 ---
# --- 文件管理标签 ---
with tabs[3]:  
    with st.container(): 
        # 标题和文件列表
        st.markdown("### 文件列表")
        file_list_str = manage_files_ui()
        st.text_area("当前文件", value=file_list_str, height=300, key="file_list_display")
        
        # 操作区域
        st.markdown("### 文��操作")
        
        # 使用container包装所有列，确保对齐
        with st.container():
            # 创建一个行，包含所有操作元素
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1], gap="small")
            
            # 第一列：文件名输入
            with col1:
                file_name = st.text_input(
                    "文件名",
                    placeholder="输入要删除的文件名",
                    label_visibility="collapsed"
                )
            
            # 第二列：删除按钮（垂直居中对齐）
            with col2:
                st.write("")  # 添加空行以对齐
                if st.button("删除", key="delete_file_btn", use_container_width=True):
                    result = delete_file_ui(file_name)
                    st.toast(result)
            
            # 第三列：刷新按钮
            with col3:
                st.write("")  # 添加空行以对齐
                if st.button("刷新", key="refresh_list_btn", use_container_width=True):
                    st.rerun()
            
            # 第四列：清理缓存按钮
            with col4:
                st.write("")  # 添加空行以对齐
                if st.button("清理", key="clear_cache_btn", use_container_width=True):
                    result = clear_cache_ui()
                    st.toast(result)

# 添加文件管理特定的CSS样式
st.markdown("""
<style>
/* 文件管理页面整体容器 */
.file-management-container {
    padding: 1rem;
}

/* 文件列表区域样式 */
.stTextArea textarea {
    border: 1px solid var(--primary-light);
    border-radius: 8px;
    font-family: monospace;
}

/* 操作区域样式 */
.operation-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
}

/* 输入样式 */
.stTextInput input {
    height: 36px !important;
    margin-bottom: 0 !important;
    border-radius: 4px !important;
}

/* 按钮样式统一 */
.stButton > button {
    height: 36px !important;
    padding: 0 1rem !important;
    font-size: 0.875rem !important;
    margin: 0 !important;
    border-radius: 4px !important;
    background-color: var(--primary-color) !important;
    color: white !important;
}

/* 按钮悬停效果 */
.stButton > button:hover {
    background-color: var(--primary-dark) !important;
    transform: translateY(-1px);
    transition: all 0.2s ease;
}

/* 标题样式 */
h3 {
    margin: 1rem 0 !important;
    color: var(--primary-dark) !important;
    font-size: 1.2rem !important;
}

/* 列对齐样式 */
[data-testid="column"] {
    display: flex !important;
    align-items: center !important;
    padding: 0 0.25rem !important;
}

/* 去除 Streamlit 默认的列间距 */
[data-testid="column"] > div {
    width: 100% !important;
}

/* toast 消息样式 */
.stToast {
    background-color: var(--primary-light) !important;
    color: var(--primary-dark) !important;
    border-radius: 4px !important;
}
</style>
""", unsafe_allow_html=True)
    
logger.info("Streamlit Web UI 初始化完成") # 日志记录