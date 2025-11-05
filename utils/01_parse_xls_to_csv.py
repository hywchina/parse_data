import os
import pandas as pd

# ========== 路径配置 ==========
data_ori = "./data_00_ori"
data_csv = "./data_01_csv"
os.makedirs(data_csv, exist_ok=True)


def excel_to_csv(data_ori, data_csv):
    # 遍历目录下所有文件
    for filename in os.listdir(data_ori):
        if filename.lower().endswith(('.xlsx', '.xls')):
            file_path = os.path.join(data_ori, filename)
            print(f"正在处理: {file_path}")

            # 读取 Excel 文件中的所有 sheet
            try:
                excel_file = pd.ExcelFile(file_path)
            except Exception as e:
                print(f"❌ 无法读取文件 {filename}: {e}")
                continue

            sheet_names = excel_file.sheet_names
            single_sheet = len(sheet_names) == 1  # 只含一个 sheet 时为 True

            for sheet_name in sheet_names:
                try:
                    # 尝试读取表格（含表头）
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)

                    # 检查是否有表头（列名为 Unnamed 或 NaN）
                    if df.columns.isnull().any() or all(str(col).startswith("Unnamed") for col in df.columns):
                        # 再读一次，不指定表头
                        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                        # 自动生成列名
                        df.columns = [f"Column_{i+1}" for i in range(df.shape[1])]

                    # 输出文件名
                    base_name = os.path.splitext(filename)[0]
                    if single_sheet:
                        csv_filename = f"{base_name}.csv"
                    else:
                        csv_filename = f"{base_name}_{sheet_name}.csv"

                    csv_path = os.path.join(data_csv, csv_filename)

                    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    print(f"✅ 已生成: {csv_path}")

                except Exception as e:
                    print(f"⚠️ 处理 {filename} 的表 {sheet_name} 时出错: {e}")


if __name__ == '__main__':
    excel_to_csv(data_ori, data_csv)
