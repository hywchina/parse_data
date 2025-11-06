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
