# Gemini 2.0 医疗报告智能解读助手

这是一个基于Google Gemini 2.0 API的医疗报告智能解读助手，能够帮助用户理解医疗报告和病理图片。

## 主要功能

1. 医疗报告PDF解读
   - 上传PDF格式的医疗报告
   - 智能分析报告内容
   - 提供通俗易懂的解释

2. 病理图片分析
   - 支持多种图片格式
   - 专业的病理图片解读
   - 关键信息提示

3. 智能对话
   - 保持对话上下文
   - 可随时清除对话历史
   - 专业医生式的回答

## 环境要求

- Python 3.8+
- 依赖包：见 requirements.txt

## 安装步骤

1. 克隆项目
```bash
git clone https://github.com/PancrePal-xiaoyibao/gemini2.0-xiaoyibao.git
cd gemini2.0-xiaoyibao
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置API密钥
   - 复制 `.env.example` 文件为 `.env`
   - 在 `.env` 文件中设置你的 Gemini API 密钥：
     ```
     GEMINI_API_KEY=your_api_key_here
     ```

## 使用方法

运行主程序：
```bash
python main.py
```

按照菜单提示进行操作：
1. 选择报告解读功能
2. 选择图片分析功能
3. 根据提示输入相应信息

## 注意事项

- 请确保在使用前已正确配置 Gemini API 密钥
- PDF文件和图片需要存放在程序可访问的路径下
- 建议定期清除对话历史以获得最佳体验

## 免责声明

本工具仅供辅助参考，不能替代专业医生的诊断意见。重要医疗决策请务必咨询专业医生。
