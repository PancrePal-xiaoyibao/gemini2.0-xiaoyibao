import json
import os
import logging
from typing import Dict, Any, Optional

class Config:
    """配置管理类"""
    def __init__(self):
        """初始化配置类"""
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.config = {}  # 初始化空配置
        self.load_config()     # 再加载配置

    def _setup_logging(self) -> None:
        """设置日志配置"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 获取日志配置
        log_config = self.config.get('system_config', {}).get('logging', {
            'level': 'INFO',
            'max_bytes': 10485760,  # 10MB
            'backup_count': 5,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        })
        
        # 设置日志级别
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        
        # 设置日志格式
        log_format = log_config.get('format')
        formatter = logging.Formatter(log_format)
        
        # 设置日志处理器
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=log_config.get('max_bytes', 10485760),
            backupCount=log_config.get('backup_count', 5),
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # 清除现有的处理器
        root_logger.handlers.clear()
        
        # 添加新的处理器
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("日志系统初始化完成")

    def load_config(self) -> None:
        """从config.json加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            # 设置日志配置
            self._setup_logging()  # 先设置日志
            self.logger.info("成功加载配置文件")
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            self.config = {}

    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        return self.config.get('model_config', {})

    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI配置"""
        return self.config.get('ui_config', {})

    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.config.get('system_config', {})

    def get_proxy_config(self) -> Dict[str, Any]:
        """获取代理配置"""
        system_config = self.get_system_config()
        return system_config.get('proxy', {
            'enabled': False,
            'http': None,
            'https': None,
            'timeout': 30,
            'retry_count': 3
        })

    def get_prompts(self) -> Dict[str, Any]:
        """获取提示词配置"""
        return self.config.get('prompts', {})

    def get_image_types(self) -> Dict[str, Dict[str, str]]:
        """获取图片类型配置"""
        prompts = self.get_prompts()
        return prompts.get('analysis_prompts', {})

    def get_image_type_prompt(self, image_type: str) -> Optional[Dict[str, str]]:
        """获取特定图片类型的提���词配置"""
        image_types = self.get_image_types()
        return image_types.get(image_type)

    def get_upload_path(self) -> str:
        """获取上传路径"""
        system_config = self.get_system_config()
        upload_path = system_config.get('upload_path', 'uploads/')
        os.makedirs(upload_path, exist_ok=True)
        return upload_path

    def get_cache_path(self) -> str:
        """获取缓存路径"""
        system_config = self.get_system_config()
        cache_path = system_config.get('cache_path', 'cache/')
        os.makedirs(cache_path, exist_ok=True)
        return cache_path

    def is_supported_image_type(self, mime_type: str) -> bool:
        """检查是否支持的图片类型"""
        system_config = self.get_system_config()
        return mime_type in system_config.get('supported_image_types', [])

    def is_supported_doc_type(self, mime_type: str) -> bool:
        """检查是否支持的文档类型"""
        system_config = self.get_system_config()
        return mime_type in system_config.get('supported_doc_types', [])

    def save_uploaded_file(self, uploaded_file) -> str:
        """
        保存上传的文件并返回保存路径
        :param uploaded_file: StreamlitUploadedFile对象
        :return: 保存后的文件路径
        """
        # 获取上传路径
        upload_path = self.get_upload_path()
        
        # 获取原始文件名
        original_filename = uploaded_file.name
        file_extension = original_filename.split('.')[-1].lower()
        
        # 构建保存路径
        save_path = os.path.join(upload_path, original_filename)
        
        # 处理文件名冲突
        if os.path.exists(save_path):
            base_name = original_filename.rsplit('.', 1)[0]
            counter = 1
            while os.path.exists(save_path):
                new_filename = f"{base_name}_{counter}.{file_extension}"
                save_path = os.path.join(upload_path, new_filename)
                counter += 1
        
        # 保存文件
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return save_path

    def get_login_password(self):
        """获取登录密码"""
        return self.config.get("system_config", {}).get("login_config", {}).get("password", "")

    def get_password_expiry_days(self):
        """获取密码过期天数"""
        return self.config.get("system_config", {}).get("login_config", {}).get("password_expiry_days", 3)

# 创建全局配置实例
config = Config()
