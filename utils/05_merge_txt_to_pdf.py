from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from PyPDF2 import PdfMerger
import os

def txt_to_pdf(txt_path, pdf_path):
    """将 TXT 文件转换为支持中文和自动换行的 PDF"""
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))  # 注册中文字体
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    margin_x = 50
    margin_y = 50
    line_height = 18
    max_width = width - 2 * margin_x
    y = height - margin_y
    c.setFont('STSong-Light', 12)

    def draw_wrapped_line(text):
        nonlocal y
        char_width = c.stringWidth("测", 'STSong-Light', 12)
        max_chars = int(max_width / char_width)
        lines = []
        while text:
            lines.append(text[:max_chars])
            text = text[max_chars:]
        for ln in lines:
            if y < margin_y:
                c.showPage()
                c.setFont('STSong-Light', 12)
                y = height - margin_y
            c.drawString(margin_x, y, ln)
            y -= line_height

    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            draw_wrapped_line(line.strip())

    c.save()


def merge_pdfs(pdf_list, output_path):
    """合并多个 PDF 文件"""
    merger = PdfMerger()
    for pdf in pdf_list:
        merger.append(pdf)
    merger.write(output_path)
    merger.close()


def main():
    # ======== 配置区域 ========
    pdf_dir = "./data_02_pdf"
    txt_dir = "./data_04_summary_txt"
    output_dir = "./data_05_final_pdf"
    os.makedirs(output_dir, exist_ok=True)
    # ==========================

    pdf_files = {os.path.splitext(f)[0]: os.path.join(pdf_dir, f)
                 for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")}
    txt_files = {os.path.splitext(f)[0]: os.path.join(txt_dir, f)
                 for f in os.listdir(txt_dir) if f.lower().endswith(".txt")}

    common_keys = sorted(set(pdf_files.keys()) & set(txt_files.keys()))

    if not common_keys:
        print("⚠️ 没有找到匹配的 PDF 和 TXT 文件。")
        return

    for key in common_keys:
        original_pdf = pdf_files[key]
        txt_file = txt_files[key]
        temp_pdf = os.path.join(output_dir, f"{key}_temp.pdf")
        output_pdf = os.path.join(output_dir, f"{key}_merge.pdf")

        print(f"📄 [{key}] 正在将 TXT 转换为 PDF...")
        txt_to_pdf(txt_file, temp_pdf)

        print(f"🔗 [{key}] 正在合并 PDF 文件...")
        merge_pdfs([original_pdf, temp_pdf], output_pdf)

        os.remove(temp_pdf)
        print(f"✅ [{key}] 合并完成 -> {output_pdf}")

    print("🎉 所有文件处理完成！")


if __name__ == "__main__":
    main()
