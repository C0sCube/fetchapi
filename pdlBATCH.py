from pathlib import Path
import json, time, gc
import pandas as pd
import psutil
from paddleocr import PaddleOCRVL  # type: ignore

# PDF
#  ↓
# PDF parsing/rendering
#  ↓
# PP-DocLayoutV3
#  ↓
# image preprocessing
#  ↓
# PaddleOCR-VL 0.9B
#  ↓
# vision encoder
#  ↓
# LLM/VLM generation
#  ↓
# Markdown / blocks

BATCH_DIR = Path(r"E:\conda-envs\input_text\single")
OUTPUT_DIR = Path("batch_results")
OUTPUT_DIR.mkdir(exist_ok=True)
RESULT_XLSX = OUTPUT_DIR / "sheet_data.xlsx"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# GPU monitoring

import pynvml  # type: ignore

pynvml.nvmlInit()
GPU_AVAILABLE = True
GPU_COUNT = pynvml.nvmlDeviceGetCount()
GPU_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)


def get_gpu_memory_mb():
    if not GPU_AVAILABLE:
        return None
    try:
        mem = pynvml.nvmlDeviceGetMemoryInfo(GPU_HANDLE)
        return mem.used / (1024**2)
    except Exception:
        return None


def get_gpu_total_mb():
    if not GPU_AVAILABLE:
        return None
    try:
        mem = pynvml.nvmlDeviceGetMemoryInfo(GPU_HANDLE)
        return mem.total / (1024**2)
    except Exception:
        return None


def get_ram_used_mb():
    return psutil.virtual_memory().used / (1024**2)


def get_ram_percent():
    return psutil.virtual_memory().percent


# Batch PDFs
batch_files = sorted(BATCH_DIR.glob("*.pdf"))

print(f"Batch PDFs: {len(batch_files)}")

# Initialize OCR once
print("\nInitializing PaddleOCR-VL...")
pipeline_init_start = time.perf_counter()
# pipeline = PaddleOCRVL()

# pipeline = PaddleOCRVL(
#     use_doc_orientation_classify=True,
#     use_doc_unwarping=False,
#     use_chart_recognition=False,
#     use_seal_recognition=False,
#     use_queues=True,
#     vl_rec_backend="native",
# )

pipeline = PaddleOCRVL(
    # pipeline_version="v1.5",  # "v1.5" "v1.6"
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_layout_detection=True,
    use_chart_recognition=False,
    use_seal_recognition=False,
    use_ocr_for_image_block=True,
    format_block_content=True,
    # merge_layout_blocks=False,
    layout_nms=True,  # NMS removes overlapping duplicates.
    vl_rec_backend="native",
    use_queues=True,
)

pipeline_init_time = time.perf_counter() - pipeline_init_start
print(f"Initialized in {pipeline_init_time:.2f} sec")

batch_metrics = []
batch_results = {}
total_start = time.perf_counter()

