from pathlib import Path
import json, re, pymupdf, time, csv
from collections import Counter
from paddleocr import LayoutDetection
from logger import setup_logger

INPUT_DIR = Path(r"C:\Users\kaustubh.keny\Downloads\Insurance May 2027")
OUTPUT_DIR = Path(r"C:\Users\kaustubh.keny\Downloads\Insurance May 2027\v1_json")
TEMP_DIR = Path(r"C:\Users\kaustubh.keny\Downloads\Insurance May 2027\temp_layout")


MODEL_PATH = r"C:\Users\kaustubh.keny\paddle_models\PP-DocLayout_plus-L"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

FINANCIAL_TERMS = [
    "non current",
    "current assets",
    "decrease in",
    "current liabilities",
    "increase decrease",
    "cash equivalents",
    "cash and",
    "and cash",
    "profit loss",
    "financial assets",
    "cash flow",
    "other current",
    "net cash",
    "flow from",
    "financial liabilities",
    "profit before",
    "the period",
    "comprehensive income",
    "other financial",
    "for the",
    "before tax",
    "equity share",
    "deferred tax",
    "of the",
    "share capital",
    "property plant",
    "operating activities",
    "in trade",
    "from operations",
    "used in",
    "investing activities",
    "financing activities",
    "in other",
    "trade receivables",
    "current tax",
    "trade payables",
    "plant and",
    "intangible assets",
    "and liabilities",
    "and equipment",
    "short term",
    "from operating",
    "income tax",
    "equity and",
    "other comprehensive",
    "proceeds from",
    "other non",
    "increase in",
    "to profit",
    "depreciation and",
    "exceptional items",
    "long term",
    "sale of",
    "working capital",
    "profit or",
    "or loss",
    "be reclassified",
    "that will",
    "loss before",
    "items that",
    "total equity",
    "tax assets",
    "tax expense",
    "generated from",
    "small enterprises",
    "from financing",
    "and small",
    "from investing",
    "at the",
    "reclassified to",
    "other than",
    "equivalents at",
    "other equity",
    "cash generated",
    "purchase of",
    "the year",
    "total current",
    "finance costs",
    "total non",
    "per share",
    "other income",
    "lease liabilities",
    "assets net",
    "total outstanding",
    "outstanding dues",
    "dues of",
    "term borrowings",
    "adjustments for",
    "changes in",
    "cash flows",
    "revenue from",
    "in cash",
    "face value",
    "earnings per",
    "net of",
    "of property",
    "net profit",
    "interest income",
    "other expenses",
    "tax liabilities",
    "enterprises and",
    "total expenses",
    "micro enterprises",
    "loss for",
    "total comprehensive",
    "work in",
    "capital changes",
    "and amortisation",
    "in progress",
    "net increase",
    "total assets",
    "paid up",
    "and tax",
    "liabilities net",
    "not be",
    "will not",
    "value of",
    "before working",
    "total income",
    "decrease increase",
    "cash used",
    "end of",
    "from used",
    "term loans",
    "extraordinary items",
    "income for",
    "up equity",
    "items and",
    "flows from",
    "finance cost",
    "before exceptional",
    "beginning of",
    "operating profit",
    "term provisions",
    "employee benefits",
    "current financial",
    "stock in",
    "loans and",
    "non controlling",
    "attributable to",
    "and advances",
    "relating to",
    "in inventories",
    "and other",
    "per equity",
    "amortisation expense",
    "loss from",
    "than micro",
    "after tax",
    "discontinued operations",
    "on sale",
    "period year",
    "tax expenses",
    "the end",
    "in investing",
    "fixed assets",
    "bank balances",
    "the beginning",
    "loss on",
    "continuing operations",
    "capital face",
    "tax relating",
    "will be",
    "rs each",
    "capital work",
    "current investments",
    "benefits expense",
    "cash cash",
    "creditors other",
    "in short",
    "in financing",
    "interest received",
    "under development",
    "in operating",
    "and amortization",
    "of micro",
    "of rs",
    "of fixed",
    "repayment of",
    "taxes paid",
    "gain on",
    "interest paid",
    "cash from",
    "of tax",
    "from continuing",
    "of creditors",
    "from sale",
    "income from",
    "assets under",
    "investment in",
    "cost of",
    "other intangible",
    "share of",
    "provision for",
    "controlling interest",
    "of stock",
    "of investments",
    "profit for",
    "to items",
    "total tax",
    "issue of",
    "owners of",
    "gain loss",
    "change in",
    "inventories of",
    "in current",
    "the company",
    "right of",
    "of use",
    "amortization expense",
    "not annualised",
    "adjustment for",
    "of equity",
    "with banks",
    "micro and",
    "income loss",
    "employee benefit",
    "of lease",
    "in working",
    "loans advances",
    "other assets",
    "use assets",
    "defined benefit",
    "sub total",
    "paid net",
    "fair value",
    "of cash",
    "total liabilities",
    "finished goods",
]

