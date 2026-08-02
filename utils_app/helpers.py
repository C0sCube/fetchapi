from pathlib import Path
from typing import Iterable, Optional


def ensure_directory(path):

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    return path


def safe_upper(text):

    if text is None:
        return ""

    return str(text).strip().upper()


def safe_lower(text):

    if text is None:
        return ""

    return str(text).strip().lower()


def clean_text(text):

    if text is None:
        return ""

    return " ".join(str(text).split())


def first_match(text, keywords):

    text = safe_upper(text)

    for keyword in keywords:

        if keyword.upper() in text:
            return keyword

    return None


def contains_any(text, keywords):

    text = safe_upper(text)

    return any(
        keyword.upper() in text
        for keyword in keywords
    )


def unique_list(values):

    seen = set()

    output = []

    for value in values:

        if value in seen:
            continue

        seen.add(value)
        output.append(value)

    return output


def chunk_list(values, chunk_size):

    for i in range(0, len(values), chunk_size):

        yield values[i:i + chunk_size]


def get_page_numbers(doc):

    pages = set()

    for text in doc.texts:

        if text.prov:

            pages.add(
                text.prov[0].page_no
            )

    return sorted(pages)


def file_exists(path):

    return Path(path).exists()


def get_file_name(path):

    return Path(path).name


def get_file_stem(path):

    return Path(path).stem


def get_extension(path):

    return Path(path).suffix.lower()


def flatten(items):

    output = []

    for item in items:

        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):

            output.extend(item)

        else:

            output.append(item)

    return output


def safe_max(values, default=0):

    if not values:

        return default

    return max(values)


def safe_min(values, default=0):

    if not values:

        return default

    return min(values)


def get_table_id(page_no, table_no):

    return f"P{page_no}_T{table_no}"


def clamp(value, minimum, maximum):

    return max(minimum, min(value, maximum))


def is_blank(text):

    return clean_text(text) == ""


def not_blank(text):

    return not is_blank(text)


def elapsed_message(seconds):

    return f"{seconds:.2f} sec"
