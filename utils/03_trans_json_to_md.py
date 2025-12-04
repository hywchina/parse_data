import json
import os
from datetime import datetime

# ========== 🎯 超参数配置 ==========
INPUT_DIR = "./data_02_json"  # JSON 文件输入目录
OUTPUT_DIR = "./data_03_md"  # Markdown 文件输出目录

# 文档类型配置
SINGLE_ROW_TYPE = "病案首页"
MULTI_ROW_TYPES = ["入院记录", "检验报告", "检查报告", "医嘱明细"]

# 病案首页显示字段（按重要性排序）
CASE_INFO_FIELDS = [
    "就诊号", "登记号", "住院次数",
    "入院时间", "出院时间",
    "性别", "年龄（岁）",
    "出院病房",
    "出院主要诊断编码", "出院主要诊断名称", "出院主要诊断入院病情",
]

# 表头配置（从 headers.json 读取）
HEADERS_FILE = "./conf/headers.json"
HEADERS_CONFIG = {}  # 动态加载

# 时间字段（用于排序）
TIME_FIELDS = ["检查时间", "检验时间", "医嘱时间", "开始时间", "报告时间", "时间"]

# 调试配置
DEBUG_MODE = False
DEBUG_CASE_ID = "000030"


# ========== 辅助函数 ==========
def load_headers_config():
    """从 headers.json 加载表头配置"""
    global HEADERS_CONFIG
    try:
        with open(HEADERS_FILE, 'r', encoding='utf-8') as f:
            HEADERS_CONFIG = json.load(f)
        print(f"✅ 已加载表头配置: {HEADERS_FILE}")
    except FileNotFoundError:
        print(f"❌ 找不到文件: {HEADERS_FILE}")
        # 使用默认值作为备选
        HEADERS_CONFIG = {
            "检查报告": ["检查日期", "检查项目名称", "检查描述", "检查结果"],
            "检验报告": ["检验项目", "结果", "结果提示", "参考范围", "审核日期"],
            "医嘱明细": ["医嘱开始日期", "医嘱开始时间", "医嘱类型", "医嘱编码", "医嘱名称", "医嘱子类", "开单科室", "开单医师", "医嘱停止日期", "医嘱停止时间"]
        }
        print(f"⚠️  使用默认表头配置")
    except Exception as e:
        print(f"❌ 读取表头配置出错: {e}")
        HEADERS_CONFIG = {}



def extract_datetime(record, time_fields=TIME_FIELDS):
    """从记录中提取时间字段用于排序"""
    for field in time_fields:
        if field in record and record[field]:
            try:
                # 尝试解析时间
                return datetime.strptime(str(record[field])[:19], "%Y-%m-%d %H:%M:%S")
            except:
                try:
                    return datetime.strptime(str(record[field])[:10], "%Y-%m-%d")
                except:
                    continue
    return datetime.min  # 如果没有时间字段，返回最小时间


def format_field_value(key, value):
    """格式化字段值用于显示"""
    if value is None or value == "":
        return ""
    
    # 特殊字段处理
    if "时间" in key or "日期" in key:
        return f"**{key}**：`{value}`"
    elif "诊断" in key or "病情" in key:
        return f"**{key}**：**{value}**"
    else:
        return f"**{key}**：{value}"


def generate_case_header(case_data):
    """生成病案首页内容"""
    lines = []
    lines.append("### 一、基本信息（病案首页）\n")
    
    # 重要字段
    for field in CASE_INFO_FIELDS:
        if field in case_data and case_data[field]:
            formatted = format_field_value(field, case_data[field])
            if formatted:
                lines.append(f"- {formatted}")
    
    # 其他字段
    lines.append("\n#### 其他信息")
    for key, value in case_data.items():
        if key not in CASE_INFO_FIELDS and value:
            formatted = format_field_value(key, value)
            if formatted:
                lines.append(f"- {formatted}")
    
    return "\n".join(lines)


