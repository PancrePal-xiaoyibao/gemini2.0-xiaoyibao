import json
import os

class Config:
    def __init__(self):
        """初始化配置类"""
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.load_config()

    def load_config(self):
        """从config.json加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.config = {}

    def get_model_config(self):
        """获取模型配置"""
        return self.config.get('model_config', {})

    def get_image_types(self):
        """获取图像类型配置"""
        return self.config.get('image_types', {})

    def get_allowed_extensions(self):
        """获取允许的文件扩展名"""
        return self.config.get('allowed_extensions', {})

    def get_ui_config(self):
        """获取UI配置"""
        return self.config.get('ui_config', {})

    def get_system_prompt(self, image_type):
        """获取特定图像类型的系统提示"""
        image_types = self.get_image_types()
        return image_types.get(image_type, {}).get('system_prompt', '')

# 创建全局配置实例
config = Config()
