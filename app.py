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
PROMPT_FILE = os.path.join(CONF_DIR, "prompt.txt")
PROMPT_DEFAULT_FILE = os.path.join(CONF_DIR, "prompt_default.txt")

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

recommended_fields_FILE = os.path.join(CONF_DIR, "recommended_fields.json")
if os.path.exists(recommended_fields_FILE):
    try:
        with open(recommended_fields_FILE, "r", encoding="utf-8") as f:
            recommended_fields = json.load(f)
    except Exception as e:
        st.warning(f"⚠️ 无法读取推荐字段配置：{e}")
        recommended_fields = {}
else:
    recommended_fields = {}

# ---------------- 工具函数 ----------------
def clean_folders():
    for key in ["ori", "csv", "pdf", "json", "txt", "final"]:
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
    "prompt_edit_done": False,
    "prompt_running": False,   # 点击确认后变 True，表示正在处理 Prompt 步骤
    "show_logs": True,
    "prompt_input": None,      # 存放 text_area 的内容
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
                "prompt_edit_done": False,
                "prompt_running": False,
                "prompt_input": None,
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
cols = st.columns(3)
steps_placeholders = []
for i, (_, cname) in enumerate(SCRIPTS):
    with cols[i % 3]:
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
                "prompt_edit_done": False,
                "prompt_running": False,
            })
            st.rerun()

with col2:
    if st.button("🧹 清空过程文件（手动）", use_container_width=True):
        clean_folders()
        for key in ["uploaded", "running", "header_edit_done", "prompt_edit_done", "prompt_running"]:
            st.session_state[key] = False
        st.session_state["step"] = 0
        st.session_state["prompt_input"] = None
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

        # 暂停点：字段选择（与之前相同）
        if script_name == "00_read_headers.py" and not st.session_state["header_edit_done"]:
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
                        rec = recommended_fields.get(table_name)
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

        # 暂停点：Prompt 编辑（关键修复点）
        elif script_name == "04_generate_reports_infini.py" and not st.session_state["prompt_edit_done"]:
            st.markdown("### 💬 报告生成 Prompt 设置")
            st.info("请在下方输入或修改 prompt 内容")

            # --- 1) 读取默认 prompt 文件内容（仅用于首次初始化） ---
            default_prompt = ""
            if os.path.exists(PROMPT_DEFAULT_FILE):
                try:
                    with open(PROMPT_DEFAULT_FILE, "r", encoding="utf-8") as f:
                        default_prompt = f.read()
                except Exception:
                    default_prompt = ""

            # --- 2) 确保 session_state['prompt_input'] 在 text_area 创建前已初始化（避免空白或双写警告） ---
            # 仅在第一次进入或值为 None 时初始化为 default_prompt（不会覆盖用户已输入的值）
            if st.session_state.get("prompt_input") is None:
                st.session_state["prompt_input"] = default_prompt

            # --- 3) 渲染 text_area（只指定 key，不传 value，避免双重赋值警告） ---
            prompt_text = st.text_area("Prompt 内容：", height=240, key="prompt_input")

            # --- 4) 按钮显示与禁用逻辑 ---
            # 按钮 label 动态：若正在处理则显示“⏳ 执行中...”
            if st.session_state.get("prompt_running", False):
                btn_label = "⏳ 执行中..."
                btn_disabled = True
            else:
                btn_label = "✅ 确认使用该 Prompt 并继续执行"
                btn_disabled = False

            clicked = st.button(btn_label, disabled=btn_disabled, key="confirm_prompt")

            # 点击后：**立即保存 prompt 到文件，设置 prompt_running=True，然后 rerun**
            if clicked:
                try:
                    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
                        f.write(st.session_state.get("prompt_input", "") or "")
                except Exception as e:
                    st.error(f"❌ 无法写入 {PROMPT_FILE}：{e}")
                    st.session_state["running"] = False
                else:
                    # 第一步：标记正在处理并重新渲染，保证用户看到按钮变灰
                    st.session_state["prompt_running"] = True
                    # 立刻 rerun 以便 UI 更新（按钮变灰）
                    st.rerun()

            # 当页面是 rerun 后，如果 prompt_running==True 且 prompt_edit_done==False，则**在这一运行里真正执行脚本**
            if st.session_state.get("prompt_running", False) and not st.session_state.get("prompt_edit_done", False):
                # 确保 prompt.txt 存在（一般在点击时已写入）
                if not os.path.exists(PROMPT_FILE):
                    try:
                        with open(PROMPT_FILE, "w", encoding="utf-8") as f:
                            f.write(st.session_state.get("prompt_input", "") or "")
                    except Exception as e:
                        st.error(f"❌ 无法写入 {PROMPT_FILE}：{e}")
                        st.session_state["prompt_running"] = False
                        st.session_state["running"] = False
                        st.rerun()

                st.success("✅ 已保存 Prompt，开始执行报告生成脚本，请稍候...")
                ok = run_script(script_name, log_area)
                if ok:
                    st.session_state["prompt_edit_done"] = True
                    st.session_state["prompt_running"] = False
                    st.session_state["step"] += 1
                    progress_bar.progress(st.session_state["step"] / total)
                    # 脚本执行完成后刷新进入下一步
                    time.sleep(0.2)
                    st.rerun()
                else:
                    st.error("❌ 报告生成脚本执行失败，请检查日志或脚本。")
                    st.session_state["prompt_running"] = False
                    st.session_state["running"] = False
                    # 不自动 rerun，让用户看到错误并决定下一步

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
