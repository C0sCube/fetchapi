from pathlib import Path
import json, fitz, tempfile, time
import pandas as pd
from paddleocr import PaddleOCRVL  # type: ignore

PDF_DIR = Path(r"D:\NSE_COMPANIES")
EXCEL = r"pages.xlsx"
OUT = Path(r"E:\conda-envs\output")
LOG = OUT / "processing_times.txt"

OUT.mkdir(parents=True, exist_ok=True)

pages = {}
df = pd.read_excel(EXCEL)
for _, r in df.iterrows():
    pdf_name = str(r["pdf"]).strip()
    if not pdf_name.lower().endswith(".pdf"):
        pdf_name += ".pdf"

    page_num = int(r["page_n"])
    pages.setdefault(pdf_name, []).append(page_num)

pipeline = PaddleOCRVL()

total_start = time.perf_counter()

with open(LOG, "w", encoding="utf-8") as log:

    for pdf_name, page_nums in list(pages.items())[:10]:
        pdf_start = time.perf_counter()

        pdf = PDF_DIR / pdf_name
        pdf_out = OUT / pdf.stem
        pdf_out.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(pdf)

        print(f"\nPROCESSING PDF: {pdf_name}")
        log.write(f"\n{'=' * 60}\n")
        log.write(f"PDF: {pdf_name}\n")

        for page_num in page_nums:
            page_start = time.perf_counter()

            print(f"\tPage: {page_num}")

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_pdf = tmp.name

            one_page = fitz.open()
            one_page.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
            one_page.save(tmp_pdf)
            one_page.close()

            result = next(iter(pipeline.predict(tmp_pdf)))

            page_out = pdf_out / f"page_{page_num}"
            page_out.mkdir(exist_ok=True)

            result.save_to_markdown(str(page_out))

            blocks = []
            for item in result["parsing_res_list"]:
                blocks.append(
                    {
                        "label": item.label,
                        "bbox": list(item.bbox),
                        "content": item.content,
                    }
                )

            with open(page_out / "blocks.json", "w", encoding="utf-8") as f:
                json.dump(
                    {"pdf": pdf_name, "page": page_num, "blocks": blocks},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            Path(tmp_pdf).unlink()

            page_time = time.perf_counter() - page_start

            print(f"\t\tTime: {page_time:.2f} sec")

            log.write(f"Page {page_num}: {page_time:.2f} sec\n")
            log.flush()

        doc.close()

        pdf_time = time.perf_counter() - pdf_start

        print(f"\tPDF total: {pdf_time:.2f} sec")

        log.write(f"PDF total: {pdf_time:.2f} sec\n")
        log.flush()

    total_time = time.perf_counter() - total_start

    print(f"\nTOTAL TIME: {total_time:.2f} sec")
    log.write(f"\n{'=' * 60}\n")
    log.write(f"TOTAL TIME: {total_time:.2f} sec\n")

print("Done.")
