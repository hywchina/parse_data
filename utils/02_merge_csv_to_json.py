import pandas as pd
import json
import os
import numpy as np

# ========== 🎯 超参数配置 ==========
# 文件路径
INPUT_DIR = "./data_01_csv"
OUTPUT_DIR = "./data_02_json"
HEADERS_FILE = "./conf/headers.json"

# 文件名映射（中文名 -> 文件名）
CSV_FILES = {
    "病案首页": "病案首页.csv",
    "检查报告": "检查报告.csv",
    "检验报告": "检验报告.csv",
    "入院记录": "入院记录.csv",
    "医嘱明细": "医嘱明细.csv",
}

# 字段名映射（用于 JSON 输出的键名）
FIELD_KEYS = {
    "病案首页": "病案首页",
    "检查报告": "检查报告",
    "检验报告": "检验报告",
    "入院记录": "入院记录",
    "医嘱明细": "医嘱明细",
}

# 文档类型顺序（病案首页为单行，其余为多行）
SINGLE_ROW_TYPES = ["病案首页"]
MULTI_ROW_TYPES = ["检查报告", "检验报告", "入院记录", "医嘱明细"]
ALL_DOC_TYPES = list(CSV_FILES.keys())

# 其他配置
CASE_ID_COL = "病案号"  # 病案号列名
CASE_ID_WIDTH = 6  # 病案号位数
NAN_PLACEHOLDER = None  # NaN 值替代
ENCODING_LIST = ["utf-8-sig", "gbk", "gb2312", "utf-8"]  # CSV 编码尝试列表

# 调试配置
DEBUG_MODE = False  # 是否开启调试模式
DEBUG_CASE_ID = "000006"  # 需要检查的病案号（6位数字）

# ========== 1️⃣ 加载配置 ==========
with open(HEADERS_FILE, "r", encoding="utf-8") as f:
    FIELDS = json.load(f)

# 读取所有 CSV 文件
dataframes = {}

# ========== 2️⃣ 辅助函数 ==========
def read_csv_auto(path):
    """自动识别编码读取 CSV"""
    for enc in ENCODING_LIST:
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            return df
        except Exception:
            continue
    raise ValueError(f"无法读取文件：{path}")

def filter_nan_value(value):
    """过滤单个值中的 NaN"""
    if isinstance(value, float) and np.isnan(value):
        return False
    return True

def clean_record_dict(record_dict):
    """清理字典中的 NaN 值"""
    return {k: v for k, v in record_dict.items() if filter_nan_value(v)}

def normalize_case_id(series):
    """将病案号统一为指定位数（前补0）"""
    return series.astype(str).str.strip().str.zfill(CASE_ID_WIDTH)

# ========== 3️⃣ 自动识别编码读取 CSV ==========
def read_csv_auto(path):
    encodings = ENCODING_LIST
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            return df
        except Exception:
            continue
    raise ValueError(f"无法读取文件：{path}")

# ========== 4️⃣ 读取数据 ==========
for doc_type, filename in CSV_FILES.items():
    file_path = os.path.join(INPUT_DIR, filename)
    dataframes[doc_type] = read_csv_auto(file_path)
    print(f"✅ 已读取 {doc_type}: {file_path}")

# ========== 5️⃣ 统一病案号为指定位数 ==========
for doc_type in dataframes:
    if CASE_ID_COL in dataframes[doc_type].columns:
        dataframes[doc_type][CASE_ID_COL] = normalize_case_id(dataframes[doc_type][CASE_ID_COL])
    else:
        print(f"⚠️ 警告：{doc_type} 中未找到 '{CASE_ID_COL}' 列")

# ========== 6️⃣ 获取所有病案号 ==========
all_case_ids = set()
for doc_type, df in dataframes.items():
    if CASE_ID_COL in df.columns:
        all_case_ids.update(df[CASE_ID_COL].unique())

