from pathlib import Path
from pprint import pformat

from paddleocr import PaddleOCRVL  # type: ignore

pdf = r"D:\BSE_PDFS\500023_page5.pdf"
out = Path(r"D:\BSE_OUTPUT\debug")
out.mkdir(parents=True, exist_ok=True)

pipeline = PaddleOCRVL()
results = pipeline.predict(pdf)

for i, res in enumerate(results):
    path = out / f"page_{i + 1}_result.txt"

    data = {
        "input_path": res["input_path"],
        "page_index": res["page_index"],
        "page_count": res["page_count"],
        "width": res["width"],
        "height": res["height"],
        "layout_boxes": res["layout_det_res"]["boxes"],
        "table_res_list": res["table_res_list"],
        "parsing_res_list": res["parsing_res_list"],
    }

    path.write_text(pformat(data, width=120), encoding="utf-8")
    print(f"Saved: {path}")
