import streamlit as st
import os
import shutil
import subprocess
import zipfile
from datetime import datetime
import time

# ---------------- 路径配置 ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.join(BASE_DIR, "utils")

DATA_DIRS = {
    "ori": os.path.join(BASE_DIR, "data_00_ori"),
    "csv": os.path.join(BASE_DIR, "data_01_csv"),
    "pdf": os.path.join(BASE_DIR, "data_02_pdf"),
    "json": os.path.join(BASE_DIR, "data_03_json"),
    "txt": os.path.join(BASE_DIR, "data_04_summary_txt"),
    "final": os.path.join(BASE_DIR, "data_05_final_pdf"),
    "temp": os.path.join(BASE_DIR, "temp"),
}

SCRIPTS = [
    ("01_parse_xls_to_csv.py", "Excel 转 CSV"),
    ("00_read_headers.py", "读取 CSV 标头"),
    ("02_rename_pdf.py", "重命名 PDF"),
    ("03_merge_csv_to_json.py", "合并 JSON 数据"),
    ("04_generate_reports_infini.py", "生成文本报告"),
    ("05_merge_txt_to_pdf.py", "合并报告与 PDF"),
]


# ---------------- 工具函数 ----------------
def clean_folders():
    """清空所有过程文件"""
    for key in ["ori", "csv", "pdf", "json", "txt", "final"]:
        path = DATA_DIRS[key]
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)
    os.makedirs(DATA_DIRS["temp"], exist_ok=True)


def save_uploaded_files(uploaded_files):
    """保存上传文件前先清空"""
    clean_folders()
    saved = []
    for file in uploaded_files:
        dest = os.path.join(DATA_DIRS["ori"], file.name)
        with open(dest, "wb") as f:
            f.write(file.getbuffer())
        saved.append(dest)
    return saved


def make_zip():
    """压缩最终结果"""
    os.makedirs(DATA_DIRS["temp"], exist_ok=True)
    folder = DATA_DIRS["final"]
    if not os.path.exists(folder) or not os.listdir(folder):
        st.error("❌ 没有生成 PDF 文件，请先执行转换。")
        return None

    zip_path = os.path.join(DATA_DIRS["temp"], f"final_output_{datetime.now():%Y%m%d_%H%M%S}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in os.listdir(folder):
            fpath = os.path.join(folder, f)
            zipf.write(fpath, arcname=f)
    return zip_path


def run_pipeline_realtime(log_area, steps_placeholder, progress_bar):
    """实时执行脚本 + 状态中文显示"""
    logs = []
    total = len(SCRIPTS)

    for i, (script, cname) in enumerate(SCRIPTS):
        steps_placeholder[i].markdown(f"🟡 **{cname}** — 执行中...")

        progress_bar.progress(i / total)
        script_path = os.path.join(UTILS_DIR, script)

        process = subprocess.Popen(
            ["python3", script_path],
            cwd=BASE_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )

        for line in process.stdout:
            logs.append(line.rstrip())
            log_html = "<div style='background:#111;color:#0f0;padding:10px;height:360px;overflow-y:auto;font-family:monospace;font-size:14px;border-radius:6px;'>" + \
                       "<br>".join(logs[-150:]) + "</div>"
            log_area.markdown(log_html, unsafe_allow_html=True)
            time.sleep(0.02)

        process.wait()
        if process.returncode == 0:
            steps_placeholder[i].markdown(f"🟢 **{cname}** — 已完成")
        else:
            steps_placeholder[i].markdown(f"🔴 **{cname}** — 失败")
            break

        progress_bar.progress((i + 1) / total)

    progress_bar.progress(1.0)
    log_html = "<div style='background:#111;color:#0f0;padding:10px;height:360px;overflow-y:auto;font-family:monospace;font-size:14px;border-radius:6px;'>" + \
               "<br>".join(logs[-200:]) + "</div>"
    log_area.markdown(log_html, unsafe_allow_html=True)
    return logs


# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="数据处理一键工具", page_icon="📊", layout="centered")

st.markdown(
    """
    <h1 style='text-align:center;'>📊 数据处理一键工具</h1>
    <p style='text-align:center;color:gray;'>上传 → 执行六个步骤 → 一键下载结果</p>
    <hr/>
    """,
    unsafe_allow_html=True,
)

# === 上传区 ===
st.subheader("📁 上传原始文件（上传前会清空旧数据）")
uploaded_files = st.file_uploader("选择要上传的文件", accept_multiple_files=True)

if uploaded_files:
    file_names = [f.name for f in uploaded_files]
    st.markdown(
        "<div style='max-height:180px;overflow-y:auto;border:1px solid #ddd;padding:8px;border-radius:6px;background:#fafafa;'>"
        + "<br>".join([f"📄 " + name for name in file_names])
        + "</div>",
        unsafe_allow_html=True,
    )
    if st.button("⬆️ 上传并保存文件", type="primary"):
        save_uploaded_files(uploaded_files)
        st.success(f"✅ 已成功上传 {len(uploaded_files)} 个文件！")

# === 步骤显示区 ===
st.markdown("---")
st.subheader("🧭 执行进度")

cols = st.columns(3)
steps_placeholder = []
for i, (_, cname) in enumerate(SCRIPTS):
    with cols[i % 3]:
        ph = st.empty()
        ph.markdown(f"⚪ **{cname}** — 未开始")
        steps_placeholder.append(ph)

st.markdown("---")
st.subheader("🖥️ 实时日志")

log_area = st.empty()
log_area.markdown(
    "<div style='background:#111;color:#0f0;padding:10px;height:360px;overflow-y:auto;font-family:monospace;font-size:14px;border-radius:6px;'>等待执行...</div>",
    unsafe_allow_html=True,
)

st.markdown("---")

# === 控制区 ===
col1, col2 = st.columns([1, 1])

if "running" not in st.session_state:
    st.session_state["running"] = False

with col1:
    if not st.session_state["running"]:
        if st.button("🚀 开始执行全部步骤", type="primary", use_container_width=True):
            st.session_state["running"] = True
            progress_bar = st.progress(0.0)
            logs = run_pipeline_realtime(log_area, steps_placeholder, progress_bar)
            st.success("✅ 所有步骤已执行完成！")
            st.session_state["running"] = False
    else:
        st.button("⏳ 正在运行中...", disabled=True, use_container_width=True)

with col2:
    if st.button("🧹 清空过程文件", use_container_width=True):
        clean_folders()
        st.success("✅ 已清理 data_00~05 目录。")

st.markdown("---")
st.subheader("📦 打包并下载结果 ZIP")

if st.button("📁 生成 ZIP 压缩包", type="primary", use_container_width=True):
    zip_path = make_zip()
    if zip_path:
        with open(zip_path, "rb") as f:
            st.download_button(
                "⬇️ 下载结果 ZIP",
                data=f,
                file_name=os.path.basename(zip_path),
                mime="application/zip",
                use_container_width=True,
            )

st.markdown("<hr/><p style='text-align:center;color:gray;'>© 2025 数据自动化工具 | Powered by Streamlit</p>", unsafe_allow_html=True)