# ========== 7️⃣ 生成输出文件夹 ==========
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== 8️⃣ 主逻辑函数 ==========
def process_single_record(df, doc_type, case_id, is_single_row=False):
    """
    处理单个文档类型的记录
    
    Args:
        df: DataFrame
        doc_type: 文档类型（如"病案首页"、"检查报告"等）
        case_id: 病案号
        is_single_row: 是否只返回单行（对病案首页）
    
    Returns:
        如果 is_single_row=True，返回字典；否则返回列表
    """
    df_sub = df[df[CASE_ID_COL] == case_id]
    
    if df_sub.empty:
        return {} if is_single_row else []
    
    # 获取该文档类型的字段
    if doc_type not in FIELDS:
        print(f"⚠️ 警告：FIELDS 中未找到 '{doc_type}'")
        return {} if is_single_row else []
    
    cols = [c for c in FIELDS[doc_type] if c in df_sub.columns]
    cols = [c for c in cols if c != CASE_ID_COL]  # 移除病案号字段
    
    if is_single_row:
        # 病案首页：返回单个字典
        record_dict = df_sub[cols].iloc[0].to_dict()
        return clean_record_dict(record_dict)
    else:
        # 其他：返回列表
        records = df_sub[cols].to_dict(orient="records")
        cleaned_records = []
        for rec in records:
            cleaned_rec = clean_record_dict(rec)
            if cleaned_rec:  # 只添加非空记录
                cleaned_records.append(cleaned_rec)
        return cleaned_records

def build_patient_json(case_id):
    """构建单个患者的完整 JSON"""
    # 初始化记录：病案首页为字典，其他为列表
    record = {field_key: {} if doc_type in SINGLE_ROW_TYPES else [] 
              for doc_type, field_key in FIELD_KEYS.items()}
    
    # 处理单行文档类型
    for doc_type in SINGLE_ROW_TYPES:
        if doc_type in dataframes:
            record[FIELD_KEYS[doc_type]] = process_single_record(
                dataframes[doc_type], doc_type, case_id, is_single_row=True
            )
    
    # 处理多行文档类型
    for doc_type in MULTI_ROW_TYPES:
        if doc_type in dataframes:
            record[FIELD_KEYS[doc_type]] = process_single_record(
                dataframes[doc_type], doc_type, case_id, is_single_row=False
            )
    
    return record

def check_case_id_data(case_id):
    """
    检查指定病案号的数据处理情况
    
    功能：
    1. 打印生成的 JSON 数据
    2. 打印原始 CSV 中该病案号的所有数据
    
    Args:
        case_id: 病案号（字符串，如 "000006"）
    """
    print("=" * 100)
    print(f"🔍 检查病案号: {case_id}")
    print("=" * 100)
    
    # 1. 生成并打印 JSON 数据
    print(f"\n{'=' * 50}")
    print("📋 生成的 JSON 数据：")
    print(f"{'=' * 50}")
    patient_json = build_patient_json(case_id)
    print(json.dumps(patient_json, ensure_ascii=False, indent=2))
    
    # 2. 打印原始 CSV 数据
    print(f"\n{'=' * 50}")
    print("📊 原始 CSV 数据：")
    print(f"{'=' * 50}")
    
    for doc_type in ALL_DOC_TYPES:
        if doc_type not in dataframes:
            continue
            
        df = dataframes[doc_type]
        
        # 查找该病案号的数据
        if CASE_ID_COL not in df.columns:
            print(f"\n⚠️  {doc_type}: 未找到 '{CASE_ID_COL}' 列")
            continue
        
        df_case = df[df[CASE_ID_COL] == case_id]
        
        if df_case.empty:
            print(f"\n❌ {doc_type}: 无数据")
        else:
            print(f"\n✅ {doc_type}: 共 {len(df_case)} 条记录")
            print("-" * 80)
            
            # 打印详细数据
            for idx, row in df_case.iterrows():
                print(f"\n  记录 #{idx + 1}:")
                for col in df_case.columns:
                    value = row[col]
                    # 跳过 NaN 值
                    if pd.isna(value):
                        continue
                    print(f"    {col}: {value}")
            print("-" * 80)
    
    print(f"\n{'=' * 100}")
    print(f"✅ 病案号 {case_id} 检查完成")
    print("=" * 100)


# ========== 9️⃣ 调试模式检查 ==========
if DEBUG_MODE:
    print("\n🐛 调试模式已开启")
    check_case_id_data(DEBUG_CASE_ID)
    print("\n提示：如需继续生成所有 JSON 文件，请将 DEBUG_MODE 设置为 False\n")
    exit(0)

# ========== 🔟 遍历导出每个病案号 ==========
print(f"\n开始生成 JSON 文件，共 {len(all_case_ids)} 个病案号...")
for idx, case_id in enumerate(sorted(all_case_ids), 1):
    patient_json = build_patient_json(case_id)
    out_path = os.path.join(OUTPUT_DIR, f"{case_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(patient_json, f, ensure_ascii=False, indent=2)
    
    if idx % 50 == 0:
        print(f"✅ 已生成 {idx}/{len(all_case_ids)} 个文件")

print(f"\n🎉 完成！所有 {len(all_case_ids)} 个病案号已成功导出到：{os.path.abspath(OUTPUT_DIR)}")