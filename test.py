import re
import fitz

NUM_RE = re.compile(r"\(?\d[\d,]*\.?\d*%?\)?")  # 1.23, 1,234.45, (123) etc etc
ALPHA_RE = re.compile(r"[A-Za-z]+")  # pure words

# def detect_spread(page, threshold=1.8):
#     rect = page.rect
#     aspect_ratio = rect.width / rect.height

#     return {
#         "aspect_ratio": round(aspect_ratio, 3),
#         "is_spread": aspect_ratio > threshold,
#         "page_width":rect.width,
#         "page_height":rect.height
#     }


def detect_spread(page, ref_width, ref_height):

    width = page.rect.width
    height = page.rect.height
    w_ratio = width / ref_width
    h_ratio = height / ref_height

    is_spread = w_ratio > 1.6 and h_ratio > 0.7

    return {
        "width": width,
        "height": height,
        "width_ratio": w_ratio,
        "height_ratio": h_ratio,
        "area_ratio": (width * height) / (ref_width * ref_height),
        "spread": is_spread,
    }


def tabular_distribution(page, rect):

    y0 = rect.y0 + rect.height * 0.20
    y1 = rect.y1 - rect.height * 0.20

    split_x = rect.x0 + rect.width * 0.60

    left_rect = fitz.Rect(rect.x0, y0, split_x, y1)
    right_rect = fitz.Rect(split_x, y0, rect.x1, y1)

    left_text = page.get_text("text", clip=left_rect)
    right_text = page.get_text("text", clip=right_rect)

    return {
        "alpha_left": len(ALPHA_RE.findall(left_text)),
        "alpha_right": len(ALPHA_RE.findall(right_text)),
        "num_left": len(NUM_RE.findall(left_text)),
        "num_right": len(NUM_RE.findall(right_text)),
    }


input_folder = r"C:\Users\kaustubh.keny\Downloads\FINANCE\FULL"
all_content = []
for pdf_file in sorted(Path(input_folder).glob("*.pdf")):

    try:
        doc = fitz.open(pdf_file)
        total_pages = doc.page_count

        page_0 = doc[0]
        ref_height = page_0.rect.height
        ref_width = page_0.rect.width
        for i in range(0, total_pages):
            page = doc[isinstance]
            spread_info = detect_spread(page, ref_width, ref_height)

            if not spread_info["is_spread"]:
                result = {"pdf_name": pdf_file.stem, "page": i + 1, "segment": "FULL"}

                result.update(spread_info)
                result.update(tabular_distribution(page, page.rect))

                all_content.append(result)

            else:

                rect = page.rect
                mid_x = rect.x0 + rect.width / 2

                left_page = fitz.Rect(rect.x0, rect.y0, mid_x, rect.y1)
                right_page = fitz.Rect(mid_x, rect.y0, rect.x1, rect.y1)
                left_result = {
                    "pdf_name": pdf_file.stem,
                    "page": i + 1,
                    "segment": "LEFT_PAGE",
                }

                left_result.update(spread_info)
                left_result.update(tabular_distribution(page, left_page))
                all_content.append(left_result)

                right_result = {
                    "pdf_name": pdf_file.stem,
                    "page": i + 1,
                    "segment": "RIGHT_PAGE",
                }

                right_result.update(spread_info)
                right_result.update(tabular_distribution(page, right_page))
                all_content.append(right_result)

        doc.close()

    except Exception as e:
        print(f"Error: {pdf_file.name} -> {e}")

df = pd.DataFrame(all_content)
df.to_csv("NUMERIC_RATIO.csv")
