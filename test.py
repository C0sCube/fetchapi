base_html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Extracted Tables</title>
<style>
body {
    font-family: Arial, sans-serif;
    margin: 30px;
}
.source {
    font-size: 18px;
    font-weight: bold;
    margin-top: 40px;
    margin-bottom: 20px;
}
.figure-title {
    font-size: 16px;
    font-weight: bold;
    margin: 20px 0 10px;
}

table {
    border-collapse: collapse;
    margin-bottom: 40px;
}

td, th {
    border: 1px solid #999;
    padding: 6px;
}
</style>
</head>
<body>

<h1>Extracted Tables</h1>
"""


def clean_table(table_html):
    """
    Clean HTML table output.

    - Removes completely empty rows.
    - Normalizes multiline cell content.
    - Replaces line breaks inside cells with <br>.
    """

    soup = BeautifulSoup(
        table_html,
        "html.parser",
    )

    table = soup.find("table")

    if table is None:
        return table_html

    for row in table.find_all("tr"):

        cells = row.find_all(["td", "th"])

        # Remove rows without cells
        if not cells:
            row.decompose()
            continue

        # Remove completely empty rows
        if all(not cell.get_text(strip=True) for cell in cells):
            row.decompose()
            continue

        # Clean individual cells
        for cell in cells:

            text = cell.get_text()

            parts = [part.strip() for part in text.splitlines() if part.strip()]

            cell.clear()

            for i, part in enumerate(parts):

                if i:
                    cell.append(soup.new_tag("br"))

                cell.append(part)

    return str(table)


# ============================================================
# DATAFRAME NORMALIZATION
# ============================================================


def normalize_dataframe(df):
    """
    Normalize extracted financial tables.

    Adds three metadata rows:

        COLUMN_TYPE
        AUDIT
        DATE

    COLUMN_TYPE:
        Financial   -> >= 50% of cells are numeric
        Particulars -> otherwise

    Metadata rows detected inside the original table are removed
    from the table body.
    """

    df = df.fillna("").copy()

    # --------------------------------------------------------
    # Classify cells as numeric/non-numeric
    # --------------------------------------------------------

    mask = df.map(lambda x: bool(NUM_LINE_RE.match(str(x).strip())))

    # --------------------------------------------------------
    # Determine column types
    # --------------------------------------------------------

    col_types = [
        ("Financial" if mask[col].mean() >= 0.5 else "Particulars")
        for col in df.columns
    ]

    # --------------------------------------------------------
    # Metadata storage
    # --------------------------------------------------------

    metadata = {
        col: {
            "audit": "",
            "date": "",
        }
        for col in df.columns
    }

    rows_to_remove = []

    # --------------------------------------------------------
    # Detect audit/date metadata rows
    # --------------------------------------------------------

    for idx, row in df.iterrows():

        is_metadata_row = False

        for col, value in row.items():

            value = str(value).strip()

            if not value:
                continue

            # Audit status
            audit_match = AUDIT_RE.search(value)

            if audit_match:

                if not metadata[col]["audit"]:
                    metadata[col]["audit"] = audit_match.group(0).title()

                is_metadata_row = True

            # Date
            dt = extract_date(value)

            if dt:

                if not metadata[col]["date"]:
                    metadata[col]["date"] = dt.strftime("%d-%m-%Y")

                is_metadata_row = True

        if is_metadata_row:
            rows_to_remove.append(idx)

    # --------------------------------------------------------
    # Remove metadata rows from body
    # --------------------------------------------------------

    body_df = df.drop(rows_to_remove).reset_index(drop=True)

    # --------------------------------------------------------
    # Create metadata header
    # --------------------------------------------------------

    header_df = pd.DataFrame(
        [
            col_types,
            [metadata[col]["audit"] for col in df.columns],
            [metadata[col]["date"] for col in df.columns],
        ],
        columns=df.columns,
        index=[
            "COLUMN_TYPE",
            "AUDIT",
            "DATE",
        ],
    )

    # --------------------------------------------------------
    # Combine metadata + table body
    # --------------------------------------------------------

    final_df = pd.concat(
        [
            header_df,
            body_df,
        ]
    )

    return final_df, metadata


# ============================================================
# PROCESS JSON FILES
# ============================================================

for json_file in sorted(JSON_DIR.glob("*.json")):

    print(f"Processing: {json_file.name}")

    # IMPORTANT:
    # Keep this inside the JSON loop so data from one JSON
    # does not appear in another JSON's workbook.
    all_dfs = {}

    html = base_html

    HTML_OUT = JSON_DIR / f"{json_file.stem}.html"
    XLS_OUT = JSON_DIR / f"{json_file.stem}.xlsx"

    # --------------------------------------------------------
    # Load JSON
    # --------------------------------------------------------

    with open(
        json_file,
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    # --------------------------------------------------------
    # Process pages
    # --------------------------------------------------------

    for page_data in data["pages"]:

        pdf_name = data["batch"]
        page_num = page_data["page"]
        blocks = page_data["blocks"]

        current_title = None
        page_has_table = False
        table_num = 0

        # ----------------------------------------------------
        # Process blocks
        # ----------------------------------------------------

        for block in blocks:

            label = str(block.get("label", "")).lower().strip()

            content = block.get("content", "")

            # ------------------------------------------------
            # Capture figure/table title
            # ------------------------------------------------

            if label == "figure_title":
                current_title = content
                continue

            # Ignore anything that isn't a table
            if label != "table":
                continue

            table_num += 1

            # ------------------------------------------------
            # Add page/source heading once
            # ------------------------------------------------

            if not page_has_table:

                html += f"""