# Process batches
for batch_id, batch_pdf in enumerate(batch_files, 1):

    print(f"\n{'=' * 60}")
    print(f"BATCH {batch_id}: {batch_pdf.name}")
    print("=" * 60)

    batch_start = time.perf_counter()

    ram_before = get_ram_used_mb()
    ram_percent_before = get_ram_percent()
    gpu_before = get_gpu_memory_mb()

    # PaddleOCR inference
    ram_inference_before = get_ram_used_mb()
    gpu_inference_before = get_gpu_memory_mb()

    inference_start = time.perf_counter()

    print("  Calling pipeline.predict()...", flush=True)

    # results = pipeline.predict(str(batch_pdf))
    results = pipeline.predict(str(batch_pdf), prompt_label="table")

    print("  pipeline.predict() returned.", flush=True)

    pages = []
    result_count = 0

    batch_gpu_peak = gpu_inference_before
    batch_ram_peak = ram_inference_before

    for page_num, result in enumerate(results, 1):

        result_count += 1

        blocks = [
            {"label": item.label, "bbox": list(item.bbox), "content": item.content}
            for item in result["parsing_res_list"]
        ]

        markdown = result.markdown["markdown_texts"]

        current_gpu = get_gpu_memory_mb()
        current_ram = get_ram_used_mb()

        if current_gpu is not None:
            batch_gpu_peak = max(batch_gpu_peak or current_gpu, current_gpu)

        batch_ram_peak = max(batch_ram_peak, current_ram)

        pages.append({"page": page_num, "blocks": blocks, "markdown": markdown})

        print(f"  Page {page_num}")

    inference_time = time.perf_counter() - inference_start

    ram_after = get_ram_used_mb()
    ram_percent_after = get_ram_percent()
    gpu_after = get_gpu_memory_mb()

    gpu_peak_delta = (
        batch_gpu_peak - gpu_inference_before
        if batch_gpu_peak is not None and gpu_inference_before is not None
        else None
    )

    ram_peak_delta = batch_ram_peak - ram_inference_before
    batch_total_time = time.perf_counter() - batch_start

    pages_per_sec = result_count / inference_time if inference_time > 0 else None

    # Save batch JSON
    batch_results[batch_pdf.stem] = {"batch": batch_pdf.name, "pages": pages}

    json_path = OUTPUT_DIR / f"{batch_pdf.stem}.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(batch_results[batch_pdf.stem], f, indent=2, ensure_ascii=False)

    # Batch metrics
    batch_metrics.append(
        {
            "batch_id": batch_id,
            "batch_pdf": batch_pdf.name,
            "batch_size": result_count,
            "result_count": result_count,
            "inference_sec": round(inference_time, 4),
            "batch_total_sec": round(batch_total_time, 4),
            "pages_per_sec": round(pages_per_sec, 4) if pages_per_sec else None,
            "ram_before_mb": round(ram_before, 2),
            "ram_inference_before_mb": round(ram_inference_before, 2),
            "ram_peak_mb": round(batch_ram_peak, 2),
            "ram_after_mb": round(ram_after, 2),
            "ram_peak_delta_mb": round(ram_peak_delta, 2),
            "ram_percent_before": round(ram_percent_before, 2),
            "ram_percent_after": round(ram_percent_after, 2),
            "gpu_total_mb": (
                round(get_gpu_total_mb(), 2) if get_gpu_total_mb() is not None else None
            ),
            "gpu_before_mb": round(gpu_before, 2) if gpu_before is not None else None,
            "gpu_inference_before_mb": (
                round(gpu_inference_before, 2)
                if gpu_inference_before is not None
                else None
            ),
            "gpu_peak_mb": (
                round(batch_gpu_peak, 2) if batch_gpu_peak is not None else None
            ),
            "gpu_after_mb": round(gpu_after, 2) if gpu_after is not None else None,
            "gpu_peak_delta_mb": (
                round(gpu_peak_delta, 2) if gpu_peak_delta is not None else None
            ),
            "gpu_count": GPU_COUNT,
        }
    )

    print(f"  Pages/sec : {pages_per_sec:.3f}")
    print(f"  Inference : {inference_time:.2f}s")
    print(f"  Total     : {batch_total_time:.2f}s")
    print(f"  RAM peak  : {batch_ram_peak:.2f} MB")
    print(
        f"  GPU peak  : {batch_gpu_peak:.2f} MB"
        if batch_gpu_peak is not None
        else "  GPU peak  : N/A"
    )

    del results
    gc.collect()


# Total
total_time = time.perf_counter() - total_start

print(f"\n{'=' * 60}")
print(f"TOTAL TIME: {total_time:.2f}s")
print("=" * 60)

# Excel
batch_df = pd.DataFrame(batch_metrics)

summary_df = pd.DataFrame(
    [
        {
            "total_batches": len(batch_files),
            "pipeline_init_sec": round(pipeline_init_time, 4),
            "total_time_sec": round(total_time, 4),
            "gpu_count": GPU_COUNT,
        }
    ]
)

with pd.ExcelWriter(RESULT_XLSX, engine="openpyxl") as writer:
    batch_df.to_excel(writer, sheet_name="batch_metrics", index=False)
    summary_df.to_excel(writer, sheet_name="summary", index=False)

print(f"\nExcel saved: {RESULT_XLSX}")
print("Done.")