SCALE = 2

# NUM_LINE_RE = re.compile(
#     r"^\s*[\(\[\{]?\s*[₹$€£]?\s*[-+]?\d[\d,]*(?:\.\d+)?%?\s*[\)\]\}]?\s*$"
# )

NUM_LINE_RE = re.compile(# exclude standalone integers: 1, 2, 3, 1., 2.
    r"""^\s*(?!\d{1,3}\s*$)[\(\[\{]?[₹$€£]?[-+]?\d[\d,]*(?:\.\d+)?%?[\)\]\}]?\s*$""",
    re.VERBOSE,
)

FINANCIAL_RE = re.compile(
    r"\b(?:"
    + "|".join(
        re.escape(term) for term in sorted(FINANCIAL_TERMS, key=len, reverse=True)
    )
    + r")\b",
    re.IGNORECASE,
)

logger = setup_logger(name="layout_log", base_dir=OUTPUT_DIR / "logs")
layout_model = LayoutDetection(model_dir=MODEL_PATH)


def page_text_or_scanned(page):
    text = page.get_text("text").strip()
    page_area = page.rect.width * page.rect.height

    if page_area <= 0:
        return "scanned"

    image_area = 0

    for img in page.get_images(full=True):
        try:
            for rect in page.get_image_rects(img[0]):
                clipped = rect & page.rect
                if not clipped.is_empty and clipped.get_area() > page_area * 0.05:
                    image_area += clipped.get_area()
        except Exception:
            continue

    image_coverage = min(image_area / page_area, 1.0)

    text_blocks = [
        b for b in page.get_text("blocks") if len(b) >= 5 and str(b[4]).strip()
    ]

    if len(text) > 100 and len(text_blocks) >= 3 and image_coverage < 0.8:
        return "text"

    if image_coverage > 0.8 and len(text) < 100:
        return "scanned"

    if image_coverage > 0.9 and len(text_blocks) <= 2:
        return "scanned"

    return "text" if len(text) > 100 else "scanned"

def table_metadata(page, rect):
    text = page.get_text("text", clip=rect)
    lines, numeric_count = [], 0

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if NUM_LINE_RE.match(line):
            numeric_count += 1
        else:
            lines.append(line)

    clean_text = re.sub(r"\s+", " ", " ".join(lines)).strip().lower()
    matches = FINANCIAL_RE.findall(clean_text)

    return {
        "financial_term_count": len(matches),
        "numeric_count": numeric_count,
    }

def get_page_rotation(page):

    dirs = Counter()

    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue

        for line in block.get("lines", []):
            direction = tuple(round(v) for v in line["dir"])
            dirs[direction] += 1

    if not dirs:
        return 0

    dominant = dirs.most_common(1)[0][0]

    rotation_map = {
        (1, 0): 0,
        (0, -1): 90,
        (0, 1): -90,
        (-1, 0): 180,
    }

    return rotation_map.get(dominant, 0)

def fmt_coord(x1, y1, x2, y2):
    return f"{x1}||{y1}||{x2}||{y2}"


execution_summary = []
page_summary = []


pdf_files = list(INPUT_DIR.glob("*.pdf")) #[2000:]
print(f"PDFs found: {len(pdf_files)}")

