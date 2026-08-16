import json
import os
import time as ts
from pathlib import Path

import fitz
import pandas as pd

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
from docling.document_converter import PdfFormatOption

PDF_DIR = Path(r"D:\BSE_PDFS")
EXCEL = Path(r"pages.xlsx")
OUTPUT_DIR = Path(r"E:\conda-envs\docling_output")
LOG_FILE = OUTPUT_DIR / "processing_times.txt"


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


df = pd.read_excel(EXCEL)

pages = {}

for _, row in df.iterrows():
    pdf_name = str(row["pdf"]).strip()

    if not pdf_name.lower().endswith(".pdf"):
        pdf_name += ".pdf"

    page_num = int(row["page_n"])

    pages.setdefault(pdf_name, []).append(page_num)


pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = False
pipeline_options.table_structure_options = TableStructureOptions(do_cell_matching=True)

converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)


total_start = ts.perf_counter()

with open(LOG_FILE, "w", encoding="utf-8") as log:

    for pdf_name, page_nums in list(pages.items())[:10]:

        pdf_start = ts.perf_counter()

        pdf_path = PDF_DIR / pdf_name
        pdf_output = OUTPUT_DIR / Path(pdf_name).stem
        pdf_output.mkdir(parents=True, exist_ok=True)

        print(f"\nPROCESSING PDF: {pdf_name}")

        log.write(f"\n{'=' * 60}\n")
        log.write(f"PDF: {pdf_name}\n")

        doc = fitz.open(pdf_path)

        for page_num in page_nums:

            page_start = ts.perf_counter()

            print(f"  Page {page_num}...", end="", flush=True)

            page_pdf = pdf_output / f"page_{page_num}.pdf"

            one_page = fitz.open()
            one_page.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
            one_page.save(page_pdf)
            one_page.close()

            result = converter.convert(page_pdf)
            document = result.document

            page_output = pdf_output / f"page_{page_num}"
            page_output.mkdir(parents=True, exist_ok=True)

            md_path = page_output / "document.md"
            json_path = page_output / "document.json"

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(document.export_to_markdown())

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(document.export_to_dict(), f, indent=2, ensure_ascii=False)

            page_time = ts.perf_counter() - page_start

            print(f" {page_time:.2f} sec")

            log.write(f"Page {page_num}: {page_time:.2f} sec\n")
            log.flush()

        doc.close()

        pdf_time = ts.perf_counter() - pdf_start

        print(f"  PDF total: {pdf_time:.2f} sec")

        log.write(f"PDF total: {pdf_time:.2f} sec\n")
        log.flush()


total_time = ts.perf_counter() - total_start

print(f"\nTOTAL TIME: {total_time:.2f} sec")

with open(LOG_FILE, "a", encoding="utf-8") as log:
    log.write(f"\n{'=' * 60}\n")
    log.write(f"TOTAL TIME: {total_time:.2f} sec\n")

print(f"Log: {LOG_FILE}")
print("Done.")

# import json
# from pathlib import Path

# from docling.document_converter import DocumentConverter
# from docling.datamodel.base_models import InputFormat
# from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
# from docling.document_converter import PdfFormatOption

# from pathlib import Path
# import os
# import time as ts

# folder_path = r"D:\Developers\Kaustubh\doctest\CFD_10_COMPANIES"
# fol_path = Path(folder_path)
# output_dir = r"cfd_output"

# output_dir = Path(output_dir)
# output_dir.mkdir(parents=True, exist_ok=True)


# def convert_pdf(pdf_path, output_dir, do_ocr=True):

#     pipeline_options = PdfPipelineOptions()
#     pipeline_options.do_ocr = do_ocr
#     pipeline_options.table_structure_options = TableStructureOptions(
#         do_cell_matching=True
#     )

#     # format:opts

#     converter = DocumentConverter(
#         format_options={
#             InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
#         }
#     )

#     name = Path(pdf_path).stem

#     print(f"Converting PDF... Do OCR: {do_ocr}")
#     result = converter.convert(pdf_path)

#     doc = result.document
#     md_path = output_dir / f"document_{name}.md"

#     with open(md_path, "w", encoding="utf-8") as f:
#         f.write(doc.export_to_markdown())

#     json_path = output_dir / f"document_{name}.json"

#     with open(json_path, "w", encoding="utf-8") as f:
#         json.dump(doc.export_to_dict(), f, indent=2, ensure_ascii=False)

#     print(f"Markdown : {md_path}")
#     print(f"JSON      : {json_path}")


# if __name__ == "__main__":

#     for file in os.listdir(folder_path):

#         fpth = os.path.join(folder_path, file)
#         st_dt = ts.perf_counter()
#         convert_pdf(fpth, output_dir, do_ocr=False)
#         en_dt = ts.perf_counter()
#         print(f"{file}: TIME TAKEN: {en_dt - st_dt}")
