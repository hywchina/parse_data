import os
import re
from openai import OpenAI

# ========== 用户配置 ==========
INPUT_JSON_DIR = "./data_03_json"
PDF_DIR = "./data_02_pdf"  # 新增 PDF 对应目录
PROMPT_FILE = "./prompt.txt"
OUTPUT_DIR = "./data_04_summary_txt"

os.makedirs(OUTPUT_DIR, exist_ok=True)

API_KEY = "sk-7xet3afg2b7fumjl"
BASE_URL = "https://cloud.infini-ai.com/maas/v1"
MODEL_NAME = "gpt-4o"

CHUNK_SIZE = 100000
CONTEXT_SNIPPET_LEN = 2000
# ==================================


def split_text(text, max_length):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


def remove_repeated_section(prev_text, new_text):
    new_text = new_text.strip()
    prev_end = prev_text[-2000:] if len(prev_text) > 2000 else prev_text

    pattern = r"(病案总结报告|一、基本信息|二、住院经过与主要时间线)"
    if re.search(pattern, new_text):
        first_match = re.search(pattern, new_text)
        if first_match:
            start_idx = first_match.start()
            if prev_end[:100] in new_text:
                new_text = new_text.replace(prev_end, "")
            if start_idx < 200:
                new_text = new_text[start_idx:]
    return new_text


def main():
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    for filename in os.listdir(INPUT_JSON_DIR):
        if not filename.endswith(".json"):
            continue

        # ===== 新增逻辑：检查对应 PDF 是否存在 =====
        base_name = os.path.splitext(filename)[0]
        pdf_path = os.path.join(PDF_DIR, base_name + ".pdf")
        if not os.path.exists(pdf_path):
            print(f"⚠️ 跳过：{filename} —— 未找到对应 PDF：{base_name}.pdf")
            continue
        # ========================================

        json_path = os.path.join(INPUT_JSON_DIR, filename)
        with open(json_path, "r", encoding="utf-8") as f:
            data_json = f.read()

        print(f"📄 正在处理：{filename}")

        chunks = split_text(data_json, CHUNK_SIZE)
        previous_summary = ""
        full_output = ""

        for idx, chunk in enumerate(chunks, 1):
            print(f"  🔹 分块 {idx}/{len(chunks)} 请求中...")

            user_input = f"""
以下为病案JSON的第 {idx} 段（共 {len(chunks)} 段）。
请【仅续写后续内容】，不要重复前文标题或章节。
不要重新生成“病案总结报告”标题或前面章节。

——前文摘要（供上下文参考）——
{previous_summary if previous_summary else "（首段，无前文）"}

——本段JSON数据——
{chunk}

请在保持医学书面语风格的前提下续写报告，注意：
1. 不重复已出现的章节或文字。
2. 不重写标题。
3. 保持逻辑衔接、时间顺序。
{prompt_template}
"""

            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一名具有30年以上临床经验的主任医师。请基于上下文续写病案总结报告，禁止重复前文内容。"
                        },
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.2,
                )

                output = response.choices[0].message.content.strip()
                cleaned = remove_repeated_section(full_output, output)

                full_output += "\n\n" + cleaned
                previous_summary = full_output[-CONTEXT_SNIPPET_LEN:]

            except Exception as e:
                print(f"❌ 分块 {idx} 出错：{e}")
                continue

        output_filename = base_name + ".txt"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(output_path, "w", encoding="utf-8") as out_f:
            out_f.write(full_output.strip())

        print(f"✅ 报告生成完成：{output_filename}")

    print("\n🎯 所有文件处理完成。")

if __name__ == "__main__":
    main()
