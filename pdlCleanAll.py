from pathlib import Path
import fitz
from paddleocr import LayoutDetection

INPUT_DIR = Path(r"D:\DUMB")
OUTPUT_DIR = Path(r"D:\Q1_CLEAN_PDFS")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCALE = 2

KEEP_LABELS = {
    "table",
    "table_caption",
}

REMOVE_LABELS = {
    "image",
    "figure",
    "seal",
    "text",
    "title",
    "paragraph_title",
    "page_number",
    "abstract",
    "table_of_contents",
    "reference",
    "footnote",
    "header",
    "footer",
    "algorithm",
    "formula",
    "formula_number",
    "figure_caption",
    "figure_title",
    "header_image",
    "footer_image",
    "sidebar_text",
}


def layout_box_to_pdf_rect(box):
    x1, y1, x2, y2 = box["coordinate"]
    return fitz.Rect(x1 / SCALE, y1 / SCALE, x2 / SCALE, y2 / SCALE)


print("Initializing LayoutDetection...")

model = LayoutDetection(model_name="PP-DocLayout_plus-L")

pdf_files = list(INPUT_DIR.glob("*.pdf"))

print(f"PDFs found: {len(pdf_files)}")


for pdf_index, pdf_path in enumerate(pdf_files, start=1):

    print(f"\n{'=' * 70}")
    print(f"[{pdf_index}/{len(pdf_files)}] Processing: {pdf_path.name}")

    output_path = OUTPUT_DIR / pdf_path.name
    temp_dir = OUTPUT_DIR / "_temp"

    temp_dir.mkdir(exist_ok=True)

    try:

        doc = fitz.open(pdf_path)

        for page_index, page in enumerate(doc):

            widget = page.first_widget

            while widget:
                next_widget = widget.next
                page.delete_widget(widget)
                widget = next_widget

            annot = page.first_annot

            while annot:
                next_annot = annot.next
                page.delete_annot(annot)
                annot = next_annot

            print(f"  Page {page_index + 1}/{len(doc)}", end="\r")

            pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))

            img_path = temp_dir / f"{pdf_path.stem}_page_{page_index + 1}.png"

            pix.save(str(img_path))

            results = list(model.predict(str(img_path)))

            img_path.unlink(missing_ok=True)

            if not results:
                print(f"\nWARNING: No layout result on page {page_index + 1}")
                continue

            boxes = results[0].json["res"]["boxes"]

            removed_count = 0

            for box in boxes:

                label = box["label"].lower()

                if label in KEEP_LABELS:
                    continue

                rect = layout_box_to_pdf_rect(box)

                page.draw_rect(
                    rect,
                    color=(1, 1, 1),
                    fill=(1, 1, 1),
                    width=0,
                    overlay=True,
                )

                removed_count += 1

            print(f"\nPage {page_index + 1} | " f"Removed: {removed_count}")

        doc.save(
            output_path,
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
        )

        doc.close()

        print(f"\nDONE → {output_path}")

    except Exception as e:

        print(f"\nFAILED → {pdf_path.name}")
        print(f"Error: {e}")


print("\nALL DONE.")
