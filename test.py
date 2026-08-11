def page_content_metadata_v1(page, layout, region=None):

    w = layout["width"]
    h = layout["height"]

    if region is None:
        region = {"x0": 0, "y0": 0, "x1": w, "y1": h}

    margin_x = (region["x1"] - region["x0"]) * 0.05
    margin_y = (region["y1"] - region["y0"]) * 0.15

    left = region["x0"] + margin_x
    right = region["x1"] - margin_x
    top = region["y0"] + margin_y
    bottom = region["y1"] - margin_y

    numeric_lines = []
    segment_lines = []

    dirs = Counter()

    # char_count = 0
    line_count = 0
    block_count = 0

    blocks = page.get_text("dict")["blocks"]

    for block in blocks:

        if block["type"] != 0:
            continue
        
        block_count += 1
        
        for line in block["lines"]:

            x0, y0, x1, y1 = line["bbox"]

            # region restriction
            if x1 < left or x0 > right or y1 < top or y0 > bottom:
                continue
            
            line_count += 1
            spans = line["spans"]
            dirs[tuple(map(round, line["dir"]))] += 1
            text = "".join(span["text"] for span in spans).strip()

            if not text:
                continue


            # char_count += len(text)
            
            if NUM_LINE_RE.match(text):
                numeric_lines.append(
                    {
                        "text": text,
                        "bbox": (x0, y0, x1, y1),
                        # IMPORTANT
                        "cx": (x0 + x1) / 2,
                    }
                )

            matches = SECTION_RE.findall(text)

            if matches:
                segment_lines.extend(matches)

    if dirs:

        dominant = dirs.most_common(1)[0][0]

        text_dir = {
            (1, 0): "n",
            (0, -1): "90_cc",
            (0, 1): "90_c",
            (-1, 0): "ud",
        }.get(dominant, "n")

    else:
        text_dir = None

    return {
        **layout,
        # "char_count": char_count,
        "line_count": line_count,
        "block_count": block_count,
        "t_dir": text_dir,
        # "numeric_lines": numeric_lines,
        "numeric_count": len(numeric_lines),
        # "segment_lines": segment_lines,
        "segment_count": len(segment_lines),
    }
