# 数据处理工具库 - 完整源代码

> 本文档包含 utils 目录下所有 Python 源代码，用于软著申请

**生成时间**: 2025-12-09 13:46:31  
**项目**: parse_data 数据处理一键工具  
**总文件数**: 8  

## 📑 文件目录

1. [00_read_headers.py](#00_read_headers-py)
2. [01_parse_xls_to_csv.py](#01_parse_xls_to_csv-py)
3. [02_rename_pdf.py](#02_rename_pdf-py)
4. [03_merge_csv_to_json.py](#03_merge_csv_to_json-py)
5. [04_generate_reports_infini.py](#04_generate_reports_infini-py)
6. [05_merge_txt_to_pdf.py](#05_merge_txt_to_pdf-py)
7. [config_manager.py](#config_manager-py)
8. [robust_utils.py](#robust_utils-py)

---

## 00_read_headers.py

**文件信息**:
- 行数: 41
- 大小: 1353 字节

```python
import pandas as pd
import os

# ===== 文件路径配置（请根据你的路径修改） =====
base_dir = "./data_01_csv/"
files = {
    "检查信息": f"{base_dir}检查信息.csv",
    "病案首页": f"{base_dir}病案首页.csv",
    "检验信息": f"{base_dir}检验信息.csv",
    "医嘱信息": f"{base_dir}医嘱信息.csv"
}

# ===== 自动识别编码读取函数 =====
def read_csv_headers(path):
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, nrows=0)  # 只读取表头
            return list(df.columns)
        except Exception:
            continue
    raise ValueError(f"❌ 无法读取文件表头：{path}")

# ===== 主逻辑：读取并输出每个文件的表头 =====
headers_dict = {}

for name, path in files.items():
    if not os.path.exists(path):
        print(f"⚠️ 文件未找到: {path}")
        continue
    headers = read_csv_headers(path)
    headers_dict[name] = headers
    print(f"\n📘 {name} 表头字段（共 {len(headers)} 个）：")
    print(headers)

# ===== 可选：保存为一个 JSON 文件 =====
import json
with open("./conf/headers.json", "w", encoding="utf-8") as f:
    json.dump(headers_dict, f, ensure_ascii=False, indent=2)

print("\n✅ 已生成文件：各表字段汇总.json")

```

---

## 01_parse_xls_to_csv.py

**文件信息**:
- 行数: 64
- 大小: 2537 字节

```python
import os
import shutil
import pandas as pd

# ========== 路径配置 ==========
data_ori = "./data_00_ori"
data_csv = "./data_01_csv"
os.makedirs(data_csv, exist_ok=True)


def excel_to_csv(data_ori, data_csv):
    # 遍历目录下所有文件
    for filename in os.listdir(data_ori):
        file_path = os.path.join(data_ori, filename)

        # ===== 情况 1：CSV 文件，直接拷贝 =====
        if filename.lower().endswith(".csv"):
            try:
                target_path = os.path.join(data_csv, filename)
                shutil.copy2(file_path, target_path)
                print(f"📄 直接拷贝 CSV: {target_path}")
            except Exception as e:
                print(f"❌ 拷贝 CSV 文件 {filename} 失败: {e}")
            continue  # 跳过后续 Excel 处理逻辑

        # ===== 情况 2：Excel 文件，转换为 CSV =====
        if filename.lower().endswith(('.xlsx', '.xls')):
            print(f"正在处理 Excel: {file_path}")

            try:
                excel_file = pd.ExcelFile(file_path)
            except Exception as e:
                print(f"❌ 无法读取文件 {filename}: {e}")
                continue

            sheet_names = excel_file.sheet_names
            single_sheet = len(sheet_names) == 1  # 仅一个 sheet

            for sheet_name in sheet_names:
                try:
                    # 尝试读取表格（含表头）
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)

                    # 检查表头是否异常（Unnamed 或 NaN）
                    if df.columns.isnull().any() or all(str(col).startswith("Unnamed") for col in df.columns):
                        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                        df.columns = [f"Column_{i+1}" for i in range(df.shape[1])]

                    # 输出文件名
                    base_name = os.path.splitext(filename)[0]
                    csv_filename = f"{base_name}.csv" if single_sheet else f"{base_name}_{sheet_name}.csv"
                    csv_path = os.path.join(data_csv, csv_filename)

                    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    print(f"✅ 已生成: {csv_path}")

                except Exception as e:
                    print(f"⚠️ 处理 {filename} 的表 {sheet_name} 时出错: {e}")

        else:
            print(f"⏭️ 跳过非 Excel/CSV 文件: {filename}")

if __name__ == '__main__':
    excel_to_csv(data_ori, data_csv)

```

---

## 02_rename_pdf.py

**文件信息**:
- 行数: 53
- 大小: 1919 字节

```python
import os
import re
import shutil
from PyPDF2 import PdfReader

# ========== 1️⃣ 配置路径 ==========
data_ori = "./data_00_ori"   # 原始 PDF 文件夹
data_pdf = "./data_02_pdf"   # 输出文件夹

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

```

---

## 03_merge_csv_to_json.py

**文件信息**:
- 行数: 168
- 大小: 6843 字节

```python
import pandas as pd
import json
import os
import numpy as np

# ========== 1️⃣ 文件路径（请修改为你自己的） ==========
input_dir = "./data_01_csv"  # 输入文件夹
output_dir = "./data_03_json"  # 输出文件夹
headers_file = "./conf/headers.json"  # headers.json 文件路径

file_检查 = f"{input_dir}/检查信息.csv"
file_检验 = f"{input_dir}/检验信息.csv"
file_病案 = f"{input_dir}/病案首页.csv"
file_医嘱 = f"{input_dir}/医嘱信息.csv"

# ========== 2️⃣ 从 headers.json 读取字段 ==========
with open(headers_file, "r", encoding="utf-8") as f:
    FIELDS = json.load(f)

# ========== 新增：删除NaN值的辅助函数 ==========
def remove_nan_values(obj):
    """递归删除字典或列表中的NaN值"""
    if isinstance(obj, dict):
        cleaned_dict = {}
        for k, v in obj.items():
            # 处理数组/Series类型的值
            if hasattr(v, '__len__') and not isinstance(v, (str, bytes)):
                # 如果是数组/Series，检查是否全部为NaN
                if len(v) > 0 and not pd.isna(v).all():
                    cleaned_dict[k] = remove_nan_values(v)
            # 处理标量值
            elif v is not None and not (isinstance(v, float) and np.isnan(v)):
                cleaned_dict[k] = remove_nan_values(v)
        return cleaned_dict
    elif isinstance(obj, list):
        cleaned_list = []
        for item in obj:
            # 处理数组/Series类型的值
            if hasattr(item, '__len__') and not isinstance(item, (str, bytes)):
                # 如果是数组/Series，检查是否全部为NaN
                if len(item) > 0 and not pd.isna(item).all():
                    cleaned_list.append(remove_nan_values(item))
            # 处理标量值
            elif item is not None and not (isinstance(item, float) and np.isnan(item)):
                cleaned_list.append(remove_nan_values(item))
        return cleaned_list
    else:
        return obj

# ========== 3️⃣ 自动识别编码读取 CSV ==========
def read_csv_auto(path):
    encodings = ["utf-8-sig", "gbk", "gb2312", "utf-8"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            return df
        except Exception:
            continue
    raise ValueError(f"无法读取文件：{path}")

# ========== 4️⃣ 读取数据 ==========
df_check = read_csv_auto(file_检查)
df_test = read_csv_auto(file_检验)
df_case = read_csv_auto(file_病案)
df_order = read_csv_auto(file_医嘱)

# ========== ✅ 统一病案号为六位数字 ==========
def normalize_case_id(series):
    """将病案号统一为6位数字（前补0）"""
    return series.astype(str).str.strip().str.zfill(6)

df_check["病案号"] = normalize_case_id(df_check["病案号"])
df_test["病案号"] = normalize_case_id(df_test["病案号"])
df_case["病案号"] = normalize_case_id(df_case["病案号"])
df_order["病案号"] = normalize_case_id(df_order["病案号"])

# ========== 5️⃣ 获取所有病案号 ==========
all_case_ids = set(
    df_case["病案号"]
) | set(
    df_check["病案号"]
) | set(
    df_test["病案号"]
) | set(
    df_order["病案号"]
)

# ========== 6️⃣ 生成输出文件夹 ==========
os.makedirs(output_dir, exist_ok=True)

# ========== 7️⃣ 主逻辑函数 ==========
def build_patient_json(case_id):
    record = {
        "病案首页": {},
        "检查信息": [],
        "检验信息": [],
        "医嘱信息": []
    }

    # 病案首页
    df_case_sub = df_case[df_case["病案号"] == case_id]
    if not df_case_sub.empty:
        cols = [c for c in FIELDS["病案首页"] if c in df_case_sub.columns]
        # 先转换为字典，然后手动处理NaN值
        case_dict = df_case_sub[cols].iloc[0].to_dict()
        # 手动过滤NaN值
        record["病案首页"] = {k: v for k, v in case_dict.items() 
                            if not (isinstance(v, float) and np.isnan(v))}
    
    # 检查信息
    df_check_sub = df_check[df_check["病案号"] == case_id]
    if not df_check_sub.empty:
        cols = [c for c in FIELDS["检查信息"] if c in df_check_sub.columns]
        # 删除病案号字段（保留其他字段）
        cols = [c for c in cols if c != "病案号"]
        # 先转换为字典，然后手动处理NaN值
        check_records = df_check_sub[cols].to_dict(orient="records")
        # 手动过滤每条记录中的NaN值
        record["检查信息"] = []
        for rec in check_records:
            cleaned_rec = {k: v for k, v in rec.items() 
                          if not (isinstance(v, float) and np.isnan(v))}
            if cleaned_rec:  # 只添加非空记录
                record["检查信息"].append(cleaned_rec)
    
    # 检验信息
    df_test_sub = df_test[df_test["病案号"] == case_id]
    if not df_test_sub.empty:
        cols = [c for c in FIELDS["检验信息"] if c in df_test_sub.columns]
        # 删除病案号字段（保留其他字段）
        cols = [c for c in cols if c != "病案号"]
        # 先转换为字典，然后手动处理NaN值
        test_records = df_test_sub[cols].to_dict(orient="records")
        # 手动过滤每条记录中的NaN值
        record["检验信息"] = []
        for rec in test_records:
            cleaned_rec = {k: v for k, v in rec.items() 
                          if not (isinstance(v, float) and np.isnan(v))}
            if cleaned_rec:  # 只添加非空记录
                record["检验信息"].append(cleaned_rec)
    
    # 医嘱信息
    df_order_sub = df_order[df_order["病案号"] == case_id]
    if not df_order_sub.empty:
        cols = [c for c in FIELDS["医嘱信息"] if c in df_order_sub.columns]
        # 删除病案号字段（保留其他字段）
        cols = [c for c in cols if c != "病案号"]
        # 先转换为字典，然后手动处理NaN值
        order_records = df_order_sub[cols].to_dict(orient="records")
        # 手动过滤每条记录中的NaN值
        record["医嘱信息"] = []
        for rec in order_records:
            cleaned_rec = {k: v for k, v in rec.items() 
                          if not (isinstance(v, float) and np.isnan(v))}
            if cleaned_rec:  # 只添加非空记录
                record["医嘱信息"].append(cleaned_rec)
    
    return record

# ========== 8️⃣ 遍历导出每个病案号 ==========
for case_id in sorted(all_case_ids):
    patient_json = build_patient_json(case_id)
    out_path = os.path.join(output_dir, f"{case_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(patient_json, f, ensure_ascii=False, indent=2)
    print(f"✅ 已生成：{out_path}")

print(f"\n🎉 所有病案号已成功导出到文件夹：{os.path.abspath(output_dir)}")
```

---

## 04_generate_reports_infini.py

**文件信息**:
- 行数: 133
- 大小: 4527 字节

```python
import os
import re
import json
from openai import OpenAI

# ========== 用户配置 ==========
INPUT_JSON_DIR = "./data_03_json"
PDF_DIR = "./data_02_pdf"  # 新增 PDF 对应目录
PROMPT_FILE = "./conf/prompt.txt"
OUTPUT_DIR = "./data_04_summary_txt"
LLM_CONFIG_FILE = "./conf/llm.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 从配置文件加载 LLM 配置
with open(LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
    llm_config = json.load(f)

default_model = llm_config["default"]
model_config = llm_config[default_model]

API_KEY = model_config["api_key"]
BASE_URL = model_config["base_url"]
MODEL_NAME = model_config["model_name"]
CHUNK_SIZE = model_config["chunk_size"]
CONTEXT_SNIPPET_LEN = model_config["context_snippet_len"]
# ==================================


def split_text(text, max_length):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


def remove_repeated_section(prev_text, new_text):
    new_text = new_text.strip()
    prev_end = prev_text[-2000:] if len(prev_text) > 2000 else prev_text

    pattern = r"(病案总结报告|一、基本信息|二、住院经过与主要时间线)"
    if re.search(pattern, new_text):
        first_match = re.search(pattern, new_text)
        if first_match:
            start_idx = first_match.start()
            if prev_end[:100] in new_text:
                new_text = new_text.replace(prev_end, "")
            if start_idx < 200:
                new_text = new_text[start_idx:]
    return new_text


def main():
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    for filename in os.listdir(INPUT_JSON_DIR):
        if not filename.endswith(".json"):
            continue

        # ===== 新增逻辑：检查对应 PDF 是否存在 =====
        base_name = os.path.splitext(filename)[0]
        pdf_path = os.path.join(PDF_DIR, base_name + ".pdf")
        if not os.path.exists(pdf_path):
            print(f"⚠️ 跳过：{filename} —— 未找到对应 PDF：{base_name}.pdf")
            continue
        # ========================================

        json_path = os.path.join(INPUT_JSON_DIR, filename)
        with open(json_path, "r", encoding="utf-8") as f:
            data_json = f.read()

        print(f"📄 正在处理：{filename}")

        chunks = split_text(data_json, CHUNK_SIZE)
        previous_summary = ""
        full_output = ""

        for idx, chunk in enumerate(chunks, 1):
            print(f"  🔹 分块 {idx}/{len(chunks)} 请求中...")

            user_input = f"""
以下为病案JSON的第 {idx} 段（共 {len(chunks)} 段）。
请【仅续写后续内容】，不要重复前文标题或章节。
不要重新生成“病案总结报告”标题或前面章节。

——前文摘要（供上下文参考）——
{previous_summary if previous_summary else "（首段，无前文）"}

——本段JSON数据——
{chunk}

请在保持医学书面语风格的前提下续写报告，注意：
1. 不重复已出现的章节或文字。
2. 不重写标题。
3. 保持逻辑衔接、时间顺序。
{prompt_template}
"""

            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一名具有30年以上临床经验的主任医师。请基于上下文续写病案总结报告，禁止重复前文内容。"
                        },
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.2,
                )

                output = response.choices[0].message.content.strip()
                cleaned = remove_repeated_section(full_output, output)

                full_output += "\n\n" + cleaned
                previous_summary = full_output[-CONTEXT_SNIPPET_LEN:]

            except Exception as e:
                print(f"❌ 分块 {idx} 出错：{e}")
                continue

        output_filename = base_name + ".txt"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(output_path, "w", encoding="utf-8") as out_f:
            out_f.write(full_output.strip())

        print(f"✅ 报告生成完成：{output_filename}")

    print("\n🎯 所有文件处理完成。")

if __name__ == "__main__":
    main()

```

---

## 05_merge_txt_to_pdf.py

**文件信息**:
- 行数: 90
- 大小: 2798 字节

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from PyPDF2 import PdfMerger
import os

def txt_to_pdf(txt_path, pdf_path):
    """将 TXT 文件转换为支持中文和自动换行的 PDF"""
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))  # 注册中文字体
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    margin_x = 50
    margin_y = 50
    line_height = 18
    max_width = width - 2 * margin_x
    y = height - margin_y
    c.setFont('STSong-Light', 12)

    def draw_wrapped_line(text):
        nonlocal y
        char_width = c.stringWidth("测", 'STSong-Light', 12)
        max_chars = int(max_width / char_width)
        lines = []
        while text:
            lines.append(text[:max_chars])
            text = text[max_chars:]
        for ln in lines:
            if y < margin_y:
                c.showPage()
                c.setFont('STSong-Light', 12)
                y = height - margin_y
            c.drawString(margin_x, y, ln)
            y -= line_height

    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            draw_wrapped_line(line.strip())

    c.save()


def merge_pdfs(pdf_list, output_path):
    """合并多个 PDF 文件"""
    merger = PdfMerger()
    for pdf in pdf_list:
        merger.append(pdf)
    merger.write(output_path)
    merger.close()


def main():
    # ======== 配置区域 ========
    pdf_dir = "./data_02_pdf"
    txt_dir = "./data_04_summary_txt"
    output_dir = "./data_05_final_pdf"
    os.makedirs(output_dir, exist_ok=True)
    # ==========================

    pdf_files = {os.path.splitext(f)[0]: os.path.join(pdf_dir, f)
                 for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")}
    txt_files = {os.path.splitext(f)[0]: os.path.join(txt_dir, f)
                 for f in os.listdir(txt_dir) if f.lower().endswith(".txt")}

    common_keys = sorted(set(pdf_files.keys()) & set(txt_files.keys()))

    if not common_keys:
        print("⚠️ 没有找到匹配的 PDF 和 TXT 文件。")
        return

    for key in common_keys:
        original_pdf = pdf_files[key]
        txt_file = txt_files[key]
        temp_pdf = os.path.join(output_dir, f"{key}_temp.pdf")
        output_pdf = os.path.join(output_dir, f"{key}_merge.pdf")

        print(f"📄 [{key}] 正在将 TXT 转换为 PDF...")
        txt_to_pdf(txt_file, temp_pdf)

        print(f"🔗 [{key}] 正在合并 PDF 文件...")
        merge_pdfs([original_pdf, temp_pdf], output_pdf)

        os.remove(temp_pdf)
        print(f"✅ [{key}] 合并完成 -> {output_pdf}")

    print("🎉 所有文件处理完成！")


if __name__ == "__main__":
    main()

```

---

## config_manager.py

**文件信息**:
- 行数: 406
- 大小: 11523 字节

```python
"""
配置管理模块 - 处理所有的配置参数和设置
提供配置验证、默认值管理、配置持久化等功能
"""

import os
import json
from typing import Any, Dict, Optional, List
from pathlib import Path
from datetime import datetime


class ConfigManager:
    """统一的配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "max_upload_size_mb": 100,
        "max_file_count": 50,
        "max_retries": 3,
        "retry_delay_seconds": 1.0,
        "script_timeout_seconds": 3600,
        "log_retention_days": 30,
        "enable_backup": True,
        "enable_compression": True,
        "thread_pool_size": 4,
        "disk_space_warning_mb": 500,
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file or os.path.join(
            os.path.dirname(__file__), "..", "conf", "config.json"
        )
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self) -> bool:
        """
        从文件加载配置
        
        Returns:
            是否成功加载
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # 合并文件配置和默认配置
                    self.config.update(file_config)
                return True
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return False
        return True
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否成功保存
        """
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        self.config[key] = value
    
    def reset_to_defaults(self) -> None:
        """重置为默认配置"""
        self.config = self.DEFAULT_CONFIG.copy()
    
    def validate_config(self) -> List[str]:
        """
        验证配置的合法性
        
        Returns:
            验证错误列表
        """
        errors = []
        
        # 检查数值范围
        if self.get("max_upload_size_mb", 0) < 1:
            errors.append("max_upload_size_mb 必须 >= 1")
        
        if self.get("max_file_count", 0) < 1:
            errors.append("max_file_count 必须 >= 1")
        
        if self.get("max_retries", 0) < 1:
            errors.append("max_retries 必须 >= 1")
        
        if self.get("retry_delay_seconds", 0) < 0:
            errors.append("retry_delay_seconds 必须 >= 0")
        
        if self.get("script_timeout_seconds", 0) < 1:
            errors.append("script_timeout_seconds 必须 >= 1")
        
        if self.get("log_retention_days", 0) < 1:
            errors.append("log_retention_days 必须 >= 1")
        
        if self.get("thread_pool_size", 0) < 1:
            errors.append("thread_pool_size 必须 >= 1")
        
        return errors


class FeatureFlags:
    """特性开关管理"""
    
    DEFAULT_FLAGS = {
        "enable_robust_logging": True,
        "enable_auto_retry": True,
        "enable_file_backup": True,
        "enable_compression": True,
        "enable_parallel_processing": False,
        "enable_health_check": True,
        "enable_performance_monitoring": False,
    }
    
    def __init__(self):
        """初始化特性开关"""
        self.flags = self.DEFAULT_FLAGS.copy()
    
    def is_enabled(self, feature: str) -> bool:
        """
        检查特性是否启用
        
        Args:
            feature: 特性名称
            
        Returns:
            特性是否启用
        """
        return self.flags.get(feature, False)
    
    def enable(self, feature: str) -> None:
        """启用特性"""
        self.flags[feature] = True
    
    def disable(self, feature: str) -> None:
        """禁用特性"""
        self.flags[feature] = False
    
    def toggle(self, feature: str) -> None:
        """切换特性状态"""
        self.flags[feature] = not self.flags.get(feature, False)


class PerformanceConfig:
    """性能相关的配置"""
    
    def __init__(self):
        """初始化性能配置"""
        self.start_time = datetime.now()
        self.metrics = {
            "total_files_processed": 0,
            "total_bytes_processed": 0,
            "total_errors": 0,
            "average_processing_time": 0.0,
        }
    
    def record_file_processing(self, file_size: int, duration: float,
                              success: bool = True) -> None:
        """
        记录文件处理信息
        
        Args:
            file_size: 文件大小（字节）
            duration: 处理时间（秒）
            success: 是否成功
        """
        self.metrics["total_files_processed"] += 1
        self.metrics["total_bytes_processed"] += file_size
        
        if not success:
            self.metrics["total_errors"] += 1
        
        # 更新平均处理时间
        current_avg = self.metrics["average_processing_time"]
        total_processed = self.metrics["total_files_processed"]
        
        self.metrics["average_processing_time"] = (
            (current_avg * (total_processed - 1) + duration) / total_processed
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        获取性能指标摘要
        
        Returns:
            性能指标字典
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "elapsed_seconds": elapsed,
            "total_files": self.metrics["total_files_processed"],
            "total_bytes_mb": self.metrics["total_bytes_processed"] / (1024 * 1024),
            "total_errors": self.metrics["total_errors"],
            "average_file_time_ms": self.metrics["average_processing_time"] * 1000,
            "throughput_mbps": (
                self.metrics["total_bytes_processed"] / (1024 * 1024) / elapsed
                if elapsed > 0 else 0
            ),
        }


class SecurityConfig:
    """安全性相关的配置"""
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {
        '.xlsx', '.xls', '.csv', '.json', '.txt', '.pdf', '.docx', '.doc'
    }
    
    # 禁止的文件名模式
    FORBIDDEN_PATTERNS = ['..', '~', '$', '\x00']
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """
        检查文件名是否安全
        
        Args:
            filename: 文件名
            
        Returns:
            文件名是否安全
        """
        # 检查禁止的模式
        for pattern in SecurityConfig.FORBIDDEN_PATTERNS:
            if pattern in filename:
                return False
        
        # 检查长度
        if len(filename) > 255:
            return False
        
        return True
    
    @staticmethod
    def is_safe_extension(filename: str) -> bool:
        """
        检查文件扩展名是否被允许
        
        Args:
            filename: 文件名
            
        Returns:
            扩展名是否被允许
        """
        ext = os.path.splitext(filename)[1].lower()
        return ext in SecurityConfig.ALLOWED_EXTENSIONS
    
    @staticmethod
    def validate_file(filename: str, check_extension: bool = True) -> List[str]:
        """
        验证文件安全性
        
        Args:
            filename: 文件名
            check_extension: 是否检查扩展名
            
        Returns:
            验证错误列表
        """
        errors = []
        
        if not SecurityConfig.is_safe_filename(filename):
            errors.append(f"不安全的文件名: {filename}")
        
        if check_extension and not SecurityConfig.is_safe_extension(filename):
            errors.append(f"不支持的文件类型: {filename}")
        
        return errors


class DataDirConfig:
    """数据目录配置管理"""
    
    # 标准的数据目录结构
    STANDARD_DIRS = {
        "ori": "data_00_ori",
        "csv": "data_01_csv",
        "pdf": "data_02_pdf",
        "json": "data_03_json",
        "txt": "data_04_summary_txt",
        "final": "data_05_final_pdf",
        "temp": "temp",
        "logs": "logs",
        "conf": "conf",
    }
    
    def __init__(self, base_dir: str):
        """
        初始化数据目录配置
        
        Args:
            base_dir: 基础目录
        """
        self.base_dir = base_dir
        self.dirs = self._build_dirs()
    
    def _build_dirs(self) -> Dict[str, str]:
        """构建目录字典"""
        dirs = {}
        for key, dirname in self.STANDARD_DIRS.items():
            dirs[key] = os.path.join(self.base_dir, dirname)
        return dirs
    
    def get(self, key: str) -> Optional[str]:
        """获取目录路径"""
        return self.dirs.get(key)
    
    def get_all(self) -> Dict[str, str]:
        """获取所有目录"""
        return self.dirs.copy()
    
    def ensure_all_dirs(self) -> bool:
        """确保所有目录都存在"""
        try:
            for path in self.dirs.values():
                Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"创建目录失败: {e}")
            return False


class CacheConfig:
    """缓存配置和管理"""
    
    def __init__(self, cache_dir: str, ttl_minutes: int = 60):
        """
        初始化缓存配置
        
        Args:
            cache_dir: 缓存目录
            ttl_minutes: 缓存过期时间（分钟）
        """
        self.cache_dir = cache_dir
        self.ttl_minutes = ttl_minutes
        self.cache = {}
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            elapsed = (datetime.now() - timestamp).total_seconds()
            if elapsed < self.ttl_minutes * 60:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        self.cache[key] = (value, datetime.now())
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()


# ==================== 导出 ====================
__all__ = [
    'ConfigManager',
    'FeatureFlags',
    'PerformanceConfig',
    'SecurityConfig',
    'DataDirConfig',
    'CacheConfig',
]

```

---

## robust_utils.py

**文件信息**:
- 行数: 909
- 大小: 28573 字节

```python
"""
鲁棒性工具库 - 提升代码可靠性和稳定性
包含验证、错误处理、日志记录、重试机制、数据清理等功能
"""

import os
import sys
import json
import logging
import traceback
import time
import shutil
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from functools import wraps
import threading
import queue


# ==================== 日志系统 ====================
class RobustLogger:
    """增强的日志系统，支持文件和控制台输出"""
    
    def __init__(self, log_dir: str = "./logs", log_name: str = "robust_log"):
        """
        初始化日志系统
        
        Args:
            log_dir: 日志目录
            log_name: 日志文件名前缀
        """
        self.log_dir = log_dir
        self.log_name = log_name
        self._ensure_dir(log_dir)
        self.logger = self._setup_logger()
        
    def _ensure_dir(self, directory: str) -> bool:
        """确保目录存在"""
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"无法创建日志目录: {e}")
            return False
            
    def _setup_logger(self) -> logging.Logger:
        """设置日志处理器"""
        logger = logging.getLogger(self.log_name)
        logger.setLevel(logging.DEBUG)
        
        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器
        log_file = os.path.join(
            self.log_dir,
            f"{self.log_name}_{datetime.now():%Y%m%d}.log"
        )
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"无法创建文件处理器: {e}")
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def debug(self, msg: str, **kwargs):
        """记录调试信息"""
        self.logger.debug(msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """记录信息"""
        self.logger.info(msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """记录警告"""
        self.logger.warning(msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """记录错误"""
        self.logger.error(msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """记录严重错误"""
        self.logger.critical(msg, **kwargs)


# ==================== 重试装饰器 ====================
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: Tuple = (Exception,)) -> Callable:
    """
    重试装饰器 - 在失败时自动重试
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数（每次失败延迟 * backoff）
        exceptions: 捕获的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = RobustLogger()
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    logger.debug(f"尝试执行 {func.__name__}，第 {attempt + 1}/{max_attempts} 次")
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"{func.__name__} 执行失败，原因: {str(e)}, "
                        f"将在 {current_delay}s 后重试"
                    )
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} 在 {max_attempts} 次尝试后仍失败")
            
            raise last_exception or Exception(f"Failed after {max_attempts} attempts")
        
        return wrapper
    return decorator


# ==================== 路径验证和清理 ====================
class PathValidator:
    """路径验证和管理工具"""
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = False, 
                     create: bool = False) -> bool:
        """
        验证路径的合法性和存在性
        
        Args:
            path: 路径字符串
            must_exist: 路径是否必须存在
            create: 路径不存在时是否创建
            
        Returns:
            路径是否有效
        """
        try:
            path_obj = Path(path)
            
            # 检查路径字符合法性
            if not path:
                return False
            
            # 路径必须存在的检查
            if must_exist and not path_obj.exists():
                if create:
                    path_obj.mkdir(parents=True, exist_ok=True)
                    return True
                return False
            
            return True
            
        except (ValueError, OSError, TypeError) as e:
            return False
    
    @staticmethod
    def safe_path_join(*parts: str) -> str:
        """
        安全的路径连接
        
        Args:
            *parts: 路径片段
            
        Returns:
            连接后的路径
        """
        try:
            result = os.path.join(*parts)
            # 规范化路径
            return os.path.normpath(result)
        except Exception:
            return ""
    
    @staticmethod
    def ensure_directory(path: str, max_retries: int = 3) -> bool:
        """
        确保目录存在，带重试机制
        
        Args:
            path: 目录路径
            max_retries: 最大重试次数
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        for attempt in range(max_retries):
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
                logger.debug(f"目录已确保: {path}")
                return True
            except Exception as e:
                logger.warning(f"创建目录 {path} 失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(0.5)
        
        logger.error(f"无法创建目录: {path}")
        return False


# ==================== 文件操作工具 ====================
class FileOperationHelper:
    """文件操作的鲁棒性辅助工具"""
    
    @staticmethod
    @retry(max_attempts=3, delay=0.5)
    def safe_read_file(filepath: str, encoding: str = 'utf-8', 
                      default: str = '') -> str:
        """
        安全读取文件内容
        
        Args:
            filepath: 文件路径
            encoding: 文件编码
            default: 读取失败时的默认值
            
        Returns:
            文件内容或默认值
        """
        logger = RobustLogger()
        
        try:
            if not Path(filepath).exists():
                logger.warning(f"文件不存在: {filepath}")
                return default
            
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            
            logger.debug(f"成功读取文件: {filepath}")
            return content
            
        except UnicodeDecodeError:
            logger.warning(f"文件编码错误: {filepath}，尝试使用其他编码")
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    return f.read()
            except Exception:
                return default
        except Exception as e:
            logger.error(f"读取文件失败: {filepath}, 原因: {e}")
            return default
    
    @staticmethod
    @retry(max_attempts=3, delay=0.5)
    def safe_write_file(filepath: str, content: str, encoding: str = 'utf-8',
                       backup: bool = True) -> bool:
        """
        安全写入文件内容
        
        Args:
            filepath: 文件路径
            content: 文件内容
            encoding: 文件编码
            backup: 覆盖前是否备份
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        try:
            # 确保目录存在
            PathValidator.ensure_directory(os.path.dirname(filepath))
            
            # 备份原文件
            if backup and Path(filepath).exists():
                backup_path = f"{filepath}.bak"
                try:
                    shutil.copy2(filepath, backup_path)
                    logger.debug(f"已备份文件: {backup_path}")
                except Exception as e:
                    logger.warning(f"备份失败: {e}")
            
            # 写入新内容
            with open(filepath, 'w', encoding=encoding) as f:
                f.write(content)
            
            logger.debug(f"成功写入文件: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"写入文件失败: {filepath}, 原因: {e}")
            return False
    
    @staticmethod
    def get_file_hash(filepath: str, algorithm: str = 'md5') -> Optional[str]:
        """
        计算文件哈希值
        
        Args:
            filepath: 文件路径
            algorithm: 哈希算法 ('md5', 'sha1', 'sha256')
            
        Returns:
            哈希值或 None
        """
        logger = RobustLogger()
        
        try:
            if not Path(filepath).exists():
                logger.warning(f"文件不存在: {filepath}")
                return None
            
            hash_obj = hashlib.new(algorithm)
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"计算文件哈希失败: {filepath}, 原因: {e}")
            return None
    
    @staticmethod
    def safe_copy_file(src: str, dst: str, overwrite: bool = False) -> bool:
        """
        安全复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 目标文件存在时是否覆盖
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        try:
            if not Path(src).exists():
                logger.error(f"源文件不存在: {src}")
                return False
            
            if Path(dst).exists() and not overwrite:
                logger.warning(f"目标文件已存在，且 overwrite=False: {dst}")
                return False
            
            PathValidator.ensure_directory(os.path.dirname(dst))
            shutil.copy2(src, dst)
            logger.debug(f"成功复制文件: {src} -> {dst}")
            return True
            
        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            return False
    
    @staticmethod
    def safe_remove_file(filepath: str, force: bool = False) -> bool:
        """
        安全删除文件
        
        Args:
            filepath: 文件路径
            force: 是否强制删除（忽略权限问题）
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        try:
            if not Path(filepath).exists():
                logger.warning(f"文件不存在，无需删除: {filepath}")
                return True
            
            os.remove(filepath)
            logger.debug(f"成功删除文件: {filepath}")
            return True
            
        except PermissionError:
            if force:
                try:
                    os.chmod(filepath, 0o777)
                    os.remove(filepath)
                    logger.debug(f"强制删除文件成功: {filepath}")
                    return True
                except Exception as e:
                    logger.error(f"强制删除失败: {filepath}, 原因: {e}")
                    return False
            else:
                logger.error(f"权限不足，无法删除: {filepath}")
                return False
        except Exception as e:
            logger.error(f"删除文件失败: {filepath}, 原因: {e}")
            return False


# ==================== JSON 操作工具 ====================
class JSONHelper:
    """JSON 文件的安全处理"""
    
    @staticmethod
    def safe_load_json(filepath: str, default: Optional[Dict] = None) -> Dict:
        """
        安全加载 JSON 文件
        
        Args:
            filepath: JSON 文件路径
            default: 加载失败时的默认值
            
        Returns:
            JSON 对象或默认值
        """
        logger = RobustLogger()
        default = default or {}
        
        try:
            content = FileOperationHelper.safe_read_file(filepath, default='{}')
            data = json.loads(content)
            
            if not isinstance(data, dict):
                logger.warning(f"JSON 数据不是字典类型: {filepath}")
                return default
            
            logger.debug(f"成功加载 JSON: {filepath}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {filepath}, 原因: {e}")
            return default
        except Exception as e:
            logger.error(f"加载 JSON 失败: {filepath}, 原因: {e}")
            return default
    
    @staticmethod
    def safe_save_json(filepath: str, data: Dict, pretty: bool = True,
                      backup: bool = True) -> bool:
        """
        安全保存 JSON 文件
        
        Args:
            filepath: JSON 文件路径
            data: 数据字典
            pretty: 是否格式化输出
            backup: 覆盖前是否备份
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        try:
            # 验证数据
            if not isinstance(data, dict):
                logger.error(f"数据不是字典类型: {type(data)}")
                return False
            
            # 尝试序列化，检查是否有不可序列化的对象
            json.dumps(data)
            
            # 保存文件
            indent = 2 if pretty else None
            content = json.dumps(data, ensure_ascii=False, indent=indent)
            
            return FileOperationHelper.safe_write_file(
                filepath, content, backup=backup
            )
            
        except TypeError as e:
            logger.error(f"JSON 序列化失败: {e}")
            return False
        except Exception as e:
            logger.error(f"保存 JSON 失败: {filepath}, 原因: {e}")
            return False
    
    @staticmethod
    def validate_json_structure(data: Dict, schema: Dict) -> bool:
        """
        验证 JSON 数据结构
        
        Args:
            data: 要验证的数据
            schema: 验证模式字典
            
        Returns:
            是否符合结构
        """
        logger = RobustLogger()
        
        try:
            for key, expected_type in schema.items():
                if key not in data:
                    logger.warning(f"缺少必需字段: {key}")
                    return False
                
                if not isinstance(data[key], expected_type):
                    logger.warning(
                        f"字段类型不匹配: {key}, "
                        f"期望 {expected_type}, 实际 {type(data[key])}"
                    )
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证 JSON 结构失败: {e}")
            return False


# ==================== 数据验证工具 ====================
class DataValidator:
    """数据验证和清理"""
    
    @staticmethod
    def is_empty(value: Any) -> bool:
        """检查值是否为空"""
        if value is None:
            return True
        if isinstance(value, (str, list, dict)):
            return len(value) == 0
        return False
    
    @staticmethod
    def clean_string(text: str, strip: bool = True, 
                    remove_empty_lines: bool = False) -> str:
        """
        清理字符串
        
        Args:
            text: 输入文本
            strip: 是否去除前后空格
            remove_empty_lines: 是否移除空行
            
        Returns:
            清理后的文本
        """
        if not isinstance(text, str):
            return ""
        
        if strip:
            text = text.strip()
        
        if remove_empty_lines:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
        
        return text
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证电子邮件格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证电话号码格式（中国）"""
        import re
        # 简单的中国电话号码验证
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def limit_string_length(text: str, max_length: int, 
                           suffix: str = '...') -> str:
        """
        限制字符串长度
        
        Args:
            text: 文本
            max_length: 最大长度
            suffix: 截断后缀
            
        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix


# ==================== 目录操作工具 ====================
class DirectoryHelper:
    """目录操作的鲁棒性工具"""
    
    @staticmethod
    def safe_clean_directory(directory: str, keep_dirs: Optional[List] = None,
                            keep_files: Optional[List] = None) -> bool:
        """
        安全清理目录（保留指定文件/文件夹）
        
        Args:
            directory: 目录路径
            keep_dirs: 保留的子目录列表
            keep_files: 保留的文件列表
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        keep_dirs = keep_dirs or []
        keep_files = keep_files or []
        
        try:
            if not Path(directory).exists():
                logger.warning(f"目录不存在: {directory}")
                return True
            
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                # 检查是否应该保留
                if item in keep_dirs or item in keep_files:
                    logger.debug(f"保留项目: {item}")
                    continue
                
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    logger.debug(f"已删除: {item_path}")
                except Exception as e:
                    logger.warning(f"删除失败: {item_path}, 原因: {e}")
            
            logger.debug(f"成功清理目录: {directory}")
            return True
            
        except Exception as e:
            logger.error(f"清理目录失败: {directory}, 原因: {e}")
            return False
    
    @staticmethod
    def get_directory_size(directory: str) -> int:
        """
        获取目录大小（字节）
        
        Args:
            directory: 目录路径
            
        Returns:
            目录大小（字节）
        """
        logger = RobustLogger()
        total_size = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except Exception:
                        pass
            
            return total_size
            
        except Exception as e:
            logger.error(f"计算目录大小失败: {directory}, 原因: {e}")
            return 0
    
    @staticmethod
    def list_files(directory: str, pattern: Optional[str] = None,
                  recursive: bool = False) -> List[str]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            pattern: 文件名模式（glob）
            recursive: 是否递归
            
        Returns:
            文件列表
        """
        logger = RobustLogger()
        files = []
        
        try:
            path_obj = Path(directory)
            
            if not path_obj.exists():
                logger.warning(f"目录不存在: {directory}")
                return files
            
            search_pattern = pattern or "*"
            
            if recursive:
                files = [str(f) for f in path_obj.rglob(search_pattern) 
                        if f.is_file()]
            else:
                files = [str(f) for f in path_obj.glob(search_pattern) 
                        if f.is_file()]
            
            logger.debug(f"找到 {len(files)} 个文件: {directory}")
            return files
            
        except Exception as e:
            logger.error(f"列出文件失败: {directory}, 原因: {e}")
            return files


# ==================== 执行环境检查 ====================
class EnvironmentChecker:
    """检查执行环境的各项条件"""
    
    @staticmethod
    def check_python_version(min_version: Tuple[int, ...] = (3, 6)) -> bool:
        """检查 Python 版本"""
        logger = RobustLogger()
        current = sys.version_info[:len(min_version)]
        
        if current >= min_version:
            logger.info(f"Python 版本: {sys.version.split()[0]} (满足最低要求)")
            return True
        else:
            logger.error(
                f"Python 版本过低: {sys.version.split()[0]}, "
                f"需要至少 {'.'.join(map(str, min_version))}"
            )
            return False
    
    @staticmethod
    def check_disk_space(directory: str, min_free_mb: int = 100) -> bool:
        """检查磁盘空间"""
        logger = RobustLogger()
        
        try:
            import shutil
            stat = shutil.disk_usage(directory)
            free_mb = stat.free / (1024 * 1024)
            
            if free_mb >= min_free_mb:
                logger.info(f"磁盘空间充足: {free_mb:.2f} MB")
                return True
            else:
                logger.warning(f"磁盘空间不足: {free_mb:.2f} MB (需要 {min_free_mb} MB)")
                return False
                
        except Exception as e:
            logger.error(f"检查磁盘空间失败: {e}")
            return False
    
    @staticmethod
    def check_module_availability(*module_names: str) -> Dict[str, bool]:
        """检查模块是否可用"""
        logger = RobustLogger()
        availability = {}
        
        for module_name in module_names:
            try:
                __import__(module_name)
                availability[module_name] = True
                logger.debug(f"模块可用: {module_name}")
            except ImportError:
                availability[module_name] = False
                logger.warning(f"模块不可用: {module_name}")
        
        return availability
    
    @staticmethod
    def check_file_permissions(filepath: str, need_read: bool = False,
                             need_write: bool = False) -> bool:
        """检查文件权限"""
        logger = RobustLogger()
        
        try:
            path_obj = Path(filepath)
            
            if not path_obj.exists():
                logger.warning(f"文件不存在: {filepath}")
                return False
            
            if need_read and not os.access(filepath, os.R_OK):
                logger.error(f"没有读权限: {filepath}")
                return False
            
            if need_write and not os.access(filepath, os.W_OK):
                logger.error(f"没有写权限: {filepath}")
                return False
            
            logger.debug(f"文件权限检查通过: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"检查文件权限失败: {e}")
            return False


# ==================== 异常处理工具 ====================
class ExceptionHandler:
    """异常处理和错误报告"""
    
    @staticmethod
    def get_exception_details(exc: Exception) -> Dict[str, Any]:
        """获取异常的详细信息"""
        return {
            'type': type(exc).__name__,
            'message': str(exc),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now(timezone(timedelta(hours=8))).isoformat()
        }
    
    @staticmethod
    def safe_execute(func: Callable, *args, logger: Optional[RobustLogger] = None,
                    **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        安全执行函数
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            logger: 日志记录器
            **kwargs: 关键字参数
            
        Returns:
            (是否成功, 返回值/错误信息, 异常对象)
        """
        if logger is None:
            logger = RobustLogger()
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"成功执行函数: {func.__name__}")
            return True, result, None
        except Exception as e:
            details = ExceptionHandler.get_exception_details(e)
            logger.error(f"执行函数失败: {func.__name__}\n{details['traceback']}")
            return False, details, e


# ==================== 初始化检查 ====================
def run_startup_checks(data_dirs: Dict[str, str]) -> bool:
    """
    启动时的综合检查
    
    Args:
        data_dirs: 数据目录字典
        
    Returns:
        所有检查是否通过
    """
    logger = RobustLogger()
    logger.info("=" * 50)
    logger.info("启动环境检查")
    logger.info("=" * 50)
    
    all_passed = True
    
    # 检查 Python 版本
    if not EnvironmentChecker.check_python_version((3, 6)):
        all_passed = False
    
    # 检查磁盘空间
    if not EnvironmentChecker.check_disk_space(".", min_free_mb=100):
        all_passed = False
    
    # 创建数据目录
    logger.info("创建数据目录...")
    for key, path in data_dirs.items():
        if PathValidator.ensure_directory(path):
            logger.info(f"✓ {key}: {path}")
        else:
            logger.error(f"✗ {key}: {path}")
            all_passed = False
    
    logger.info("=" * 50)
    if all_passed:
        logger.info("✓ 所有检查已通过")
    else:
        logger.warning("⚠ 部分检查未通过，请检查配置")
    logger.info("=" * 50)
    
    return all_passed


# ==================== 导出函数 ====================
__all__ = [
    'RobustLogger',
    'retry',
    'PathValidator',
    'FileOperationHelper',
    'JSONHelper',
    'DataValidator',
    'DirectoryHelper',
    'EnvironmentChecker',
    'ExceptionHandler',
    'run_startup_checks',
]

```

---

## 📊 统计信息

| 指标 | 数值 |
|------|------|
| 文件总数 | 8 |
| 代码总行数 | 1864 |
| 总大小 | 60,073 字节 (58.67 KB) |
| 平均行数 | 233 |

---

**备注**: 本文档为软著申请用途，包含完整的源代码。
