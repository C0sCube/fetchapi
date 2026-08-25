from pathlib import Path
import json, time, gc, re

import pandas as pd
import psutil

from paddleocr import PaddleOCRVL  # type: ignore

BATCH_DIR = Path(r"D:\Q1_CLEAN_PDFS_v1")
OUTPUT_DIR = Path(r"D:\Q1_CLEAN_PDFS_v1\batch_results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METRICS_CSV = OUTPUT_DIR / "batch_metrics.csv"
SUMMARY_JSON = OUTPUT_DIR / "summary.json"


try:

    import pynvml  # type: ignore

    pynvml.nvmlInit()

    GPU_AVAILABLE = True
    GPU_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)

except Exception:

    GPU_AVAILABLE = False
    GPU_HANDLE = None


def get_gpu_memory_mb():

    if not GPU_AVAILABLE:
        return None

    try:

        mem = pynvml.nvmlDeviceGetMemoryInfo(GPU_HANDLE)

        return mem.used / (1024**2)

    except Exception:

        return None


def get_ram_used_mb():

    return psutil.virtual_memory().used / (1024**2)


batch_files = sorted(
    BATCH_DIR.glob("*.pdf"),
    key=lambda x: [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", x.stem)
    ],
)[1:]

print(f"Batch PDFs: {len(batch_files)}")


print("\nInitializing PaddleOCR-VL...")

pipeline_init_start = time.perf_counter()


pipeline = PaddleOCRVL(
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_layout_detection=True,
    use_chart_recognition=False,
    use_seal_recognition=False,
    use_ocr_for_image_block=True,
    format_block_content=True,
    layout_nms=True,
    vl_rec_backend="native",
    use_queues=True,
)


pipeline_init_time = time.perf_counter() - pipeline_init_start

print(f"Initialized in {pipeline_init_time:.2f} sec")


batch_metrics = []
batch_results = {}

total_start = time.perf_counter()


for batch_id, batch_pdf in enumerate(batch_files, 1):

    print(f"\n{'=' * 60}")
    print(f"BATCH {batch_id}: {batch_pdf.name}")
    print("=" * 60)

    batch_start = time.perf_counter()

    ram_peak = get_ram_used_mb()
    gpu_peak = get_gpu_memory_mb()

    inference_start = time.perf_counter()

    print("Calling pipeline.predict()...", flush=True)

    results = pipeline.predict(
        str(batch_pdf),
        prompt_label="table",
    )

    print("pipeline.predict() returned.", flush=True)

    pages = []
    result_count = 0

    for page_num, result in enumerate(results, 1):

        result_count += 1

        blocks = [
            {
                "label": item.label,
                "bbox": list(item.bbox),
                "content": item.content,
            }
            for item in result["parsing_res_list"]
        ]

        markdown = result.markdown["markdown_texts"]

        current_ram = get_ram_used_mb()
        ram_peak = max(ram_peak, current_ram)

        current_gpu = get_gpu_memory_mb()

        if current_gpu is not None:
            gpu_peak = max(gpu_peak or 0, current_gpu)

        pages.append(
            {
                "page": page_num,
                "blocks": blocks,
                "markdown": markdown,
            }
        )

        print(f"Page {page_num}")

    inference_time = time.perf_counter() - inference_start
    batch_total_time = time.perf_counter() - batch_start

    pages_per_sec = result_count / inference_time if inference_time > 0 else 0

    avg_sec_per_page = inference_time / result_count if result_count > 0 else 0

    # Save OCR results

    batch_results[batch_pdf.stem] = {
        "batch": batch_pdf.name,
        "pages": pages,
    }

    json_path = OUTPUT_DIR / f"{batch_pdf.stem}.json"

    with open(json_path, "w", encoding="utf-8") as f:

        json.dump(
            batch_results[batch_pdf.stem],
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Save useful metrics

    batch_metrics.append(
        {
            "batch_id": batch_id,
            "batch_pdf": batch_pdf.name,
            "pages": result_count,
            "inference_sec": round(inference_time, 4),
            "total_sec": round(batch_total_time, 4),
            "pages_per_sec": round(pages_per_sec, 4),
            "avg_sec_per_page": round(avg_sec_per_page, 4),
            "ram_peak_mb": round(ram_peak, 2),
            "gpu_peak_mb": (round(gpu_peak, 2) if gpu_peak is not None else None),
        }
    )

    print(f"Pages        : {result_count}")
    print(f"Inference    : {inference_time:.2f}s")
    print(f"Total        : {batch_total_time:.2f}s")
    print(f"Pages/sec    : {pages_per_sec:.3f}")
    print(f"Avg sec/page : {avg_sec_per_page:.3f}")
    print(f"RAM peak     : {ram_peak:.2f} MB")

    print(
        f"GPU peak     : {gpu_peak:.2f} MB"
        if gpu_peak is not None
        else "GPU peak     : N/A"
    )

    del results
    gc.collect()


total_time = time.perf_counter() - total_start

total_pages = sum(metric["pages"] for metric in batch_metrics)

avg_pages_per_sec = total_pages / total_time if total_time > 0 else 0


batch_df = pd.DataFrame(batch_metrics)

batch_df.to_csv(
    METRICS_CSV,
    index=False,
)


summary = {
    "total_batches": len(batch_files),
    "total_pages": total_pages,
    "pipeline_init_sec": round(pipeline_init_time, 4),
    "total_time_sec": round(total_time, 4),
    "avg_pages_per_sec": round(avg_pages_per_sec, 4),
}


with open(SUMMARY_JSON, "w", encoding="utf-8") as f:

    json.dump(
        summary,
        f,
        indent=2,
    )


print(f"\n{'=' * 60}")
print(f"TOTAL TIME: {total_time:.2f}s")
print(f"TOTAL PAGES: {total_pages}")
print(f"AVG PAGES/SEC: {avg_pages_per_sec:.4f}")
print("=" * 60)

print(f"\nMetrics saved: {METRICS_CSV}")
print(f"Summary saved: {SUMMARY_JSON}")
print("Done.")
