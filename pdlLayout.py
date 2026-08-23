from pathlib import Path
import json
import pymupdf

PDF_DIR = Path(r"D:\Q1_2026_PDFS")
JSON_DIR = Path(r"E:\conda-envs\layout_json")
OUTPUT_DIR = Path(r"D:\Q1_PDF_LABELS")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


SCALE = 2
COLOR = (0, 0, 1)


for json_path in JSON_DIR.glob("*.json"):

    pdf_path = PDF_DIR / f"{json_path.stem}.pdf"

    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path.name}")
        continue

    print(f"Processing: {pdf_path.name}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc = pymupdf.open(pdf_path)

    for page_data in data.get("pages", []):

        page_index = page_data["page_number"] - 1

        if page_index >= len(doc):
            continue

        page = doc[page_index]

        for box_string in page_data.get("layout_boxes", []):

            label, coords, score = box_string.split("--")

            x1, y1, x2, y2 = map(
                float,
                coords.split("|"),
            )

            rect = pymupdf.Rect(
                x1 / SCALE,
                y1 / SCALE,
                x2 / SCALE,
                y2 / SCALE,
            )

            page.draw_rect(
                rect,
                color=COLOR,
                width=0.5,
                overlay=True,
            )

            page.insert_text(
                (
                    rect.x0,
                    max(5, rect.y0 - 2),
                ),
                label,
                fontsize=4,
                color=COLOR,
                overlay=True,
            )

    output_path = OUTPUT_DIR / pdf_path.name

    doc.save(
        output_path,
        garbage=4,
        deflate=True,
    )

    doc.close()

    print(f"Saved: {output_path.name}")


print("ALL DONE")
