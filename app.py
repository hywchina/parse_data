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
# ✅ 从配置文件读取推荐字段
if os.path.exists(recommended_fields_FILE):
    try:
        with open(recommended_fields_FILE, "r", encoding="utf-8") as f:
            recommended_fields = json.load(f)
    except Exception as e:
        st.warning(f"⚠️ 无法读取推荐字段配置：{e}")
        recommended_fields = {}
else:
    st.info("ℹ️ 未找到 recommended_fields.json，字段推荐功能将跳过。")
    recommended_fields = {}


# ---------------- 工具函数 ----------------
def clean_folders():
    """清空所有过程文件（data_00 ~ data_05），并确保 temp 存在"""
    for key in ["ori", "csv", "pdf", "json", "txt", "final"]:
        path = DATA_DIRS[key]
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)
    os.makedirs(DATA_DIRS["temp"], exist_ok=True)


def save_uploaded_files(uploaded_files):
    """
    在保存上传文件之前先清空所有过程文件（按你的正确要求），
    然后保存文件到 data_00_ori 下。
    """
    # 先清空各个过程目录（保证干净环境）
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


def run_script(script_name, log_area, timeout=None):
    """运行单个 Python 脚本并实时输出日志（阻塞直到脚本结束）"""
    logs = []
    script_path = os.path.join(UTILS_DIR, script_name)

    if not os.path.exists(script_path):
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
        log_html = (
            "<div style='background:#111;color:#0f0;padding:10px;height:360px;overflow-y:auto;"
            "font-family:monospace;font-size:14px;border-radius:6px;'>"
            + "<br>".join(logs[-150:])
            + "</div>"
        )
        log_area.markdown(log_html, unsafe_allow_html=True)
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
    <p style='text-align:center;color:gray;'>上传（先清空旧数据）→ 执行脚本（暂停以编辑字段）→ 下载</p>
    <hr/>
    """,
    unsafe_allow_html=True,
)

# === 上传区 ===
st.subheader("📁 上传原始文件（上传前会清空旧数据）")
uploaded_files = st.file_uploader("选择要上传的文件（支持多文件）", accept_multiple_files=True)

# 初始化 session_state
if "uploaded" not in st.session_state:
    st.session_state["uploaded"] = False
if "running" not in st.session_state:
    st.session_state["running"] = False
if "step" not in st.session_state:
    st.session_state["step"] = 0
if "header_edit_done" not in st.session_state:
    st.session_state["header_edit_done"] = False

# 当用户点击上传并保存时：先清空，再保存文件
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

            # ✅ 保存状态（供 rerun 后显示）
            st.session_state["uploaded"] = True
            st.session_state["uploaded_count"] = len(saved)
            st.session_state["step"] = 0
            st.session_state["header_edit_done"] = False

            # ✅ 先显示成功提示
            st.success(f"✅ 已成功上传并保存 {len(saved)} 个文件，已清空旧数据。")

            # ✅ 暂停片刻，让用户看到反馈后再刷新
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"❌ 上传保存失败：{e}")

else:
    # 如果没有选择任何文件，提醒用户
    st.info("提示：先选择文件再点击“上传并保存文件”。")

# ✅ 如果页面刷新后仍处于“已上传”状态，显示上传成功提示
if st.session_state.get("uploaded"):
    st.success(f"✅ 已成功上传 {st.session_state.get('uploaded_count', 0)} 个文件！")


st.markdown("---")
st.subheader("🧭 执行进度与日志")

# 进度条和日志区
progress_bar = st.progress(0.0)
log_area = st.empty()
log_area.markdown(
    "<div style='background:#111;color:#0f0;padding:10px;height:360px;overflow-y:auto;"
    "font-family:monospace;font-size:14px;border-radius:6px;'>等待执行...</div>",
    unsafe_allow_html=True,
)

# 步骤状态展示（只作可视化）
cols = st.columns(3)
steps_placeholders = []
for i, (_, cname) in enumerate(SCRIPTS):
    with cols[i % 3]:
        ph = st.empty()
        ph.markdown(f"⚪ **{cname}** — 未开始")
        steps_placeholders.append(ph)

st.markdown("---")

# 控制区：只有在上传成功后允许开始执行
col1, col2 = st.columns([1, 1])

with col1:
    start_disabled = not st.session_state["uploaded"] or st.session_state["running"]
    if start_disabled:
        if not st.session_state["uploaded"]:
            st.button("🚀 开始执行全部步骤", disabled=True, use_container_width=True)
            st.warning("⚠️ 请先上传并保存文件，上传操作会先清空旧数据。")
        else:
            st.button("⏳ 执行中...", disabled=True, use_container_width=True)
    else:
        if st.button("🚀 开始执行全部步骤", type="primary", use_container_width=True):
            # 标记开始执行
            st.session_state["running"] = True
            st.session_state["step"] = 0
            st.session_state["header_edit_done"] = False
            st.rerun()

with col2:
    if st.button("🧹 清空过程文件（手动）", use_container_width=True):
        clean_folders()
        st.session_state["uploaded"] = False
        st.session_state["running"] = False
        st.session_state["step"] = 0
        st.session_state["header_edit_done"] = False
        st.success("✅ 已清理 data_00 ~ data_05 目录（手动操作）。")
        st.rerun()

# 如果正在运行，按顺序执行脚本（并在需要处暂停）
if st.session_state["running"]:
    total = len(SCRIPTS)
    # 更新步骤卡片显示（已完成/执行中）
    for idx, (_, cname) in enumerate(SCRIPTS):
        if idx < st.session_state["step"]:
            steps_placeholders[idx].markdown(f"🟢 **{cname}** — 已完成")
        elif idx == st.session_state["step"]:
            steps_placeholders[idx].markdown(f"🟡 **{cname}** — 执行中...")
        else:
            steps_placeholders[idx].markdown(f"⚪ **{cname}** — 未开始")

    # 执行当前步骤
    if st.session_state["step"] < total:
        script_name, cname = SCRIPTS[st.session_state["step"]]
        # 特殊暂停：在执行到读取 CSV 表头脚本后，暂停让用户编辑字段
        if script_name == "00_read_headers.py" and not st.session_state["header_edit_done"]:
            # 先运行脚本去生成 conf/headers.json
            ok = run_script(script_name, log_area)
            progress_bar.progress((st.session_state["step"] + 1) / total)
            if not ok:
                st.error(f"❌ 执行脚本失败：{cname}")
                st.session_state["running"] = False
            else:
                # 如果 headers.json 存在，加载并展示多选界面供用户编辑
                if os.path.exists(HEADERS_FILE):
                    try:
                        with open(HEADERS_FILE, "r", encoding="utf-8") as f:
                            headers_data = json.load(f)
                    except Exception as e:
                        st.error(f"❌ 读取 {HEADERS_FILE} 失败：{e}")
                        st.session_state["running"] = False
                        st.rerun()
                    st.success("✅ 已读取 CSV 表头，请选择需要保留的字段（各表）并确认保存以继续。")
                    st.markdown("### 🧩 字段选择区（多选）")
                    new_headers = {}
                    # ✅ 在文件顶部或靠前定义推荐字段

                    for table_name, fields in headers_data.items():
                        st.markdown(f"**📘 {table_name}**")

                        # ✅ 推荐字段提示
                        recommended = recommended_fields.get(table_name)
                        if recommended:
                            st.markdown(
                                f"<div style='color:#999;font-size:13px;margin-bottom:6px;'>"
                                f"💡 推荐字段：<span style='color:#007bff;'>{'，'.join(recommended)}</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                            # ✅ 过滤出推荐字段中实际存在的部分
                            default = [f for f in recommended if f in fields]
                            if not default:
                                default = fields  # 如果推荐字段一个都不在 header 里，则退回默认全选
                        else:
                            st.markdown(
                                "<div style='color:#999;font-size:13px;margin-bottom:6px;'>💡 暂无推荐字段</div>",
                                unsafe_allow_html=True,
                            )
                            default = fields  # 没推荐字段则默认全选

                        # ✅ 唯一 key 保持不变
                        key = f"sel_{table_name}"

                        # ✅ 字段多选
                        selected = st.multiselect(
                            f"选择要保留的字段（{table_name}）",
                            options=fields,
                            default=default,
                            key=key
                        )

                        new_headers[table_name] = selected


                    if st.button("✅ 确认保存并继续执行"):
                        try:
                            with open(HEADERS_FILE, "w", encoding="utf-8") as f:
                                json.dump(new_headers, f, ensure_ascii=False, indent=2)
                            st.session_state["header_edit_done"] = True
                            st.session_state["step"] += 1  # 跳到下一个脚本
                            st.success("✅ 字段已保存，继续执行后续步骤...")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 保存 headers.json 失败：{e}")
                            st.session_state["running"] = False
                else:
                    st.error("❌ 未生成 headers.json，请检查脚本输出。")
                    st.session_state["running"] = False
        else:
            # 正常执行非暂停脚本
            ok = run_script(script_name, log_area)
            if ok:
                st.session_state["step"] += 1
                progress_bar.progress(st.session_state["step"] / total)
                # 小延迟并重刷页面以更新 UI
                time.sleep(0.3)
                st.rerun()
            else:
                st.error(f"❌ 脚本执行失败：{cname}")
                st.session_state["running"] = False
    else:
        # 所有步骤已完成
        st.session_state["running"] = False
        st.success("🎉 所有步骤已执行完成！")
        progress_bar.progress(1.0)

# 完成后提供下载 ZIP
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
