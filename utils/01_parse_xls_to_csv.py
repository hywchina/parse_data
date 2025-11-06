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