def generate_admission_record(records):
    """生成入院记录内容"""
    if not records:
        return "### 二、入院记录\n\n> 无数据\n"
    
    lines = []
    lines.append("### 二、入院记录\n")
    
    for idx, record in enumerate(records, 1):
        if len(records) > 1:
            lines.append(f"#### 入院记录 #{idx}\n")
        
        for key, value in record.items():
            formatted = format_field_value(key, value)
            if formatted:
                lines.append(f"- {formatted}")
        lines.append("")
    
    return "\n".join(lines)


def generate_test_reports(records, title="检验报告", fields=None):
    """
    生成检验报告内容（直接用表格展示）
    
    Args:
        records: 报告记录列表
        title: 标题
        fields: 要显示的字段列表（如果为None，则从HEADERS_CONFIG读取）
    """
    if not records:
        return f"### 三、{title}\n\n> 无数据\n"
    
    if fields is None:
        # 从 headers.json 中的"检验报告"字段列表读取
        fields = HEADERS_CONFIG.get("检验报告", [])
        if not fields:
            # 备选方案：使用默认字段
            fields = ["检验项目", "结果", "结果提示", "参考范围", "审核日期"]
    
    lines = []
    lines.append(f"### 三、{title}（共 {len(records)} 条）\n")
    
    # 按时间排序
    sorted_records = sorted(records, key=extract_datetime)
    
    # 生成表格头
    table_headers = ["#"] + fields
    lines.append("| " + " | ".join(table_headers) + " |")
    lines.append("|" + "|".join(["---"] * len(table_headers)) + "|")
    
    # 生成表格行
    for idx, record in enumerate(sorted_records, 1):
        row = [str(idx)]
        for field in fields:
            value = record.get(field, "-")
            # 清理表格值
            clean_value = clean_table_value(value)
            row.append(clean_value)
        lines.append("| " + " | ".join(row) + " |")
    
    return "\n".join(lines)


def clean_table_value(value):
    """清理表格单元格中的特殊字符（换行符、多余空格等）"""
    if value is None or value == "":
        return "-"
    
    value_str = str(value)
    # 移除换行符和制表符
    value_str = value_str.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # 移除多余的空格
    value_str = " ".join(value_str.split())
    # 转义 Markdown 表格分隔符 '|'，防止单元格内含 '|' 导致表格列错位
    if '|' in value_str:
        value_str = value_str.replace('|', '\\|')
    # 截断过长的内容
    if len(value_str) > 50:
        value_str = value_str[:47] + "..."
    return value_str


def generate_check_reports(records):
    """生成检查报告内容（直接用表格展示，表头从HEADERS_CONFIG读取）"""
    if not records:
        return "### 四、检查报告\n\n> 无数据\n"
    
    # 从 headers.json 中的"检查报告"字段列表读取
    check_report_fields = HEADERS_CONFIG.get("检查报告", [])
    if not check_report_fields:
        # 备选方案
        check_report_fields = ["检查日期", "检查项目名称", "检查描述", "检查结果"]
    
    lines = []
    lines.append(f"### 四、检查报告（共 {len(records)} 条）\n")
    
    # 按时间排序
    sorted_records = sorted(records, key=extract_datetime)
    
    # 生成表格头
    table_headers = ["#"] + check_report_fields
    lines.append("| " + " | ".join(table_headers) + " |")
    lines.append("|" + "|".join(["---"] * len(table_headers)) + "|")
    
    # 生成表格行
    for idx, record in enumerate(sorted_records, 1):
        row = [str(idx)]
        for field in check_report_fields:
            value = record.get(field, "-")
            # 清理表格值
            clean_value = clean_table_value(value)
            row.append(clean_value)
        lines.append("| " + " | ".join(row) + " |")
    
    return "\n".join(lines)


