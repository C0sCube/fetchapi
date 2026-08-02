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
                # Ignore small logos/icons
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
