import json
import os
from typing import Dict, Any, Optional

class Config:
    """配置管理类"""
    def __init__(self):
        """初始化配置类"""
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.load_config()

    def load_config(self) -> None:
        """从config.json加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
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

    def get_prompts(self) -> Dict[str, Any]:
        """获取提示词配置"""
        return self.config.get('prompts', {})

    def get_image_types(self) -> Dict[str, Dict[str, str]]:
        """获取图片类型配置"""
        prompts = self.get_prompts()
        return prompts.get('analysis_prompts', {})

    def get_image_type_prompt(self, image_type: str) -> Optional[Dict[str, str]]:
        """获取特定图片类型的提示词配置"""
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

    def get_supported_types(self, type_key: str) -> list:
        """获取支持的文件类型"""
        system_config = self.get_system_config()
        return system_config.get(f'supported_{type_key}_types', [])

# 创建全局配置实例
config = Config()
