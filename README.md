# Gemini 2.0 Demo 应用

这是基于小胰宝思路，通过Gemini 2.0 API实现的demo应用，可以方便后续对于小胰宝的开发模块参考。

## 主要功能

1. **医疗报告解读**：支持对PDF格式的医疗报告进行智能解读，提供概要和关键发现。
2. **病理图片分析**：支持对病理切片及其他医学图像进行分析，提供专业的解读和建议。
3. **多轮对话**：用户可以在解读结果后继续提问，系统会根据上下文进行回答。

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
