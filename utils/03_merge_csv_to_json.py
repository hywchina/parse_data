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