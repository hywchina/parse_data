import os
import re
import shutil
from PyPDF2 import PdfReader

# ========== 1️⃣ 配置路径 ==========
data_ori = "/home/huyanwei/projects/parse_data/data_00_ori"   # 原始 PDF 文件夹
data_pdf = "/home/huyanwei/projects/parse_data/data_02_pdf"   # 输出文件夹

os.makedirs(data_pdf, exist_ok=True)

# ========== 2️⃣ 提取病案号函数 ==========
def extract_case_id_from_pdf(pdf_path):
    """
    从 PDF 文本中提取病案号（格式：病案号：xxxxxx）
    返回6位病案号字符串或 None
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        # 匹配病案号（格式：病案号：后跟数字，取最后6位）
        match = re.search(r"病案号[:：]?\s*0*(\d{1,6})", text)
        if match:
            case_id = match.group(1).zfill(6)
            return case_id
    except Exception as e:
        print(f"⚠️ 无法读取 {pdf_path}，错误：{e}")
    return None

# ========== 3️⃣ 遍历目录并重命名 ==========
for root, dirs, files in os.walk(data_ori):
    for filename in files:
        if filename.lower().endswith(".pdf"):
            ori_path = os.path.join(root, filename)
            case_id = extract_case_id_from_pdf(ori_path)

            if case_id:
                new_filename = f"{case_id}.pdf"
                new_path = os.path.join(data_pdf, new_filename)

                # 如果已存在同名文件，可以在此加逻辑避免覆盖
                if os.path.exists(new_path):
                    print(f"⚠️ 病案号 {case_id} 已存在，跳过 {filename}")
                    continue

                shutil.copy2(ori_path, new_path)
                print(f"✅ 已提取病案号 {case_id} → {new_filename}")
            else:
                print(f"❌ 未找到病案号：{ori_path}")

print(f"\n🎉 处理完成！所有新文件保存在：{os.path.abspath(data_pdf)}")