for pdf_index, pdf_path in enumerate(pdf_files, 1):

    pdf_start = time.perf_counter()
    pdf_size_mb = round(pdf_path.stat().st_size / (1024 * 1024), 2)

    logger.info(f"START | PDF={pdf_path.name} | SIZE_MB={pdf_size_mb}")

    try:

        doc = pymupdf.open(pdf_path)

        data = {
            "source_pdf": pdf_path.name,
            "total_pages": len(doc),
            "pdf_scan_ratio": 0,
            "text_pages": [],
            "text_page_count": 0,
            "scanned_pages": [],
            "scan_page_count": 0,
            "table_page_count": 0,
            "scan_and_table": [],
            "to_parser": [],
            "table_pages": {},
            "pages": [],
        }

        text_pages = []
        scan_pages = []

        for i, page in enumerate(doc, 1):

            print(f"Page {i}/{len(doc)}", end="\r")

            # scan/text and text_dir
            page_type = "text"
            rotation = 0

            page_type = page_text_or_scanned(page)

            if page_type == "text":
                text_pages.append(i)
                rotation = get_page_rotation(page)
            else:
                scan_pages.append(i)
                
            original_rotation = page.rotation
            if original_rotation != 0:
                page.set_rotation(0)
            
            img_path = TEMP_DIR / f"{pdf_path.stem}_{i}.png"
            page.get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE)).save(img_path)

            # layout paddle model
            results = list(layout_model.predict(str(img_path)))

            img_path.unlink(missing_ok=True)
            boxes = results[0].json["res"]["boxes"] if results else []

            layout_boxes = []
            page_tables = []

            # filter the pages with table

            for b in boxes:

                label = b["label"].lower()
                x1, y1, x2, y2 = b["coordinate"]

                layout_boxes.append(
                    f"{label}--{x1}|{y1}|{x2}|{y2}--{b.get('score', 0)}"
                )

                if label != "table":
                    continue

                rect = pymupdf.Rect(x1 / SCALE, y1 / SCALE, x2 / SCALE, y2 / SCALE)

                table_data = {
                    "page_type": page_type,
                    "coordinates": fmt_coord(
                        x1 / SCALE, y1 / SCALE, x2 / SCALE, y2 / SCALE
                    ),
                }

                if page_type == "text":
                    table_data.update(table_metadata(page, rect))

                page_tables.append(table_data)

            if page_tables:

                data["table_pages"][str(i)] = page_tables
                data["to_parser"].append(i)

                if page_type == "scanned":
                    data["scan_and_table"].append(i)

            data["pages"].append(
                {
                    "page_number": i,
                    "page_type": page_type,
                    "layout_boxes": layout_boxes,
                }
            )

            page_metrics = {
                "financial_term_count": 0,
                "numeric_count": 0,
            }

            if page_type == "text" and page_tables:
                page_metrics = {
                    "financial_term_count": sum(
                        t.get("financial_term_count", 0) for t in page_tables
                    ),
                    "numeric_count": sum(
                        t.get("numeric_count", 0) for t in page_tables
                    ),
                }

            page_summary.append(
                {
                    "source_pdf": pdf_path.name,
                    "page_number": i,
                    "page_type": page_type,
                    "text_rotation": rotation,
                    "tabular": bool(page_tables),
                    **page_metrics,
                }
            )

        data["text_pages"] = text_pages
        data["text_page_count"] = len(text_pages)
        data["scanned_pages"] = scan_pages
        data["scan_page_count"] = len(scan_pages)
        data["pdf_scan_ratio"] = round(len(scan_pages) / len(doc), 2) if len(doc) else 0
        data["table_page_count"] = len(data["table_pages"])
        data["to_parser"] = list(dict.fromkeys(data["to_parser"]))

        doc.close()

        output_path = OUTPUT_DIR / f"{pdf_path.stem}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        pdf_time = round(time.perf_counter() - pdf_start, 2)

        logger.info(
            f"END | PDF={pdf_path.name} | "
            f"SIZE_MB={pdf_size_mb} | "
            f"TOTAL_PAGES={data['total_pages']} | "
            f"PDF_SCAN_RATIO={data['pdf_scan_ratio']} | "
            f"TABLE_PAGES={data['table_page_count']} | "
            f"SCAN_AND_TABLE={len(data['scan_and_table'])} | "
            f"TO_PARSER={len(data['to_parser'])} | "
            f"TIME_SEC={pdf_time}"
        )

        execution_summary.append(
            {
                "source_pdf": pdf_path.name,
                "pdf_size_mb": pdf_size_mb,
                "total_pages": data["total_pages"],
                "text_pages": data["text_page_count"],
                "scanned_pages": data["scan_page_count"],
                "pdf_scan_ratio": data["pdf_scan_ratio"],
                "table_pages": data["table_page_count"],
                "scan_and_table": len(data["scan_and_table"]),
                "to_parser": len(data["to_parser"]),
                "time_seconds": pdf_time,
                "status": "SUCCESS",
                "error": "",
            }
        )

    except Exception as e:

        pdf_time = round(time.perf_counter() - pdf_start, 2)

        logger.error(
            f"FAILED | PDF={pdf_path.name} | "
            f"SIZE_MB={pdf_size_mb} | "
            f"TIME_SEC={pdf_time} | ERROR={e}"
        )

        execution_summary.append(
            {
                "source_pdf": pdf_path.name,
                "pdf_size_mb": pdf_size_mb,
                "total_pages": None,
                "text_pages": None,
                "scanned_pages": None,
                "pdf_scan_ratio": None,
                "table_pages": None,
                "scan_and_table": None,
                "to_parser": None,
                "time_seconds": pdf_time,
                "status": "FAILED",
                "error": str(e),
            }
        )

        print(f"\nFAILED → {pdf_path.name}")
        print(e)


csv_path = OUTPUT_DIR / "execution_summary.csv"

if execution_summary:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=execution_summary[0].keys())
        writer.writeheader()
        writer.writerows(execution_summary)


page_csv_path = OUTPUT_DIR / "page_summary.csv"

if page_summary:
    with open(page_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=page_summary[0].keys())
        writer.writeheader()
        writer.writerows(page_summary)


logger.info(
    f"ALL DONE | TOTAL_PDFS={len(pdf_files)} | "
    f"PDF_SUMMARY={csv_path} | "
    f"PAGE_SUMMARY={page_csv_path}"
)

print(f"\nPDF Summary → {csv_path}")
print(f"Page Summary → {page_csv_path}")
print("\nALL DONE.")