<div class="source">
    {pdf_name} | Page {page_num}
</div>
"""

                page_has_table = True

            # ------------------------------------------------
            # Add figure title
            # ------------------------------------------------

            if current_title:

                html += f"""
<div class="figure-title">
    {current_title}
</div>
"""

                current_title = None

            # ------------------------------------------------
            # Clean HTML table
            # ------------------------------------------------

            table = clean_table(content)

            html += f"""
<div>
    {table}
</div>
"""

            # ------------------------------------------------
            # HTML -> DataFrame
            # ------------------------------------------------

            try:

                tables = pd.read_html(StringIO(table))

                if not tables:
                    print(
                        f"  No readable table found "
                        f"on page {page_num}, "
                        f"table {table_num}"
                    )
                    continue

                df = tables[0]

            except (ValueError, ImportError) as exc:

                print(
                    f"  Failed to parse table "
                    f"on page {page_num}, "
                    f"table {table_num}: {exc}"
                )

                continue

            # ------------------------------------------------
            # Clean DataFrame strings
            # ------------------------------------------------

            df = df.fillna("")

            df = df.map(lambda x: " ".join(str(x).split()))

            # ------------------------------------------------
            # Normalize
            # ------------------------------------------------

            normalized_df, metadata = normalize_dataframe(df)

            # ------------------------------------------------
            # Store table
            #
            # Don't use only page_num because multiple tables
            # on the same page would overwrite each other.
            # ------------------------------------------------

            sheet_name = f"page_{page_num}_table_{table_num}"

            all_dfs[sheet_name] = normalized_df

    # --------------------------------------------------------
    # Finish HTML
    # --------------------------------------------------------

    html += """
</body>
</html>
"""

    # --------------------------------------------------------
    # Save HTML
    # --------------------------------------------------------

    with open(
        HTML_OUT,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(html)

    print(f"Saved HTML: {HTML_OUT}")

    # --------------------------------------------------------
    # Save Excel
    # --------------------------------------------------------

    if all_dfs:

        with pd.ExcelWriter(
            XLS_OUT,
            engine="openpyxl",
        ) as writer:

            for sheet_name, df in all_dfs.items():

                # Excel worksheet names have a 31-char limit
                safe_sheet_name = sheet_name[:31]

                df.to_excel(
                    writer,
                    sheet_name=safe_sheet_name,
                    index=True,
                )

        print(f"Saved Excel: {XLS_OUT}")

    else:
        print(f"No tables found in {json_file.name}; " "Excel file not created.")

    print()


print("Done.")
