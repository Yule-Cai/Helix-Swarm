# skills/drag_reader.py
import os
import shutil
from core.registry import tool

# 定义沙盒目录
SANDBOX_DIR = os.path.abspath(os.path.join(os.getcwd(), "workspace", "sandbox"))
os.makedirs(SANDBOX_DIR, exist_ok=True)

@tool(
    name="read_dragged_file",
    description="【最高特权指令】当用户或主管提供本地文件的绝对路径时，调用此工具读取内容并存入沙盒。"
)
def read_dragged_file(filepath: str) -> str:
    """支持终端拖拽的智能文件读取器：自动拷贝入沙盒 -> 解析 -> 返回内容"""
    # 1. 清洗终端拖拽时自动生成的双引号和单引号
    clean_path = filepath.strip("\"'").strip()
    
    # 🚀 新增：清洗 file:/// 协议头，提取纯正 Windows 绝对路径
    if clean_path.startswith("file:///"):
        clean_path = clean_path[8:]
    
    if not os.path.exists(clean_path):
        return f"Error: 找不到你拖进来的文件 -> {clean_path}"
        
    filename = os.path.basename(clean_path)
    sandbox_path = os.path.join(SANDBOX_DIR, filename)
    
    try:
        # 2. 核心：自动把文件“吸”进沙盒
        shutil.copy2(clean_path, sandbox_path)
        
        # 3. 开始解析沙盒里的文件
        ext = os.path.splitext(sandbox_path)[1].lower()
        content = ""
        
        if ext in ['.txt', '.md', '.py', '.json', '.csv', '.html', '.log']:
            with open(sandbox_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
        elif ext == '.pdf':
            try:
                import PyPDF2
                with open(sandbox_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            content += extracted + "\n"
            except ImportError:
                return "Error: 缺少 PyPDF2。请终端运行 pip install PyPDF2"
                
        elif ext in ['.docx', '.doc']:
            try:
                import docx
                doc = docx.Document(sandbox_path)
                content = "\n".join([p.text for p in doc.paragraphs])
            except ImportError:
                return "Error: 缺少 python-docx。请终端运行 pip install python-docx"
                
        else:
            # 未知文件暴力读取
            with open(sandbox_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
        return f"✅ [系统提示] 文件已自动拷贝至沙盒: {sandbox_path}\n\n[以下是文件内容]\n" + content
        
    except Exception as e:
        return f"Error: 读取失败 -> {str(e)}"