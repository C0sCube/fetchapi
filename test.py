def normalize_dataframe(df):
    df = df.fillna("").copy()

    mask = df.map(
        lambda x: bool(NUM_LINE_RE.match(str(x).strip()))
    )

    col_types = [
        "Financial" if mask[col].mean() >= 0.5 else "Particulars"
        for col in df.columns
    ]

    metadata = {
        col: {"audit": "", "date": ""}
        for col in df.columns
    }

    rows_to_remove = []

    for idx, row in df.iterrows():

        is_metadata_row = False

        for col, value in row.items():

            value = str(value).strip()

            m = AUDIT_RE.search(value)
            if m:
                metadata[col]["audit"] = (
                    metadata[col]["audit"]
                    or m.group(0).title()
                )
                is_metadata_row = True

            dt = extract_date(value)
            if dt:
                metadata[col]["date"] = (
                    metadata[col]["date"]
                    or dt.strftime("%d-%m-%Y")
                )
                is_metadata_row = True

        if is_metadata_row:
            rows_to_remove.append(idx)

    body_df = df.drop(rows_to_remove).reset_index(drop=True)

    header_df = pd.DataFrame(
        [
            col_types,
            [metadata[c]["audit"] for c in df.columns],
            [metadata[c]["date"] for c in df.columns],
        ],
        columns=df.columns,
        index=["COLUMN_TYPE", "AUDIT", "DATE"],
    )

    final_df = pd.concat([header_df, body_df])

    return final_df, metadata