def generate_orders(records):
    """生成医嘱明细内容（直接用表格展示，表头从HEADERS_CONFIG读取）"""
    if not records:
        return "### 五、医嘱明细\n\n> 无数据\n"
    
    # 从 headers.json 中的"医嘱明细"字段列表读取
    order_fields = HEADERS_CONFIG.get("医嘱明细", [])
    if not order_fields:
        # 备选方案
        order_fields = ["医嘱开始日期", "医嘱开始时间", "医嘱类型", "医嘱编码", "医嘱名称", "医嘱子类", "开单科室", "开单医师", "医嘱停止日期", "医嘱停止时间"]
    
    lines = []
    lines.append(f"### 五、医嘱明细（共 {len(records)} 条）\n")
    
    # 按时间排序
    sorted_records = sorted(records, key=extract_datetime)
    
    # 生成表格头
    table_headers = ["#"] + order_fields
    lines.append("| " + " | ".join(table_headers) + " |")
    lines.append("|" + "|".join(["---"] * len(table_headers)) + "|")
    
    # 生成表格行
    for idx, record in enumerate(sorted_records, 1):
        row = [str(idx)]
        for field in order_fields:
            value = record.get(field, "-")
            # 清理表格值
            clean_value = clean_table_value(value)
            row.append(clean_value)
        lines.append("| " + " | ".join(row) + " |")
    
    return "\n".join(lines)


def json_to_markdown(json_data, case_id):
    """将 JSON 数据转换为 Markdown 格式（方案一：时间线+分类展示）"""
    lines = []
    lines.append(f"## 病案号：{case_id}\n")
    lines.append("---\n")
    
    # 1. 病案首页
    if SINGLE_ROW_TYPE in json_data and json_data[SINGLE_ROW_TYPE]:
        lines.append(generate_case_header(json_data[SINGLE_ROW_TYPE]))
        lines.append("\n---\n")
    
    # 2. 入院记录
    if "入院记录" in json_data:
        lines.append(generate_admission_record(json_data["入院记录"]))
        lines.append("---\n")
    
    # 3. 检验报告（按时间排序）
    if "检验报告" in json_data:
        lines.append(generate_test_reports(json_data["检验报告"]))
        lines.append("---\n")
    
    # 4. 检查报告（按时间排序）
    if "检查报告" in json_data:
        lines.append(generate_check_reports(json_data["检查报告"]))
        lines.append("---\n")
    
    # 5. 医嘱明细（按时间排序）
    if "医嘱明细" in json_data:
        lines.append(generate_orders(json_data["医嘱明细"]))
    
    return "\n".join(lines)


def convert_single_file(json_path, output_path):
    """转换单个 JSON 文件为 Markdown"""
    # 读取 JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 提取病案号
    case_id = os.path.splitext(os.path.basename(json_path))[0]
    
    # 转换为 Markdown
    markdown_content = json_to_markdown(data, case_id)
    
    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    return case_id


# ========== 主程序 ==========
if __name__ == "__main__":
    # 加载表头配置
    load_headers_config()
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 调试模式
    if DEBUG_MODE:
        print(f"🐛 调试模式：只转换病案号 {DEBUG_CASE_ID}")
        json_file = os.path.join(INPUT_DIR, f"{DEBUG_CASE_ID}.json")
        md_file = os.path.join(OUTPUT_DIR, f"{DEBUG_CASE_ID}.md")
        
        if os.path.exists(json_file):
            case_id = convert_single_file(json_file, md_file)
            print(f"✅ 已生成：{md_file}")
            print(f"\n提示：请打开 {md_file} 查看效果")
        else:
            print(f"❌ 文件不存在：{json_file}")
    else:
        # 批量转换
        json_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]
        print(f"开始转换 {len(json_files)} 个 JSON 文件为 Markdown...\n")
        
        for idx, filename in enumerate(sorted(json_files), 1):
            json_path = os.path.join(INPUT_DIR, filename)
            md_filename = filename.replace(".json", ".md")
            md_path = os.path.join(OUTPUT_DIR, md_filename)
            
            try:
                case_id = convert_single_file(json_path, md_path)
                if idx % 50 == 0:
                    print(f"✅ 已转换 {idx}/{len(json_files)} 个文件")
            except Exception as e:
                print(f"❌ 转换失败：{filename} - {e}")
        
        print(f"\n🎉 完成！所有文件已转换到：{os.path.abspath(OUTPUT_DIR)}")
