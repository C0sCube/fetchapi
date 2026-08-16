import json
import os
import time as ts
from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    AcceleratorOptions,
    AcceleratorDevice,
)
from docling.document_converter import PdfFormatOption

PDF_DIR = Path(r"D:\BSE_PDFS")
EXCEL = Path(r"pages.xlsx")
OUT = Path(r"E:\conda-envs\docling_gpu")
LOG = OUT / "processing_times.txt"

OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(EXCEL)

pages = {}
for _, r in df.iterrows():
    pdf_name = str(r["pdf"]).strip()
    if not pdf_name.lower().endswith(".pdf"):
        pdf_name += ".pdf"

    page_num = int(r["page_n"])
    pages.setdefault(pdf_name, []).append(page_num)


pipeline_options = PdfPipelineOptions()

pipeline_options.do_ocr = False

pipeline_options.accelerator_options = AcceleratorOptions(
    num_threads=4,
    device=AcceleratorDevice.CUDA,
)

pipeline_options.table_structure_options = TableStructureOptions(do_cell_matching=True)

converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)


total_start = ts.perf_counter()

with open(LOG, "w", encoding="utf-8") as log:

    for pdf_name, page_nums in list(pages.items())[:10]:

        pdf_start = ts.perf_counter()
        pdf = PDF_DIR / pdf_name

        print(f"\nPROCESSING: {pdf_name}")
        log.write(f"\n{'=' * 60}\n")
        log.write(f"PDF: {pdf_name}\n")

        for page_num in page_nums:

            page_start = ts.perf_counter()

            print(f"  Page {page_num} ...", flush=True)

            result = converter.convert(
                pdf,
                page_range=(page_num, page_num),
            )

            doc = result.document

            pdf_out = OUT / Path(pdf_name).stem
            pdf_out.mkdir(parents=True, exist_ok=True)

            page_out = pdf_out / f"page_{page_num}"
            page_out.mkdir(parents=True, exist_ok=True)

            with open(
                page_out / "output.md",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(doc.export_to_markdown())

            with open(
                page_out / "output.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    doc.export_to_dict(),
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            page_time = ts.perf_counter() - page_start

            print(
                f"  Page {page_num}: {page_time:.2f} sec",
                flush=True,
            )

            log.write(f"Page {page_num}: {page_time:.2f} sec\n")
            log.flush()

        pdf_time = ts.perf_counter() - pdf_start

        print(
            f"  PDF total: {pdf_time:.2f} sec",
            flush=True,
        )

        log.write(f"PDF total: {pdf_time:.2f} sec\n")
        log.flush()


total_time = ts.perf_counter() - total_start

print(f"\nTOTAL TIME: {total_time:.2f} sec")

with open(LOG, "a", encoding="utf-8") as log:
    log.write(f"\n{'=' * 60}\n")
    log.write(f"TOTAL TIME: {total_time:.2f} sec\n")

print("Done.")
