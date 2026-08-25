import pandas as pd
import pymupdf
from pathlib import Path
from paddleocr import LayoutDetection
import json

PDF_DIR = Path(r"C:\Q1_2026_RESULTS")
OUTPUT_DIR = Path(r"C:\Users\kaustubh.keny\Projects\OFFICE PROJECTS\eda_pdf\v2.json")
TEMP_DIR = Path(r"C:\Q1_2026_RESULTS\temp_layout")


MODEL_PATH = r"C:\Users\kaustubh.keny\paddle_models\PP-DocLayout_plus-L"

SCALE = 2

layout_model = LayoutDetection(model_dir=MODEL_PATH)

df = pd.read_excel("rotated_pages.xlsx")

results_json = {}

for pdf_name, rows in df.groupby("source_pdf"):

    pdf_path = PDF_DIR / pdf_name

    print(f"Processing {pdf_name}")

    doc = pymupdf.open(pdf_path)

    pdf_results = {}

    for page_num in rows["page_number"]:

        page = doc[int(page_num) - 1]

        original_rotation = page.rotation

        if original_rotation:
            page.set_rotation(0)

        img_path = TEMP_DIR / f"{pdf_path.stem}_{page_num}.png"

        page.get_pixmap(
            matrix=pymupdf.Matrix(SCALE, SCALE)
        ).save(img_path)

        results = list(layout_model.predict(str(img_path)))
        img_path.unlink(missing_ok=True)

        boxes = results[0].json["res"]["boxes"] if results else []

        layout_boxes = []

        for b in boxes:

            label = b["label"].lower()
            x1, y1, x2, y2 = b["coordinate"]

            layout_boxes.append(
                f"{label}--{x1}|{y1}|{x2}|{y2}--{b.get('score',0)}"
            )

        pdf_results[str(page_num)] = {
            "rotation": original_rotation,
            "layout_boxes": layout_boxes,
        }

        if original_rotation:
            page.set_rotation(original_rotation)

    doc.close()

    results_json[pdf_name] = pdf_results

with open("v2.json", "w", encoding="utf-8") as f:
    json.dump(
        results_json,
        f,
        indent=2,
        ensure_ascii=False,
    )