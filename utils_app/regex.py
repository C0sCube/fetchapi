import re

# Financial period

PERIOD_PATTERN = re.compile(
    r"ENDED\s+(.*)",
    re.IGNORECASE
)

YEAR_PATTERN = re.compile(
    r"(20\d{2})"
)

FINANCIAL_YEAR_PATTERN = re.compile(
    r"\b20\d{2}\s*[-/]\s*20\d{2}\b",
    re.IGNORECASE
)

DATE_PATTERN = re.compile(
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
)

MONTH_DATE_PATTERN = re.compile(
    r"\d{1,2}\s+"
    r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|"
    r"JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)"
    r"\s+\d{4}",
    re.IGNORECASE
)

# Currency and units

CURRENCY_PATTERN = re.compile(
    r"(₹|RS\.?|INR|RUPEES)",
    re.IGNORECASE
)

UNIT_PATTERN = re.compile(
    r"(LAKH|LAKHS|CRORE|CRORES|THOUSAND|"
    r"MILLION|BILLION)",
    re.IGNORECASE
)

# Company detection

COMPANY_PATTERN = re.compile(
    r".*(LIMITED|LTD|PRIVATE LIMITED|PVT\.?\s*LTD).*",
    re.IGNORECASE
)

# Report type

STANDALONE_PATTERN = re.compile(
    r"\bSTANDALONE\b",
    re.IGNORECASE
)

CONSOLIDATED_PATTERN = re.compile(
    r"\bCONSOLIDATED\b",
    re.IGNORECASE
)

# Financial statements

BALANCE_SHEET_PATTERN = re.compile(
    r"BALANCE\s+SHEET|STATEMENT\s+OF\s+FINANCIAL\s+POSITION",
    re.IGNORECASE
)

PROFIT_LOSS_PATTERN = re.compile(
    r"PROFIT\s+AND\s+LOSS|"
    r"STATEMENT\s+OF\s+PROFIT|"
    r"FINANCIAL\s+RESULTS",
    re.IGNORECASE
)

CASH_FLOW_PATTERN = re.compile(
    r"CASH\s+FLOW",
    re.IGNORECASE
)

SEGMENT_PATTERN = re.compile(
    r"SEGMENT",
    re.IGNORECASE
)

# Notes

NOTE_PATTERN = re.compile(
    r"NOTE\s*\d+",
    re.IGNORECASE
)

# Numbers

NUMBER_PATTERN = re.compile(
    r"[-+]?\d[\d,]*\.?\d*"
)

NEGATIVE_NUMBER_PATTERN = re.compile(
    r"\(\s*\d[\d,]*\.?\d*\s*\)"
)

PERCENT_PATTERN = re.compile(
    r"\d+(\.\d+)?%"
)

# Empty values

EMPTY_PATTERN = re.compile(
    r"^\s*$"
)