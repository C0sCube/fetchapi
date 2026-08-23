from pathlib import Path
import fitz

from paddleocr import LayoutDetection

INPUT_DIR = Path(r"E:\conda-envs\input_text\batch_0")
OUTPUT_DIR = Path(r"E:\conda-envs\cleaned_pdfs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCALE = 2
KEEP_LABELS = {
    "table",
    # "text",
    # "title",
}
REMOVE_LABELS = {"image", "figure", "seal", "text", "title"}
# LAYOUT_LABELS = {
#     "doc_title",
#     "paragraph_title",
#     "text",
#     "page_number",
#     "abstract",
#     "table_of_contents",
#     "reference",
#     "footnote",
#     "header",
#     "footer",
#     "algorithm",
#     "formula",
#     "formula_number",
#     "image",
#     "figure_caption",
#     "table",
#     "table_caption",
#     "seal",
#     "figure_title",
#     "figure",
#     "header_image",
#     "footer_image",
#     "sidebar_text",
# }


def layout_box_to_pdf_rect(box, scale=SCALE):
    x1, y1, x2, y2 = box["coordinate"]
    return fitz.Rect(x1 / scale, y1 / scale, x2 / scale, y2 / scale)


def overlaps(rect1, rect2):
    intersection = rect1 & rect2
    return not intersection.is_empty


# MODEL
print("Initializing LayoutDetection...")
model = LayoutDetection(model_name="PP-DocLayout_plus-L")
pdf_files = list(INPUT_DIR.glob("*.pdf"))
print(f"PDFs found: {len(pdf_files)}")


for pdf_index, pdf_path in enumerate(pdf_files, start=1):
    print("\n" + "=" * 70)
    print(f"[{pdf_index}/{len(pdf_files)}] Processing: {pdf_path.name}")
    output_path = OUTPUT_DIR / pdf_path.name
    temp_dir = OUTPUT_DIR / "_temp"
    temp_dir.mkdir(exist_ok=True)

    try:

        doc = fitz.open(pdf_path)
        for page_index, page in enumerate(doc):
            print(f"  Page {page_index + 1}/{len(doc)}", end="\r")

            pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
            img_path = temp_dir / (f"{pdf_path.stem}_page_{page_index + 1}.png")
            pix.save(str(img_path))

            results = list(model.predict(str(img_path)))
            # Delete temp image immediately
            img_path.unlink(missing_ok=True)

            if not results:
                print(f"\n  WARNING: No layout result " f"on page {page_index + 1}")
                continue

            result = results[0]
            boxes = result.json["res"]["boxes"]

            protected_rects = []
            for box in boxes:
                label = box["label"].lower()
                if label in KEEP_LABELS:
                    rect = layout_box_to_pdf_rect(box)
                    protected_rects.append(rect)

            removed_count = 0
            skipped_overlap_count = 0

            for box in boxes:

                label = box["label"].lower()

                if label not in REMOVE_LABELS:
                    continue

                unwanted_rect = layout_box_to_pdf_rect(box)

                # --------------------------------------------
                # CHECK OVERLAP WITH IMPORTANT CONTENT
                # --------------------------------------------

                overlaps_important = False

                for protected_rect in protected_rects:

                    if overlaps(unwanted_rect, protected_rect):

                        overlaps_important = True
                        break

                # --------------------------------------------
                # IF OVERLAPS → KEEP IT
                # --------------------------------------------

                if overlaps_important:

                    skipped_overlap_count += 1
                    continue

                # --------------------------------------------
                # SAFE TO REMOVE
                # --------------------------------------------

                page.draw_rect(
                    unwanted_rect,
                    color=(1, 1, 1),
                    fill=(1, 1, 1),
                    width=0,
                    overlay=True,
                )

                removed_count += 1

            print(
                f"\n    Removed: {removed_count} | "
                f"Preserved due to overlap: "
                f"{skipped_overlap_count}"
            )

        # ====================================================
        # SAVE CLEANED PDF
        # ====================================================

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
