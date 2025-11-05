import pandas as pd
import json
import os

# ========== 1️⃣ 文件路径（请修改为你自己的） ==========
input_dir = "/home/huyanwei/projects/parse_data/data_01_csv"  # 输入文件夹
output_dir = "/home/huyanwei/projects/parse_data/data_03_json"  # 输出文件夹

file_检查 = f"{input_dir}/检查信息.csv"
file_检验 = f"{input_dir}/检验信息.csv"
file_病案 = f"{input_dir}/病案首页.csv"
file_医嘱 = f"{input_dir}/医嘱信息.csv"


# ========== 2️⃣ 选择保留的字段（可按需修改） ==========
FIELDS = {
    "病案首页" :[
        "病案号","住院次数","入院日期","出院日期","性别","出生日期","年龄","出院科室",
        "出院诊断编码","出院诊断","出院诊断1编码","出院诊断1名称","出院诊断2编码","出院诊断2名称",
        "出院诊断3编码","出院诊断3名称","过敏药物","手术治疗及操作编码","手术治疗及操作名称","操作日期",
        "住院总费用","住院总费用其中自付金额","一般医疗服务费","一般治疗操作费","护理费",
        "综合医疗服务类其他费用","病理诊断费","实验室诊断费","影像学诊断费","临床诊断项目费",
        "非手术治疗项目费","其中：临床物理治疗费","手术治疗费","其中：麻醉费","其中：手术费",
        "康复费","中医治疗费","西药费","其中：抗菌药物费","中成药费","中草药费","血费",
        "白蛋白类制品费","球蛋白类制品费","凝血因子类制品费","细胞因子类制品费",
        "检查用一次性医用材料费","治疗用一次性医用材料费","手术用一次性医用材料费","其他费："
    ],
    "检验信息":[
        "病案号","检验项目","检验项目名称","检验结果","检验标志","阴阳性","单位","标本","采集时间","报告日期"
    ],
    "检查信息": [
        "病案号","医嘱名称","检查结果","报告时间"
    ],
    "医嘱信息": [
        "病案号","医嘱类型","医嘱分类","医嘱名称","医嘱开始时间","医嘱结束时间","医嘱状态名称","费用分类名称","药品规格","药品剂型名称"
    ]                    
}

# ========== 3️⃣ 自动识别编码读取 CSV ==========
def read_csv_auto(path):
    encodings = ["utf-8-sig", "gbk", "gb2312", "utf-8"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
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
        record["病案首页"] = df_case_sub[cols].iloc[0].dropna().to_dict()

    # 检查信息
    df_check_sub = df_check[df_check["病案号"] == case_id]
    if not df_check_sub.empty:
        cols = [c for c in FIELDS["检查信息"] if c in df_check_sub.columns]
        record["检查信息"] = df_check_sub[cols].dropna(axis=1, how="all").to_dict(orient="records")

    # 检验信息
    df_test_sub = df_test[df_test["病案号"] == case_id]
    if not df_test_sub.empty:
        cols = [c for c in FIELDS["检验信息"] if c in df_test_sub.columns]
        record["检验信息"] = df_test_sub[cols].dropna(axis=1, how="all").to_dict(orient="records")

    # 医嘱信息
    df_order_sub = df_order[df_order["病案号"] == case_id]
    if not df_order_sub.empty:
        cols = [c for c in FIELDS["医嘱信息"] if c in df_order_sub.columns]
        record["医嘱信息"] = df_order_sub[cols].dropna(axis=1, how="all").to_dict(orient="records")

    return record

# ========== 8️⃣ 遍历导出每个病案号 ==========
for case_id in sorted(all_case_ids):
    patient_json = build_patient_json(case_id)
    out_path = os.path.join(output_dir, f"{case_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(patient_json, f, ensure_ascii=False, indent=2)
    print(f"✅ 已生成：{out_path}")

print(f"\n🎉 所有病案号已成功导出到文件夹：{os.path.abspath(output_dir)}")
