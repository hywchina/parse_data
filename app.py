import streamlit as st
import os
import shutil
import subprocess
import zipfile
from datetime import datetime
import time
import json

# ---------------- 路径配置 ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.join(BASE_DIR, "utils")
CONF_DIR = os.path.join(BASE_DIR, "conf")
os.makedirs(CONF_DIR, exist_ok=True)

HEADERS_FILE = os.path.join(CONF_DIR, "headers.json")

DATA_DIRS = {
    "ori": os.path.join(BASE_DIR, "data_00_ori"),
    "csv": os.path.join(BASE_DIR, "data_01_csv"),
    "json": os.path.join(BASE_DIR, "data_02_json"),
    "md": os.path.join(BASE_DIR, "data_03_md"),
    "temp": os.path.join(BASE_DIR, "temp"),
}

SCRIPTS = [
    ("00_parse_xls_to_csv.py", "数据格式标准化"),
    ("01_read_headers.py", "字段解析与映射"),
    ("02_merge_csv_to_json.py", "多源数据融合"),
    ("03_trans_json_to_md.py", "成果文档整合"),
]

headers_default_file = os.path.join(CONF_DIR, "headers_default.json")
if os.path.exists(headers_default_file):
    try:
        with open(headers_default_file, "r", encoding="utf-8") as f:
            headers_default = json.load(f)
    except Exception as e:
        st.warning(f"⚠️ 无法读取推荐字段配置：{e}")
        headers_default = {}
else:
    headers_default = {}

# ---------------- 工具函数 ----------------
def clean_folders():
    for key in ["ori", "csv", "json", "md"]:
        path = DATA_DIRS[key]
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)
    os.makedirs(DATA_DIRS["temp"], exist_ok=True)

def save_uploaded_files(uploaded_files):
    clean_folders()
    saved = []
    os.makedirs(DATA_DIRS["ori"], exist_ok=True)
    for file in uploaded_files:
        dest = os.path.join(DATA_DIRS["ori"], file.name)
        with open(dest, "wb") as f:
            f.write(file.getbuffer())
        saved.append(dest)
    return saved

