from pathlib import Path
import json
import pymupdf


PDF_DIR = Path(r"C:\Q1_2026_RESULTS")
JSON_DIR = Path(r"C:\Q1_2026_RESULTS\v1_json_working")
OUTPUT_DIR = Path(r"C:\Q1_2026_CLEAN")

SCALE = 2

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def parse_box(box_string):
    """
    Example:
    text--138.88|500.40|1034.90|597.62--0.98
    """

    try:
        label, coords, score = box_string.split("--")
        x1, y1, x2, y2 = map(float, coords.split("|"))

        return (
            label.lower(),
            x1,
            y1,
            x2,
            y2,
        )

    except Exception:
        return None

def draw_boxes(page, layout_boxes):
    """
    Draw all boxes in a single color.
    """

    for box in layout_boxes:

        parsed = parse_box(box)

        if not parsed:
            continue

        label, x1, y1, x2, y2 = parsed

        rect = pymupdf.Rect(
            x1 / SCALE,
            y1 / SCALE,
            x2 / SCALE,
            y2 / SCALE,
        )

        # Red rectangle
        page.draw_rect(
            rect,
            color=(1, 0, 0),
            width=1.2,
            overlay=True,
        )

        # Optional label
        page.insert_text(
            (
                rect.x0,
                max(10, rect.y0 - 2),
            ),
            label,
            fontsize=5,
            color=(1, 0, 0),
            overlay=True,
        )

json_files = sorted(JSON_DIR.glob("*.json"))

print(f"Found {len(json_files)} json files")

for json_file in json_files:

    try:

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        pdf_name = data["source_pdf"]

        pdf_path = PDF_DIR / pdf_name

        if not pdf_path.exists():
            print(f"PDF not found: {pdf_name}")
            continue

        print(f"Processing: {pdf_name}")

        pdf = pymupdf.open(pdf_path)

        for page_info in data.get("pages", []):

            page_number = page_info.get("page_number")

            if page_number is None:
                continue

            if page_number < 1 or page_number > len(pdf):
                continue

            page = pdf[page_number - 1]

            # print(page_number, page.rotation)

            # if page.rotation == 270:
            #     page.set_rotation(0)

            # draw_boxes(page, layout_boxes)
            
            # pix = page.get_pixmap(
            # matrix=pymupdf.Matrix(2,2)
        
            # )
            # pix.save(f"debug_{page_number}.png")


            layout_boxes = page_info.get(
                "layout_boxes",
                [],
            )

            draw_boxes(
                page,
                layout_boxes,
            )

        output_pdf = OUTPUT_DIR / pdf_name

        pdf.save(
            output_pdf,
            garbage=4,
            deflate=True,
        )

        pdf.close()

        print(f"Saved: {output_pdf}")

    except Exception as e:
        print(
            f"Failed: {json_file.name} -> {e}"
        )

print("Done")