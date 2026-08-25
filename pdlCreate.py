from pathlib import Path
import json
import pymupdf

PDF_DIR = Path(r"C:\Q1_2026_RESULTS")
JSON_DIR = Path(r"C:\Users\kaustubh.keny\Downloads\OFFICE_FILES\v2_json")
OUTPUT_DIR = Path(r"C:\Q1_2026_CLEAN")
SCALE = 2
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KEEP_LABELS = {"table", "table_caption", "doc_title"}


def parse_box(box_string):
    label, coords, _ = box_string.split("--")
    x1, y1, x2, y2 = map(float, coords.split("|"))
    return label.lower(), x1, y1, x2, y2


def get_table_rects(layout_boxes):

    table_rects = []

    for box in layout_boxes:

        label, x1, y1, x2, y2 = parse_box(box)

        if label != "table":
            continue

        rect = pymupdf.Rect(
            x1 / SCALE,
            y1 / SCALE,
            x2 / SCALE,
            y2 / SCALE,
        )

        table_rects.append(rect)

    return table_rects


def should_merge(rect1, rect2, gap=30):

    expanded = pymupdf.Rect(
        rect1.x0 - gap,
        rect1.y0 - gap,
        rect1.x1 + gap,
        rect1.y1 + gap,
    )

    return expanded.intersects(rect2)


def merge_table_rects(rects, gap=30):

    if not rects:
        return []

    rects = list(rects)

    changed = True

    while changed:

        changed = False
        merged = []

        while rects:

            current = rects.pop(0)

            i = 0

            while i < len(rects):

                if should_merge(
                    current,
                    rects[i],
                    gap,
                ):

                    current = current | rects.pop(i)
                    changed = True

                else:
                    i += 1

            merged.append(current)

        rects = merged

    return rects


def add_padding(rect, page_rect, pad_ratio=0.05):

    pad_x = rect.width * pad_ratio
    pad_y = rect.height * pad_ratio

    return pymupdf.Rect(
        max(
            page_rect.x0,
            rect.x0 - pad_x,
        ),
        max(
            page_rect.y0,
            rect.y0 - pad_y,
        ),
        min(
            page_rect.x1,
            rect.x1 + pad_x,
        ),
        min(
            page_rect.y1,
            rect.y1 + pad_y,
        ),
    )


def get_candidates(table_pages):
    return {
        int(page_number)
        for page_number, tables in table_pages.items()
        if any(table.get("numeric_count", 0) > 2 for table in tables)
    }


def add_metadata(page, pdf_name, page_number, total_pages):
    page.insert_text(
        (10, 25),
        f"{pdf_name} | {page_number} | {total_pages}",
        fontsize=20,
        color=(0, 0, 0),
        overlay=True,
    )


clean_batch = pymupdf.open()
original_batch = pymupdf.open()

batch_number = 1
batch_count = 0
batch_log = []
all_batches_log = []


def save_batch():
    global clean_batch, original_batch
    global batch_number, batch_count, batch_log

    if not batch_count:
        return

    clean_name = f"batch_pdl_{batch_number}.pdf"
    original_name = f"batch_ori_{batch_number}.pdf"

    clean_batch.save(
        OUTPUT_DIR / clean_name,
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
    )

    original_batch.save(
        OUTPUT_DIR / original_name,
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
    )

    clean_batch.close()
    original_batch.close()

    all_batches_log.append(
        {
            "batch_name": clean_name,
            "original_batch": original_name,
            "total_pages": batch_count,
            "pages": batch_log,
        }
    )

    print(f"SAVED → {clean_name} | {original_name}")

    batch_number += 1
    batch_count = 0
    batch_log = []

    clean_batch = pymupdf.open()
    original_batch = pymupdf.open()


json_files = sorted(JSON_DIR.glob("*.json"))

print(f"JSON files found: {len(json_files)}")


for json_path in json_files:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        pdf_name = data.get("source_pdf")

        if not pdf_name:
            print(f"Skipping → {json_path.name} | source_pdf missing")
            continue

        pdf_path = PDF_DIR / pdf_name

        if not pdf_path.exists():
            print(f"PDF NOT FOUND → {pdf_name}")
            continue

        candidates = get_candidates(data.get("table_pages", {}))

        if not candidates:
            print(f"NO CANDIDATE PAGES → {pdf_name}")
            continue

        print(f"\nProcessing → {pdf_name}")
        print(f"Candidate pages → {sorted(candidates)}")

        pages_lookup = {page["page_number"]: page for page in data.get("pages", [])}

        clean_doc = pymupdf.open(pdf_path)
        original_doc = pymupdf.open(pdf_path)

        total_pages = len(clean_doc)

        for page_number in sorted(candidates):
            if not 1 <= page_number <= total_pages:
                continue

            page_data = pages_lookup.get(page_number)

            if not page_data:
                print(f"Page {page_number} → No layout data")
                continue

            layout_boxes = page_data.get("layout_boxes", [])

            clean_page = clean_doc[page_number - 1]
            original_page = original_doc[page_number - 1]

            widget = clean_page.first_widget

            while widget:
                next_widget = widget.next
                clean_page.delete_widget(widget)
                widget = next_widget

            annot = clean_page.first_annot

            while annot:
                next_annot = annot.next
                clean_page.delete_annot(annot)
                annot = next_annot

            if not layout_boxes:
                continue

            for box in layout_boxes:
                label, x1, y1, x2, y2 = parse_box(box)

                if label in KEEP_LABELS:
                    continue

                rect = pymupdf.Rect(
                    x1 / SCALE,
                    y1 / SCALE,
                    x2 / SCALE,
                    y2 / SCALE,
                )

                clean_page.draw_rect(
                    rect,
                    color=(1, 1, 1),
                    fill=(1, 1, 1),
                    width=0,
                    overlay=True,
                )

            add_metadata(clean_page, pdf_name, page_number, total_pages)
            add_metadata(original_page, pdf_name, page_number, total_pages)

            clean_batch.insert_pdf(
                clean_doc,
                from_page=page_number - 1,
                to_page=page_number - 1,
            )

            original_batch.insert_pdf(
                original_doc,
                from_page=page_number - 1,
                to_page=page_number - 1,
            )

            batch_count += 1

            batch_log.append(
                {
                    "batch_page": batch_count,
                    "source_pdf": pdf_name,
                    "original_page": page_number,
                    "source_total_pages": total_pages,
                }
            )

            print(
                f"Added → {pdf_name} | Page {page_number} | "
                f"Batch {batch_number} Page {batch_count}"
            )

            if batch_count == 10:
                save_batch()

        clean_doc.close()
        original_doc.close()

    except Exception as e:
        print(f"FAILED → {json_path.name}")
        print(f"Error → {e}")


save_batch()

with open(OUTPUT_DIR / "paddle_batch_log.json", "w", encoding="utf-8") as f:
    json.dump(all_batches_log, f, indent=4)

print("\nALL DONE")
print(f"Total batches → {len(all_batches_log)}")