def make_zip():
    os.makedirs(DATA_DIRS["temp"], exist_ok=True)
    folder = DATA_DIRS["md"]
    if not os.path.exists(folder) or not os.listdir(folder):
        st.error("❌ 没有生成 MD 文件，请先执行转换。")
        return None
    zip_path = os.path.join(DATA_DIRS["temp"], f"final_output_{datetime.now():%Y%m%d_%H%M%S}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in os.listdir(folder):
            fpath = os.path.join(folder, f)
            zipf.write(fpath, arcname=f)
    return zip_path

def run_script(script_name, log_area, timeout=None):
    logs = []
    script_path = os.path.join(UTILS_DIR, script_name)
    if not os.path.exists(script_path):
        # 若日志可见则写入，否则直接 info
        if st.session_state.get("show_logs", True):
            log_area.info(f"⚠️ 脚本不存在：{script_name}")
        else:
            log_area.info(f"⚠️ 脚本不存在：{script_name}")
        return False

    process = subprocess.Popen(
        ["python3", script_path],
        cwd=BASE_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )

    start_time = time.time()
    for line in process.stdout:
        logs.append(line.rstrip())
        if st.session_state.get("show_logs", True):
            log_html = (
                "<div style='background:#111;color:#0f0;padding:10px;height:360px;overflow-y:auto;"
                "font-family:monospace;font-size:14px;border-radius:6px;'>"
                + "<br>".join(logs[-150:])
                + "</div>"
            )
            log_area.markdown(log_html, unsafe_allow_html=True)
        # tiny sleep to allow front-end update
        time.sleep(0.02)
        if timeout and (time.time() - start_time) > timeout:
            process.kill()
            logs.append("❌ 脚本执行超时并被终止。")
            break

    process.wait()
    success = process.returncode == 0
    return success

# ---------------- Streamlit 页面布局 ----------------
st.set_page_config(page_title="数据处理一键工具", page_icon="📊", layout="centered")
st.markdown(
    """
    <h1 style='text-align:center;'>📊 数据处理一键工具</h1>
    <p style='text-align:center;color:gray;'>上传（清空旧数据）→ 执行脚本（暂停编辑字段 / Prompt）→ 下载</p>
    <hr/>
    """,
    unsafe_allow_html=True,
)

# === 上传区 ===
st.subheader("📁 上传原始文件")
uploaded_files = st.file_uploader("选择要上传的文件（支持多文件）", accept_multiple_files=True)

# 初始化 session_state
_defaults = {
    "uploaded": False,
    "running": False,
    "step": 0,
    "header_edit_done": False,
    "show_logs": True,
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

# 上传逻辑
if uploaded_files:
    file_names = [f.name for f in uploaded_files]
    st.markdown(
        "<div style='max-height:180px;overflow-y:auto;border:1px solid #ddd;padding:8px;border-radius:6px;background:#fafafa;'>"
        + "<br>".join([f"📄 " + name for name in file_names])
        + "</div>",
        unsafe_allow_html=True,
    )
    if st.button("⬆️ 上传并保存文件", type="primary"):
        try:
            saved = save_uploaded_files(uploaded_files)
            st.session_state.update({
                "uploaded": True,
                "uploaded_count": len(saved),
                "step": 0,
                "header_edit_done": False,
            })
            st.success(f"✅ 已上传 {len(saved)} 个文件，旧数据已清空。")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"❌ 上传保存失败：{e}")
else:
    st.info("提示：选择文件后点击“上传并保存文件”开始。")

if st.session_state["uploaded"]:
    st.success(f"✅ 已成功上传 {st.session_state.get('uploaded_count', 0)} 个文件。")

st.markdown("---")
st.subheader("🧭 执行进度与日志")

# 日志显示切换按钮
col_toggle, _ = st.columns([1, 3])
if col_toggle.button("👁️ 显示 / 隐藏日志", use_container_width=True):
    st.session_state["show_logs"] = not st.session_state["show_logs"]
    st.rerun()

# 日志区和进度条
progress_bar = st.progress(0.0)
log_area = st.empty()
if st.session_state["show_logs"]:
    log_area.markdown(
        "<div style='background:#111;color:#0f0;padding:10px;height:360px;overflow-y:auto;"
        "font-family:monospace;font-size:14px;border-radius:6px;'>等待执行...</div>",
        unsafe_allow_html=True,
    )
else:
    log_area.info("日志已隐藏，可点击上方按钮显示。")

# 步骤卡片显示
cols = st.columns(4)
steps_placeholders = []
for i, (_, cname) in enumerate(SCRIPTS):
    with cols[i]:
        ph = st.empty()
        ph.markdown(f"⚪ **{cname}** — 未开始")
        steps_placeholders.append(ph)

st.markdown("---")

# 控制区：开始 / 清空
col1, col2 = st.columns([1, 1])
with col1:
    if not st.session_state["uploaded"]:
        st.button("🚀 开始执行全部步骤", disabled=True, use_container_width=True)
        st.warning("⚠️ 请先上传并保存文件。")
    elif st.session_state["running"]:
        st.button("⏳ 执行中...", disabled=True, use_container_width=True)
    else:
        if st.button("🚀 开始执行全部步骤", type="primary", use_container_width=True):
            st.session_state.update({
                "running": True,
                "step": 0,
                "header_edit_done": False,
            })
            st.rerun()

with col2:
    if st.button("🧹 清空过程文件（手动）", use_container_width=True):
        clean_folders()
        for key in ["uploaded", "running", "header_edit_done"]:
            st.session_state[key] = False
        st.session_state["step"] = 0
        st.success("✅ 已清理所有数据目录。")
        st.rerun()

# ---------------- 执行逻辑 ----------------
if st.session_state["running"]:
    total = len(SCRIPTS)

    # 更新每一步的可视状态
    for idx, (_, cname) in enumerate(SCRIPTS):
        if idx < st.session_state["step"]:
            steps_placeholders[idx].markdown(f"🟢 **{cname}** — 已完成")
        elif idx == st.session_state["step"]:
            steps_placeholders[idx].markdown(f"🟡 **{cname}** — 执行中...")
        else:
            steps_placeholders[idx].markdown(f"⚪ **{cname}** — 未开始")

    if st.session_state["step"] < total:
        script_name, cname = SCRIPTS[st.session_state["step"]]

        # 暂停点：字段选择
        if script_name == "01_read_headers.py" and not st.session_state["header_edit_done"]:
            ok = run_script(script_name, log_area)
            progress_bar.progress((st.session_state["step"] + 1) / total)
            if not ok:
                st.error(f"❌ 执行脚本失败：{cname}")
                st.session_state["running"] = False
            else:
                if os.path.exists(HEADERS_FILE):
                    with open(HEADERS_FILE, "r", encoding="utf-8") as f:
                        headers_data = json.load(f)
                    st.markdown("### 🧩 字段选择")
                    new_headers = {}
                    for table_name, fields in headers_data.items():
                        st.markdown(f"**📘 {table_name}**")
                        rec = headers_default.get(table_name)
                        default = [f for f in (rec or []) if f in fields] or fields
                        selected = st.multiselect(
                            f"选择要保留的字段（{table_name}）",
                            options=fields,
                            default=default,
                            key=f"sel_{table_name}"
                        )
                        new_headers[table_name] = selected

                    if st.button("✅ 确认保存并继续执行"):
                        with open(HEADERS_FILE, "w", encoding="utf-8") as f:
                            json.dump(new_headers, f, ensure_ascii=False, indent=2)
                        st.session_state["header_edit_done"] = True
                        st.session_state["step"] += 1
                        st.success("✅ 字段已保存，继续执行后续步骤...")
                        st.rerun()
                else:
                    st.error("❌ 未找到 headers.json，请检查上一步脚本输出。")
                    st.session_state["running"] = False

        # 其他步骤按序执行
        else:
            ok = run_script(script_name, log_area)
            if ok:
                st.session_state["step"] += 1
                progress_bar.progress(st.session_state["step"] / total)
                time.sleep(0.3)
                st.rerun()
            else:
                st.error(f"❌ 脚本执行失败：{cname}")
                st.session_state["running"] = False

    else:
        # 完成全部步骤
        st.session_state["running"] = False
        st.success("🎉 所有步骤已执行完成！")
        progress_bar.progress(1.0)

# ---------------- 打包下载 ----------------
if not st.session_state["running"] and st.session_state["step"] >= len(SCRIPTS):
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
