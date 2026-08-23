from pathlib import Path
import json
import pymupdf
from paddleocr import LayoutDetection

INPUT_DIR = Path(r"D:\Q1_2026_PDFS")
OUTPUT_DIR = Path(r"E:\conda-envs\layout_json")
TEMP_DIR = Path(r"E:\conda-envs\temp_layout")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

model = LayoutDetection(model_name="PP-DocLayout_plus-L")


def page_text_or_scanned(page):
    text = page.get_text().strip()
    area = page.rect.width * page.rect.height

    if area <= 0:
        return "scanned"

    image_area = 0

    for img in page.get_images(full=True):
        for rect in page.get_image_rects(img[0]):
            rect = rect & page.rect
            if not rect.is_empty and rect.get_area() > area * 0.05:
                image_area += rect.get_area()

    coverage = min(image_area / area, 1.0)

    return "scanned" if coverage > 0.85 else "text"


for pdf_path in INPUT_DIR.glob("*.pdf"):

    doc = pymupdf.open(pdf_path)

    data = {
        "source_pdf": pdf_path.name,
        "total_pages": len(doc),
        "text_pages": [],
        "scanned_pages": [],
        "table_pages": [],
        "pages": [],
    }

    for i, page in enumerate(doc, 1):

        page_type = page_text_or_scanned(page)

        data[f"{page_type}_pages"].append(i)

        img_path = TEMP_DIR / f"{pdf_path.stem}_{i}.png"

        page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(img_path)

        results = list(model.predict(str(img_path)))
        img_path.unlink(missing_ok=True)

        boxes = results[0].json["res"]["boxes"] if results else []

        if any(box["label"] == "table" for box in boxes):
            data["table_pages"].append(i)

        data["pages"].append(
            {
                "page_number": i,
                "page_type": page_type,
                "page_info": {
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "rotation": page.rotation,
                },
                "layout_boxes": [
                    {
                        "label": b["label"],
                        "coordinate": b["coordinate"],
                        "score": b.get("score", 0),
                    }
                    for b in boxes
                ],
            }
        )

    doc.close()

    with open(OUTPUT_DIR / f"{pdf_path.stem}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Done: {pdf_path.name}")
