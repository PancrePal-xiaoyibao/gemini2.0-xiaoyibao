import google.generativeai as genai
from IPython.display import Markdown
import logging

def list_all_files():
    """列出所有上传的文件"""
    try:
        # 列出普通文件
        files = list(genai.list_files())
        total_files = []
        
        if not files:
            print("当前没有已上传的文件")
        else:
            print("\n=== 已上传文件列表 ===")
            for i, file in enumerate(files, 1):
                print(f"{i}. 文件名: {file.display_name}")
                print(f"   文件URI: {file.uri}")
                print(f"   类型: 普通文件")
                print("-" * 50)
                total_files.append(("file", file))

        return total_files
    except Exception as e:
        print(f"列出文件时发生错误: {e}")
        return []

def delete_file(file_type, file_obj):
    """删除指定的文件"""
    try:
        if file_type == "file":
            genai.delete_file(file_obj.name)
            print(f'已成功删除文件: {file_obj.display_name}')
            return True
    except Exception as e:
        print(f"删除时发生错误: {e}")
        return False

def clear_all_cache():
    """清理所有缓存"""
    try:
        genai.caching.clear_all()
        print("已成功清理所有缓存")
        return True
    except Exception as e:
        print(f"清理缓存时发生错误: {e}")
        return False

def manage_files():
    """文件管理主菜单"""
    while True:
        print("\n=== 文件管理菜单 ===")
        print("1. 查看所有文件")
        print("2. 删除文件")
        print("3. 清理所有缓存")
        print("4. 返回主菜单")
        
        choice = input("请选择操作 (1-4): ").strip()
        
        if choice == "1":
            list_all_files()
        elif choice == "2":
            files = list_all_files()
            if files:
                file_index = input("\n请输入要删除的文件序号 (输入 'N' 取消): ").strip()
                if file_index.upper() != 'N':
                    try:
                        idx = int(file_index) - 1
                        if 0 <= idx < len(files):
                            file_type, file_obj = files[idx]
                            confirm = input(f"确认删除文件 '{file_obj.display_name}'? (Y/N): ").strip().upper()
                            
                            if confirm == 'Y':
                                delete_file(file_type, file_obj)
                        else:
                            print("无效的文件序号")
                    except ValueError:
                        print("请输入有效的数字")
        elif choice == "3":
            confirm = input("确认清理所有缓存? 这将删除所有PDF文档的处理缓存 (Y/N): ").strip().upper()
            if confirm == 'Y':
                clear_all_cache()
        elif choice == "4":
            break
        else:
            print("无效的选择，请重试")

if __name__ == "__main__":
    manage_files()