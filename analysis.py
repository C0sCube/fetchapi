#new pdf
import pandas as pd
import numpy as np
import os, json
import fitz
from pathlib import Path
import time

folder_pdf = r"C:\Users\kaustubh.keny\Documents\Quarterly Results 2026 Q1"
def page_text_or_scanned(page):

    text = page.get_text("text").strip()
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height

    if page_area <= 0:
        return "scanned"

    image_area = 0
    for img in page.get_images(full=True):
        try:
            xref = img[0]
            for rect in page.get_image_rects(xref):
                clipped = rect & page_rect
                if clipped.is_empty:
                    continue

                rect_area = clipped.width * clipped.height
                # Ignore small logos
                if rect_area > page_area * 0.05:
                    image_area += rect_area

        except Exception:
            continue

    image_coverage = min(image_area / page_area, 1.0)
    blocks = page.get_text("blocks")
    text_blocks = [
        block for block in blocks if len(block) >= 5 and str(block[4]).strip()
    ]

    num_text_blocks = len(text_blocks)

    # Strong text page
    if len(text) > 100 and num_text_blocks >= 3 and image_coverage < 0.8:
        return "text"
    # Strong scanned page
    if image_coverage > 0.8 and len(text) < 100:
        return "scanned"
    # OCR scanned page
    if image_coverage > 0.9 and num_text_blocks <= 2:
        return "scanned"
    return "text" if len(text) > 100 else "scanned"


all_data = []

for file in os.listdir(folder_pdf):

    file_path = os.path.join(folder_pdf, file)

    stem = Path(file_path).name
    print(f"\nProcessing: {stem}")

    doc = fitz.open(file_path)

    for idx, page in enumerate(doc):
        
        res = page_text_or_scanned(page)

        # print("Result:", res)

        all_data.append({
            "pdf_name":stem,
            "page_n":idx +1,
            "type":res
        })
        
    doc.close()


fpath = Path(folder_pdf)

# Overwrite original file
df = pd.DataFrame(all_data)
df.to_excel(f"{fpath.stem}_TYPE.xlsx" ,index=False)
