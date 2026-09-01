import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ELRF WhatsApp Monitoring Extractor",
    layout="wide"
)


# ============================================================
# OUTPUT COLUMNS
# ============================================================

COLUMNS = [
    "County",
    "Country",
    "planting_site",
    "Check",
    "type_of_plot",
    "plot_number",
    "monitoring_month",
    "monitoring_year",
    "monitoring_date",
    "planting_date",
    "latitude",
    "longitude",
    "planting_materials",
    "species_planted",
    "partner",
    "zonation",
    "ecosystem type",
    "trees_age",
    "natural_regenation",
    "re_planted_alive",
    "old_samplings_alive",
    "total_alive",
    "dead",
    "dormant",
    "total_planted",
    "area_restored_ha",
    "spacing_m",
    "salinity",
    "dbh_mm",
    "height_cm",
    "no_of_leaves",
    "branches",
    "Disturbance",
    "Recommendation",
    "Comment",
    "planting_id"
]


# ============================================================
# SPECIES ABBREVIATIONS / NORMALIZATION
# ============================================================

SPECIES_MAP = {

    # Ceriops tagal
    "ct": "Ceriops tagal",
    "c.t": "Ceriops tagal",
    "c.tagal": "Ceriops tagal",
    "ceriops tagal": "Ceriops tagal",

    # Rhizophora mucronata
    "rm": "Rhizophora mucronata",
    "r.m": "Rhizophora mucronata",
    "r.mucronata": "Rhizophora mucronata",
    "rhizophora mucronata": "Rhizophora mucronata",

    # Common WhatsApp spelling
    "rhizophorus mucronata": "Rhizophora mucronata",

    # Avicennia marina
    "am": "Avicennia marina",
    "a.m": "Avicennia marina",
    "a.marina": "Avicennia marina",
    "avicennia marina": "Avicennia marina",

    # Bruguiera gymnorhiza
    "bg": "Bruguiera gymnorhiza",
    "b.g": "Bruguiera gymnorhiza",
    "b.gymnorhiza": "Bruguiera gymnorhiza",
    "bruguiera gymnorhiza": "Bruguiera gymnorhiza",

    # Xylocarpus granatum
    "xg": "Xylocarpus granatum",
    "x.granatum": "Xylocarpus granatum",
    "xylocarpus granatum": "Xylocarpus granatum",

    # Lumnitzera racemosa
    "lr": "Lumnitzera racemosa",
    "l.r": "Lumnitzera racemosa",
    "l.racemosa": "Lumnitzera racemosa",
    "lumnitzera racemosa": "Lumnitzera racemosa"
}


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):

    if value is None:
        return None

    value = str(value)

    value = value.replace("\r", "")

    value = re.sub(
        r"[ \t]+",
        " ",
        value
    )

    value = re.sub(
        r"\n+",
        "\n",
        value
    )

    return value.strip()


# ============================================================
# FIND VALUE
# ============================================================

def find_value(
    text,
    pattern,
    default=None,
    flags=re.IGNORECASE
):

    match = re.search(
        pattern,
        text,
        flags
    )

    if match:

        return clean_text(
            match.group(1)
        )

    return default


# ============================================================
# NUMBER
# ============================================================

def parse_number(value):

    if value is None:
        return None

    value = str(value)

    value = value.replace(",", "")

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    try:

        return float(
            match.group(0)
        )

    except:

        return None


# ============================================================
# DATE PARSER
# ============================================================

def parse_date(date_text):

    if not date_text:
        return None

    date_text = clean_text(
        date_text
    )

    # Remove ordinal suffixes
    date_text = re.sub(
        r"(\d)(st|nd|rd|th)",
        r"\1",
        date_text,
        flags=re.IGNORECASE
    )

    date_text = date_text.replace(
        ",",
        ""
    )

    date_text = re.sub(
        r"\s+",
        " ",
        date_text
    ).strip()

    formats = [

        "%d/%m/%Y",
        "%d/%m/%y",

        "%d-%m-%Y",
        "%d-%m-%y",

        "%d %B %Y",
        "%d %b %Y"
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                date_text,
                fmt
            ).date()

        except ValueError:

            continue

    return None


# ============================================================
# TREE AGE
#
# <12 months      = 0
# 12–23 months    = 1
# 24–35 months    = 2
# 36–47 months    = 3
# etc.
# ============================================================

def calculate_age_years(
    planting_date,
    monitoring_date
):

    if not planting_date:
        return None

    if not monitoring_date:
        return None

    if monitoring_date < planting_date:
        return None

    years = (
        monitoring_date.year
        - planting_date.year
    )

    if (
        monitoring_date.month,
        monitoring_date.day
    ) < (
        planting_date.month,
        planting_date.day
    ):

        years -= 1

    return max(
        int(years),
        0
    )


# ============================================================
# SPECIES NORMALIZATION
# ============================================================

def normalize_species_text(value):

    if not value:
        return None

    value = clean_text(
        value
    )

    value = value.replace(
        "*",
        ""
    )

    value = value.replace(
        "_",
        ""
    )

    # --------------------------------------------------------
    # Remove quantities
    # Examples:
    # 3,127 CT
    # 281 RM
    # 13,061 RM
    # --------------------------------------------------------

    value = re.sub(
        r"\b\d[\d,]*(?:\.\d+)?\s*",
        "",
        value
    )

    # --------------------------------------------------------
    # Remove material descriptions
    # --------------------------------------------------------

    value = re.sub(
        r"\b(?:propagules?|propergules?|seedlings?|"
        r"wildings?|seeds?|trees?)\b",
        "",
        value,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # Replace separators
    # --------------------------------------------------------

    value = re.sub(
        r"\s*(?:&|and|\+|/|,)\s*",
        " & ",
        value,
        flags=re.IGNORECASE
    )

    parts = re.split(
        r"\s*&\s*",
        value
    )

    normalized = []

    for part in parts:

        part = part.strip(
            " .:-"
        )

        if not part:
            continue

        key = part.lower().strip()

        # Direct map
        if key in SPECIES_MAP:

            name = SPECIES_MAP[key]

            if name not in normalized:

                normalized.append(
                    name
                )

            continue

        # Search known species
        found = False

        for short_name, full_name in SPECIES_MAP.items():

            if re.search(
                rf"\b{re.escape(short_name)}\b",
                key
            ):

                if full_name not in normalized:

                    normalized.append(
                        full_name
                    )

                found = True

                break

        if not found:

            part = re.sub(
                r"\d[\d,]*",
                "",
                part
            ).strip()

            if part:

                normalized.append(
                    part
                )

    if not normalized:
        return None

    return " & ".join(
        normalized
    )


# ============================================================
# SPECIES + MATERIAL
# ============================================================

def extract_species_and_material(text):
    """Extract species and planting material from both inline and multiline WhatsApp formats.

    Supports examples such as:
      Tree Species planted : Ceriops tagal
      Species planted
      *Ceriops tagal propergules - 3621
      *RM propergules -712 Total planted-4333
      Species planted: CT Sd
    """
    # --------------------------------------------------------
    # 1. Find the species header.
    # --------------------------------------------------------
    header_patterns = [
        r"^\s*Tree\s+Species\s+planted[ \t]*:?[ \t]*(.*)$",
        r"^\s*Trees\s+species\s+planted[ \t]*:?[ \t]*(.*)$",
        r"^\s*Species\s+planted[ \t]*:?[ \t]*(.*)$",
        r"^\s*Tree\s+species\s+planted[ \t]*:?[ \t]*(.*)$",
        r"^\s*Species[ \t]*:?[ \t]*(.*)$",
    ]

    header_match = None
    for pattern in header_patterns:
        header_match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if header_match:
            break

    if not header_match:
        return None, None

    inline_value = clean_text(header_match.group(1)) if header_match.group(1) else ""
    candidate_lines = []
    if inline_value:
        candidate_lines.append(inline_value)

    # --------------------------------------------------------
    # 2. If the header has no value, collect continuation lines
    #    until the next plot/observation field.
    # --------------------------------------------------------
    lines = text.splitlines()
    header_line_index = None
    for i, line in enumerate(lines):
        if re.search(
            r"^\s*(?:Tree\s+Species|Trees\s+species|Species)\s+planted[ \t]*:?.*$",
            line,
            flags=re.IGNORECASE,
        ):
            header_line_index = i
            break

    if header_line_index is not None and not inline_value:
        stop_pattern = re.compile(
            r"^\s*(?:"
            r"Coordinates?|Alive|Total\s+alive|Total\s+live\s+trees|"
            r"Dead|Mortality|Dormant|Natural\s+regeneration|Natural|"
            r"Regeneration\s+stage|Spacing|Disturbances?|Cause\s+mortality|"
            r"Plantable\s+area|Area\s+planted|Area|Zonation|Zone|"
            r"Plot\b|Check\b|Task\s*🆔?|Task\s*ID|ID\s*:|"
            r"Total\s+planted|No\.?\s*planted|Planting\s+date|Date\s+planted|"
            r"Monitoring\b"
            r")",
            re.IGNORECASE,
        )
        for line in lines[header_line_index + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stop_pattern.search(stripped):
                break
            candidate_lines.append(stripped)

    if not candidate_lines:
        return None, None

    # --------------------------------------------------------
    # 3. Keep only the species/material portion of each line.
    #    This is important for: "RM propergules -712 Total planted-4333".
    # --------------------------------------------------------
    species_parts = []
    material_values = []
    for line in candidate_lines:
        line = re.sub(r"Total\s+planted\s*[-:=]?\s*.*$", "", line, flags=re.IGNORECASE)
        line = re.sub(r"No\.?\s*planted\s*[-:=]?\s*.*$", "", line, flags=re.IGNORECASE)
        if not line.strip():
            continue
        species_parts.append(line.strip(" -*•"))
        lower = line.lower()
        if re.search(r"\bpropagules?|\bpropergules?|\bprop\b", lower):
            material_values.append("Propagules")
        elif re.search(r"\bseedlings?|\bsd\b", lower):
            material_values.append("Seedlings")
        elif re.search(r"\bwildings?\b", lower):
            material_values.append("Wildings")
        elif re.search(r"\bseeds?\b", lower):
            material_values.append("Seeds")

    # If the report gives several species, normalize each line and combine them.
    normalized_species = []
    for part in species_parts:
        normalized = normalize_species_text(part)
        if normalized:
            for item in normalized.split(" & "):
                if item not in normalized_species:
                    normalized_species.append(item)

    species = " & ".join(normalized_species) if normalized_species else None
    material = material_values[0] if material_values else None
    return species, material


# ============================================================
# PLANTING MATERIAL
# ============================================================

def extract_planting_material(text):
    """Extract planting material from explicit fields or total/species lines."""
    patterns = [
        r"^\s*Planting\s+materials?\s*:?\s*(.+)$",
        r"^\s*Planting\s+material\s*:?\s*(.+)$",
    ]
    values = []
    for pattern in patterns:
        values.extend(re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE))

    # Also support: Total planted :119,320CT Propagules
    values.extend(re.findall(
        r"^\s*(?:Total\s+(?:trees\s+)?planted|No\.?\s*planted)\s*[:=\-–—]?\s*(.*)$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ))

    for value in values:
        lower = str(value).lower()
        if re.search(r"propagules?|propergules?|prop\b", lower):
            return "Propagules"
        if re.search(r"seedlings?|sd\b", lower):
            return "Seedlings"
        if re.search(r"wildings?", lower):
            return "Wildings"
        if re.search(r"seeds?", lower):
            return "Seeds"
        if clean_text(value):
            return clean_text(value)
    return None


# ============================================================
# GENERAL INFORMATION
# ============================================================

def extract_general_information(text):
    """Extract report-level information.

    Report-level fields such as Site, County/Country, Forest type and the
    report Date are intentionally extracted from the complete report, while
    planting dates are extracted separately from each planting/monitoring
    session.
    """
    site = find_value(
        text,
        r"^\s*Site\s*:?\s*(.+)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    county = find_value(
        text,
        r"^\s*County\s*:?\s*(.+)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # Newer reports may use Country instead of County.
    country = find_value(
        text,
        r"^\s*Country\s*:?\s*(.+)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    forest_type = find_value(
        text,
        r"^\s*Forest\s+type\s*:?\s*(.+)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # --------------------------------------------------------
    # Report / monitoring date
    # --------------------------------------------------------
    monitoring_date_text = find_value(
        text,
        r"^\s*Date\s*:?\s*"
        r"(\d{1,2}(?:st|nd|rd|th)?[\/-]\d{1,2}[\/-]\d{2,4})",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    if not monitoring_date_text:
        monitoring_date_text = find_value(
            text,
            r"^\s*Date\s*:?\s*"
            r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:,\s*|\s+)\d{4})",
            flags=re.IGNORECASE | re.MULTILINE,
        )

    monitoring_date = parse_date(monitoring_date_text)

    observation = find_value(
        text,
        r"^\s*(?:General\s+Observation|Observation)\s*:?[ \t]*(.+)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    recommendation = find_value(
        text,
        r"^\s*Recommendation\s*:?[ \t]*(.+)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    return {
        "site": site,
        "county": county,
        "country": country,
        "forest_type": forest_type,
        "monitoring_date": monitoring_date,
        "observation": observation,
        "recommendation": recommendation,
    }


# ============================================================
# CHECK NUMBER
# ============================================================

def extract_check_number(text):

    # NOTE: no longer anchored with "\s*\*?\s*$" - reports
    # commonly add trailing annotations after the check
    # number, e.g. "Check 2 (CO)" or "Check 3*". Requiring
    # the line to end right after the number (or a single
    # "*") silently failed to match "Check 2 (CO)", leaving
    # the Check column empty. A digit directly after
    # "Check"/"CHECK" is a safe enough anchor on its own.
    match = re.search(
        r"^\s*(?:Check|CHECK)"
        r"\s*(\d+)"
        r".*$",

        text,

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    if match:

        return int(
            match.group(1)
        )

    return None


# ============================================================
# PLANTING DATE
#
# IMPORTANT:
# Do NOT use monitoring report date as planting date.
#
# Supports:
#
# Planting date: 18th May 2026
# Date planted: 21st May 2026
# Monitoring of 11th December 2024 planting
# 1. Monitoring of 14th April 2025 planting
# Monitoring May 2026 planting
# ============================================================

def extract_planting_date(text):

    # --------------------------------------------------------
    # Direct planting date
    # --------------------------------------------------------

    patterns = [

        # Planting date: 17/10/24
        r"^\s*(?:[-•*]\s*)?"
        r"Planting\s+date\s*:?\s*"
        r"(\d{1,2}/\d{1,2}/\d{2,4})",

        # Planting date: 18th May 2026
        r"^\s*(?:[-•*]\s*)?"
        r"Planting\s+date\s*:?\s*"
        r"(\d{1,2}"
        r"(?:st|nd|rd|th)?"
        r"\s+[A-Za-z]+"
        r"(?:,\s*|\s+)"
        r"\d{4})",

        # Date planted: 21st May 2026
        r"^\s*(?:[-•*]\s*)?"
        r"Date\s+planted\s*:?\s*"
        r"(\d{1,2}"
        r"(?:st|nd|rd|th)?"
        r"\s+[A-Za-z]+"
        r"(?:,\s*|\s+)"
        r"\d{4})",

        # Date planted: 21/05/2026
        r"^\s*(?:[-•*]\s*)?"
        r"Date\s+planted\s*:?\s*"
        r"(\d{1,2}/\d{1,2}/\d{2,4})"
    ]

    for pattern in patterns:

        value = find_value(
            text,
            pattern,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
            )
        )

        if value:

            parsed = parse_date(
                value
            )

            if parsed:
                return parsed

    # --------------------------------------------------------
    # Monitoring of 11th December 2024 planting
    #
    # Also:
    #
    # 1. Monitoring of 11th December 2024 planting
    # Check 3
    # 1. Monitoring of 14th April 2025 planting
    # --------------------------------------------------------

    long_date_pattern = re.compile(
        r"^\s*(?:\d+[\.\)]\s*)?"
        r"Monitoring\s+(?:of\s+)?"
        r"(\d{1,2}"
        r"(?:st|nd|rd|th)?"
        r"\s+[A-Za-z]+"
        r"(?:,\s*|\s+)"
        r"\d{4})"
        r"(?:\s+planting)?",

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    match = long_date_pattern.search(
        text
    )

    if match:

        parsed = parse_date(
            match.group(1)
        )

        if parsed:

            return parsed

    # --------------------------------------------------------
    # Monitoring of 14/04/2025 planting
    # --------------------------------------------------------

    numeric_pattern = re.compile(
        r"^\s*(?:\d+[\.\)]\s*)?"
        r"Monitoring\s+(?:of\s+)?"
        r"(\d{1,2}/\d{1,2}/\d{2,4})"
        r"(?:\s+planting)?",

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    match = numeric_pattern.search(
        text
    )

    if match:

        parsed = parse_date(
            match.group(1)
        )

        if parsed:

            return parsed

    # --------------------------------------------------------
    # UNLABELED PLANTING DATE
    # --------------------------------------------------------
    # Some WhatsApp reports use:
    #
    # Monitoring 2024 planting
    # ID :8712
    # P.A : N.A
    # 16/12/2024
    #
    # The date is the planting date even though it has no label.
    # IMPORTANT: this is intentionally evaluated on the CURRENT PLOT
    # TEXT, not the entire report, so the report date (e.g. 31/08/2026)
    # is never accidentally assigned to the planting session.
    #
    # Also supports standalone dates written as 16-12-2024 or 16.12.2024.
    # --------------------------------------------------------

    unlabeled_numeric_patterns = [
        r"^\s*(?:[-•*]\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*$",
        r"^\s*(?:[-•*]\s*)?(\d{1,2}\.\d{1,2}\.\d{2,4})\s*$",
    ]

    for pattern in unlabeled_numeric_patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE | re.MULTILINE
        ):
            parsed = parse_date(match.group(1))
            if parsed:
                return parsed

    # --------------------------------------------------------
    # UNLABELED LONG-FORM PLANTING DATE
    # --------------------------------------------------------
    # Example: 16th December 2024 on its own line.
    # --------------------------------------------------------

    unlabeled_long_pattern = re.compile(
        r"^\s*(?:[-•*]\s*)?"
        r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:,\s*|\s+)\d{4})\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    match = unlabeled_long_pattern.search(text)
    if match:
        parsed = parse_date(match.group(1))
        if parsed:
            return parsed

    # --------------------------------------------------------
    # Monitoring May 2026 planting
    # --------------------------------------------------------

    month_year_pattern = re.compile(
        r"^\s*(?:\d+[\.\)]\s*)?"
        r"Monitoring\s+"
        r"([A-Za-z]+)\s+(\d{4})"
        r"\s+planting",

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    match = month_year_pattern.search(
        text
    )

    if match:

        month = match.group(1)
        year = match.group(2)

        try:

            return datetime.strptime(
                f"1 {month} {year}",
                "%d %B %Y"
            ).date()

        except ValueError:

            try:

                return datetime.strptime(
                    f"1 {month} {year}",
                    "%d %b %Y"
                ).date()

            except ValueError:
                pass

    return None


# ============================================================
# PLANTING ID / SESSION ID
# ============================================================

def extract_planting_id(text):

    patterns = [

        # Planting ID: 21330
        r"^\s*Planting\s+ID\s*:?\s*(\d+)",

        # Planted Session ID: 8670
        r"^\s*Planted\s+Session\s+ID\s*:?\s*(\d+)",

        # Session ID: 8670
        r"^\s*Session\s+ID\s*:?\s*(\d+)",

        # ID: 8670
        r"^\s*ID\s*:?\s*(\d+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
            )
        )

        if match:

            return match.group(1)

    # Monitoring lines sometimes carry the planting ID in brackets,
    # e.g. "Monitoring of 28th Feb 2025 (ID:9747)".
    match = re.search(
        r"\bMonitoring\b[^\n]*?\(\s*ID\s*:\s*(\d+)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)

    return None


# ============================================================
# AREA
# ============================================================

def extract_area(text):

    patterns = [

        r"^\s*(?:Area\s+planted|Plantable\s+area|P\.A)"
        r"\s*:?\s*([^\n]+)",

        r"^\s*Area\s*:?\s*([^\n]+)"
    ]

    for pattern in patterns:

        value = find_value(
            text,
            pattern,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
            )
        )

        if value:

            if value.lower().strip() in [
                "nil",
                "none",
                "n/a",
                "na"
            ]:

                return None

            return parse_number(
                value
            )

    return None


# ============================================================
# TOTAL PLANTED
# ============================================================

def extract_total_planted(text):
    """Extract total planted from common WhatsApp variants.

    Supports:
      Total planted: 4333
      Total planted-4333
      Total planted - 4,333 CT
      Total planted :119,320CT Propagules
      No planted:107,800 CT
      No. Planted: 1,824 CT
    """
    patterns = [
        r"^\s*Total\s+(?:trees\s+)?planted\s*[:=\-–—]?\s*([\d,]+)",
        r"^\s*No\.?\s*planted\s*[:=\-–—]?\s*([\d,]+)",
        r"^\s*Number\s+planted\s*[:=\-–—]?\s*([\d,]+)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        for value in matches:
            number = parse_number(value)
            if number is not None:
                return int(number)
    inline_patterns = [
        r"\bTotal\s+(?:trees\s+)?planted\s*[:=\-–—]?\s*([\d,]+)",
        r"\bNo\.?\s*planted\s*[:=\-–—]?\s*([\d,]+)",
    ]
    for pattern in inline_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for value in matches:
            number = parse_number(value)
            if number is not None:
                return int(number)
    return None


# ============================================================
# SPACING
# ============================================================

def extract_spacing(text):

    value = find_value(
        text,
        r"^\s*Spacing"
        r"\s*:?\s*([\d.]+)",

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    return parse_number(
        value
    )


# ============================================================
# ZONATION
# ============================================================

def extract_zonation(text):

    value = find_value(
        text,
        r"^\s*(?:Zonation|Zone)"
        r"\s*:?\s*(.+)$",

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    if value:

        return value

    if re.search(
        r"\bGood\s+Zonation\b",
        text,
        re.IGNORECASE
    ):

        return "Good"

    if re.search(
        r"\bRight\s+Zonation\b",
        text,
        re.IGNORECASE
    ):

        return "Right"

    if re.search(
        r"\bWrong\s+Zonation\b",
        text,
        re.IGNORECASE
    ):

        return "Wrong"

    return None


# ============================================================
# DISTURBANCE
# ============================================================

def extract_disturbance(text):

    patterns = [

        r"^\s*Disturbances?"
        r"\s*:?\s*(.+)$",

        r"^\s*Cause\s+mortality"
        r"\s*:?\s*(.+)$"
    ]

    for pattern in patterns:

        value = find_value(
            text,
            pattern,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
            )
        )

        if value:

            return value

    return None


# ============================================================
# COORDINATES
# ============================================================

def parse_coordinates(text):

    # --------------------------------------------------------
    # latitude / longitude format
    # --------------------------------------------------------

    lat_match = re.search(
        r"\blat(?:itude)?\s*:?\s*"
        r"(-?\d+(?:\.\d+)?)",

        text,
        re.IGNORECASE
    )

    lon_match = re.search(
        r"\blong(?:itude)?\s*:?\s*"
        r"(-?\d+(?:\.\d+)?)",

        text,
        re.IGNORECASE
    )

    if lat_match and lon_match:

        return (
            float(
                lat_match.group(1)
            ),
            float(
                lon_match.group(1)
            )
        )

    # --------------------------------------------------------
    # Coordinates: lat, long
    # --------------------------------------------------------

    patterns = [

        r"Coordinates\s*:?\s*"
        r"(-?\d+(?:\.\d+)?)"
        r"\s*,\s*"
        r"(-?\d+(?:\.\d+)?)",

        r"Coordinates\s*:?\s*"
        r"(-?\d+(?:\.\d+)?)"
        r"\s+"
        r"(-?\d+(?:\.\d+)?)",

        # Bare coordinate line
        r"^\s*"
        r"(-?\d+\.\d+)"
        r"\s*,\s*"
        r"(-?\d+\.\d+)\s*$"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
            )
        )

        if match:

            return (
                float(
                    match.group(1)
                ),
                float(
                    match.group(2)
                )
            )

    return None, None


# ============================================================
# PLOT TYPE
# ============================================================

def extract_plot_type(
    plot_header
):

    if not plot_header:

        return "Monitoring Plot"

    if re.search(
        r"\btemporary\b",
        plot_header,
        re.IGNORECASE
    ):

        return "Temporary"


    if re.search(
        r"\bpermanent\b",
        plot_header,
        re.IGNORECASE
    ):

        return "Permanent"

    return "Monitoring Plot"


# ============================================================
# PARTNER
# ============================================================

def extract_partner(text):

    value = find_value(
        text,
        r"^\s*Partner\s*:?\s*(.+)$",

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    if value:

        return value

    return None


# ============================================================
# ALIVE
#
# Rules:
#
# 1. Alive: 32
#       -> Replanted Alive = 32
#
# 2. Total live trees: 32
#       -> Replanted Alive = 32
#
# 3. Alive: 6 old + 20 new
#       -> Old = 6
#       -> Replanted = 20
#
# 4. Total Alive:
#       -> if no explicit old/new, treat as Replanted Alive
#
# 5. Total Alive is ALWAYS:
#
#       Replanted Alive + Old Samplings Alive
# ============================================================

def extract_alive_values(text):
    """Extract alive trees into two independent groups.

    IMPORTANT DATA RULE:
    - Natural regeneration is NOT replanted alive and is NEVER added to total_alive.
    - Replanted/new planting alive is stored in ``re_planted_alive``.
    - Explicit old-sampling alive is stored in ``old_samplings_alive``.
    - ``total_alive`` is calculated only as:
          re_planted_alive + old_samplings_alive

    The key protection here is that an ``Alive:`` line inside a
    ``Natural regeneration`` section must not be interpreted as replanted alive.
    """
    old_alive = 0
    new_alive = 0
    old_found = False
    new_found = False

    lines = text.splitlines()
    in_natural_regen = False

    # A new normal field ends a natural-regeneration subsection.
    natural_start = re.compile(
        r'^\s*(?:Natural\s+regeneration|Natural\s+regeneration\s+trees?)\b',
        re.IGNORECASE,
    )
    section_end = re.compile(
        r'^\s*(?:Coordinates?|Spacing|Disturbances?|Cause\s+mortality|'
        r'Survival\s+rate|Zonation|Zone|Plot\b|Check\b|Monitoring\b|'
        r'Tree\s+species|Trees\s+species|Species\s+planted|Planting\s+date|'
        r'Date\s+planted|Session\s+ID|Planting\s+ID|ID\s*:|Area\b|'
        r'Total\s+planted|No\.?\s*planted|Observation|Recommendation)\b',
        re.IGNORECASE,
    )

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if natural_start.match(line):
            in_natural_regen = True
            continue

        if in_natural_regen:
            # Keep natural-regeneration Alive/Dead/etc. completely outside
            # the replanted/old-sampling counters.
            if section_end.match(line):
                in_natural_regen = False
            else:
                continue

        # Explicit old-sampling labels.
        m = re.match(
            r'^\s*(?:Old(?:\s+samplings?)?|Old\s+sampling)\s*:?[ \t]*(\d[\d,]*)',
            line,
            flags=re.IGNORECASE,
        )
        if m:
            old_alive += int(m.group(1).replace(',', ''))
            old_found = True
            continue

        # Explicit new/replanted labels.
        m = re.match(
            r'^\s*(?:New|Replanted)\s*:?[ \t]*(\d[\d,]*)',
            line,
            flags=re.IGNORECASE,
        )
        if m:
            new_alive += int(m.group(1).replace(',', ''))
            new_found = True
            continue

        # Alive lines outside Natural regeneration.
        m = re.match(
            r'^\s*Alive\s*:?[ \t]*(.+)$',
            line,
            flags=re.IGNORECASE,
        )
        if m:
            value_text = m.group(1)

            explicit_old = re.findall(
                r'(\d[\d,]*)\s*(?:old|older)',
                value_text,
                flags=re.IGNORECASE,
            )
            explicit_new = re.findall(
                r'(\d[\d,]*)\s*(?:new|replanted)',
                value_text,
                flags=re.IGNORECASE,
            )

            for value in explicit_old:
                old_alive += int(value.replace(',', ''))
                old_found = True

            for value in explicit_new:
                new_alive += int(value.replace(',', ''))
                new_found = True

            if not explicit_old and not explicit_new:
                # Plain Alive: N is replanted alive.
                before_equal = (
                    value_text.split('=', 1)[0]
                    if '=' in value_text
                    else value_text
                )
                numbers = re.findall(r'\d[\d,]*', before_equal)
                if numbers:
                    new_alive += sum(
                        int(v.replace(',', '')) for v in numbers
                    )
                    new_found = True

    # Total live trees / Total alive are replanted alive only when no
    # explicit alive components have already been found.
    if not old_found and not new_found:
        for pattern in [
            r'^\s*Total\s+live\s+trees\s*:?\s*(\d[\d,]*)',
            r'^\s*Total\s+alive\s*:?\s*(\d[\d,]*)',
        ]:
            for value in re.findall(
                pattern,
                text,
                flags=re.IGNORECASE | re.MULTILINE,
            ):
                new_alive = int(value.replace(',', ''))
                new_found = True
                break
            if new_found:
                break

    return (
        new_alive if new_found else None,
        old_alive if old_found else None,
    )


# ============================================================
# DEAD
# ============================================================

def extract_dead(text):

    values = []

    patterns = [

        r"^\s*Dead\s*:?\s*(.+)$",

        r"^\s*Mortality\s*:?\s*(.+)$"
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,

            flags=(
                re.IGNORECASE
                | re.MULTILINE
            )
        )

        for value in matches:

            numbers = re.findall(
                r"\d[\d,]*",
                value
            )

            values.extend(
                numbers
            )

    if not values:

        return None

    return sum(
        int(
            x.replace(",", "")
        )
        for x in values
    )


# ============================================================
# DORMANT
# ============================================================

def extract_dormant(text):

    matches = re.findall(
        r"^\s*Dormant"
        r"\s*:?\s*(.+)$",

        text,

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    values = []

    for value in matches:

        numbers = re.findall(
            r"\d[\d,]*",
            value
        )

        values.extend(
            numbers
        )

    if not values:

        return None

    return sum(
        int(
            x.replace(",", "")
        )
        for x in values
    )


# ============================================================
# NATURAL REGENERATION
# ============================================================

def extract_natural_regeneration(text):

    matches = re.findall(
        r"^\s*(?:Natural regeneration|Natural|Regeneration stage)"
        r"\s*:?\s*(.+)$",

        text,

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    if not matches:

        return None

    return " | ".join(
        clean_text(x)
        for x in matches
    )


# ============================================================
# SPLIT INTO PLANTING BLOCKS
#
# Supports:
#
# Planting ID: 21330
# Planted Session ID: 8670
# Session ID: 8670
# ID: 8670
# ============================================================

def split_into_planting_blocks(text):
    """Split a report into monitoring/planting groups.

    The important improvement is that a monitoring group does NOT have to
    contain the word 'planting'. Real reports use:
      Monitoring of 28th Feb 2025 (ID:9747)
      Monitoring of 25th March 2025 (ID:9960)
      Monitoring May 2026 planting
      Monitoring of 11th December 2024 planting
    """
    monitoring_line = (
        r"^\s*(?:\d+[\.\)]\s*)?"
        r"Monitoring\b.*$"
    )
    # Some reports place the plot header BEFORE the monitoring line, e.g.
    # "Plot 1:Temporary plot" followed by "Monitoring of 28th Feb 2025...".
    # In that structure, let parse_report use the plot-level fallback so the
    # plot header is never lost.
    first_monitoring = re.search(monitoring_line, text, flags=re.IGNORECASE | re.MULTILINE)
    first_plot = re.search(
        r"^\s*(?:Plot\s*:?\s*\d+|Temporary\s+Plot\s*:?\s*\d+)",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if first_plot and first_monitoring and first_plot.start() < first_monitoring.start():
        return []

    sections = re.split(
        rf"(?={monitoring_line})",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    blocks = []
    block_start = re.compile(
        r"^\s*(?:\d+[\.\)]\s*)?Monitoring\b",
        flags=re.IGNORECASE,
    )
    for section in sections:
        section = section.strip()
        if section and block_start.match(section):
            blocks.append(section)
    if blocks:
        return blocks

    # Fallback for reports without a Monitoring line.
    id_pattern = (
        r"(?=^\s*(?:"
        r"Planting\s+ID|Planted\s+Session\s+ID|Session\s+ID|ID"
        r")\s*:?\s*\d+)"
    )
    sections = re.split(id_pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    blocks = []
    for section in sections:
        section = section.strip()
        if re.match(
            r"^(?:Planting\s+ID|Planted\s+Session\s+ID|Session\s+ID|ID)\s*:?\s*\d+",
            section,
            flags=re.IGNORECASE,
        ):
            blocks.append(section)
    return blocks


# ============================================================
# SPLIT PLOTS
# ============================================================

def split_into_plots(text):
    """Split monitoring blocks into Plot records.

    Handles all of these:
      Plot 1
      Plot 1:
      Plot 1: Temporary plot
      Plot 1:Temporary plot
      Plot 1:Temporary
      Temporary Plot 1
      Plot 3:Temporary plot Monitoring ...
    """
    # Colon AFTER the plot number is explicitly allowed.
    header = (
        r"^\s*(?:"
        r"Plot\s*:??\s*\d+"
        r"|"
        r"Temporary\s+Plot\s*:??\s*\d+"
        r")"
        r"\s*:?[ \t].*$|^\s*(?:"
        r"Plot\s*:??\s*\d+"
        r"|"
        r"Temporary\s+Plot\s*:??\s*\d+"
        r")\s*:?[ \t]*$"
    )
    # Simpler, robust split anchor: Plot/Temporary Plot + number, then optional colon.
    split_anchor = (
        r"(?=^\s*(?:"
        r"Plot\s*:?\s*\d+"
        r"|"
        r"Temporary\s+Plot\s*:?\s*\d+"
        r")\s*:?)"
    )
    sections = re.split(split_anchor, text, flags=re.IGNORECASE | re.MULTILINE)
    plots = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        match = re.match(
            r"^(?:"
            r"Plot\s*:?\s*"
            r"|"
            r"Temporary\s+Plot\s*:?\s*"
            r")"
            r"(\d+)\s*:?[ \t]*(.*)$",
            section,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            continue
        plot_number = int(match.group(1))
        remainder = match.group(2)
        first_line = remainder.split("\n", 1)[0].strip()
        plots.append({
            "plot_number": plot_number,
            "plot_header": first_line or None,
            "plot_text": section,
        })
    return plots


# ============================================================
# BLOCK INFORMATION
# ============================================================

def extract_block_information(
    block_text
):

    species, material = (
        extract_species_and_material(
            block_text
        )
    )

    if material is None:

        material = (
            extract_planting_material(
                block_text
            )
        )

    return {

        "planting_id":
            extract_planting_id(
                block_text
            ),

        "planting_date":
            extract_planting_date(
                block_text
            ),

        "species":
            species,

        "planting_materials":
            material,

        "total_planted":
            extract_total_planted(
                block_text
            ),

        "area":
            extract_area(
                block_text
            ),

        "zonation":
            extract_zonation(
                block_text
            ),

        "spacing":
            extract_spacing(
                block_text
            ),

        "disturbance":
            extract_disturbance(
                block_text
            ),

        "check":
            extract_check_number(
                block_text
            )
    }


# ============================================================
# CREATE RECORD
# ============================================================

def create_record(
    plot_text,
    plot_number,
    plot_header,
    general_info,
    block_info,
    check_number
):

    row = {
        column: None
        for column in COLUMNS
    }

    # --------------------------------------------------------
    # GENERAL
    # --------------------------------------------------------

    row["County"] = (
        general_info["county"]
    )

    # Country is kept as a separate report-level field.
    row["Country"] = (
        general_info.get("country")
    )

    row["planting_site"] = (
        general_info["site"]
    )

    row["ecosystem type"] = (
        general_info["forest_type"]
    )

    row["monitoring_date"] = (
        general_info["monitoring_date"]
    )

    if row["monitoring_date"]:

        row["monitoring_month"] = (
            row["monitoring_date"]
            .strftime("%B")
        )

        row["monitoring_year"] = (
            row["monitoring_date"]
            .year
        )

    # --------------------------------------------------------
    # CHECK
    # --------------------------------------------------------

    row["Check"] = (
        check_number
    )

    # --------------------------------------------------------
    # PLOT
    # --------------------------------------------------------

    row["plot_number"] = (
        plot_number
    )

    row["type_of_plot"] = (
        extract_plot_type(
            plot_header
        )
    )

    row["partner"] = (
        extract_partner(
            plot_text
        )
    )

    # --------------------------------------------------------
    # PLANTING ID
    # --------------------------------------------------------

    planting_id = (
        block_info.get(
            "planting_id"
        )
    )

    if planting_id is None:

        planting_id = (
            extract_planting_id(
                plot_text
            )
        )

    row["planting_id"] = (
        planting_id
    )

    # --------------------------------------------------------
    # PLANTING DATE
    # --------------------------------------------------------

    planting_date = (
        block_info.get(
            "planting_date"
        )
    )

    if planting_date is None:

        planting_date = (
            extract_planting_date(
                plot_text
            )
        )

    row["planting_date"] = (
        planting_date
    )

    # --------------------------------------------------------
    # SPECIES
    # --------------------------------------------------------

    species, material = (
        extract_species_and_material(
            plot_text
        )
    )

    if species is None:

        species = (
            block_info.get(
                "species"
            )
        )

    if material is None:

        material = (
            extract_planting_material(
                plot_text
            )
        )

    if material is None:

        material = (
            block_info.get(
                "planting_materials"
            )
        )

    row["species_planted"] = (
        species
    )

    row["planting_materials"] = (
        material
    )

    # --------------------------------------------------------
    # TOTAL PLANTED
    # --------------------------------------------------------

    total_planted = (
        extract_total_planted(
            plot_text
        )
    )

    if total_planted is None:

        total_planted = (
            block_info.get(
                "total_planted"
            )
        )

    row["total_planted"] = (
        total_planted
    )

    # --------------------------------------------------------
    # AREA
    # --------------------------------------------------------

    area = extract_area(
        plot_text
    )

    if area is None:

        area = (
            block_info.get(
                "area"
            )
        )

    row["area_restored_ha"] = (
        area
    )

    # --------------------------------------------------------
    # ZONATION
    # --------------------------------------------------------

    zonation = extract_zonation(
        plot_text
    )

    if zonation is None:

        zonation = (
            block_info.get(
                "zonation"
            )
        )

    row["zonation"] = (
        zonation
    )

    # --------------------------------------------------------
    # SPACING
    # --------------------------------------------------------

    spacing = extract_spacing(
        plot_text
    )

    if spacing is None:

        spacing = (
            block_info.get(
                "spacing"
            )
        )

    row["spacing_m"] = (
        spacing
    )

    # --------------------------------------------------------
    # DISTURBANCE
    # --------------------------------------------------------

    disturbance = extract_disturbance(
        plot_text
    )

    if disturbance is None:

        disturbance = (
            block_info.get(
                "disturbance"
            )
        )

    row["Disturbance"] = (
        disturbance
    )

    # --------------------------------------------------------
    # COORDINATES
    # --------------------------------------------------------

    latitude, longitude = (
        parse_coordinates(
            plot_text
        )
    )

    row["latitude"] = (
        latitude
    )

    row["longitude"] = (
        longitude
    )

    # --------------------------------------------------------
    # ALIVE
    # --------------------------------------------------------

    (
        replanted_alive,
        old_alive
    ) = extract_alive_values(
        plot_text
    )

    row["re_planted_alive"] = (
        replanted_alive
    )

    row["old_samplings_alive"] = (
        old_alive
    )

    # --------------------------------------------------------
    # TOTAL ALIVE
    #
    # ALWAYS:
    #
    # Replanted Alive + Old Samplings Alive
    # --------------------------------------------------------

    components = []

    if replanted_alive is not None:

        components.append(
            replanted_alive
        )

    if old_alive is not None:

        components.append(
            old_alive
        )

    if components:

        row["total_alive"] = sum(
            components
        )

    # --------------------------------------------------------
    # DEAD
    # --------------------------------------------------------

    row["dead"] = (
        extract_dead(
            plot_text
        )
    )

    # --------------------------------------------------------
    # DORMANT
    # --------------------------------------------------------

    row["dormant"] = (
        extract_dormant(
            plot_text
        )
    )

    # --------------------------------------------------------
    # NATURAL REGENERATION
    # --------------------------------------------------------

    row["natural_regenation"] = (
        extract_natural_regeneration(
            plot_text
        )
    )

    # --------------------------------------------------------
    # TREE AGE
    # --------------------------------------------------------

    row["trees_age"] = (
        calculate_age_years(
            row["planting_date"],
            row["monitoring_date"]
        )
    )

    # --------------------------------------------------------
    # RECOMMENDATION
    # --------------------------------------------------------

    row["Recommendation"] = (
        general_info[
            "recommendation"
        ]
    )

    # --------------------------------------------------------
    # COMMENT
    # --------------------------------------------------------

    row["Comment"] = (
        general_info[
            "observation"
        ]
    )

    return row


# ============================================================
# PARSE ONE REPORT
# ============================================================

def parse_report(text):
    """Parse one complete WhatsApp report plot-by-plot.

    IMPORTANT DESIGN:
    We do NOT split the report first on ``Monitoring`` lines.  That approach
    fails when several planting sessions occur under one Check, because a
    later plot can inherit the first session's date/ID.

    Instead:
      1. Split the complete report into actual Plot sections.
      2. For each plot, use information inside that plot first.
      3. If planting-level fields are missing, inherit them from the nearest
         preceding planting/session context (ID/Session/Planting ID or
         Monitoring line), bounded by the current Check.

    This preserves older formats while correctly handling Kuchi-style reports
    where every plot may repeat its own Monitoring date and Session ID.
    """
    text = clean_text(text)
    general_info = extract_general_information(text)
    rows = []

    # --------------------------------------------------------
    # Locate all Check headers with positions.
    # --------------------------------------------------------
    check_matches = list(re.finditer(
        r"^\s*Check\s*(\d+).*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ))

    # --------------------------------------------------------
    # Locate ALL plot sections in the original report.
    # --------------------------------------------------------
    plot_anchor = re.compile(
        r"^\s*(?:Plot\s*:??\s*|Temporary\s+Plot\s*:??\s*)"
        r"(\d+)\s*:?[ \t]*(.*)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    plot_matches = list(plot_anchor.finditer(text))

    if not plot_matches:
        return pd.DataFrame(columns=COLUMNS)

    # --------------------------------------------------------
    # Planting/session markers.
    # These are used ONLY as context boundaries. Actual extraction is always
    # performed from the plot first.
    # --------------------------------------------------------
    session_marker = re.compile(
        r"^\s*(?:"
        r"Planting\s+ID|"
        r"Planted\s+Session\s+ID|"
        r"Session\s+ID|"
        r"ID"
        r")\s*:?[ \t]*\d+",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    monitoring_marker = re.compile(
        r"^\s*(?:\d+[\.)]\s*)?Monitoring\b.*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # Combine session and monitoring markers in source order.
    context_markers = []
    for m in session_marker.finditer(text):
        context_markers.append((m.start(), "session"))
    for m in monitoring_marker.finditer(text):
        context_markers.append((m.start(), "monitoring"))
    context_markers.sort(key=lambda x: x[0])

    def current_check_for_position(position):
        current = None
        for match in check_matches:
            if match.start() <= position:
                current = int(match.group(1))
            else:
                break
        return current

    def previous_check_start(position):
        starts = [m.start() for m in check_matches if m.start() <= position]
        return max(starts) if starts else 0

    def next_check_start(position):
        for match in check_matches:
            if match.start() > position:
                return match.start()
        return len(text)

    def context_for_plot(plot_start):
        """Return the best preceding planting/session context for a plot."""
        check_start = previous_check_start(plot_start)
        check_end = next_check_start(plot_start)

        markers = [
            (pos, kind)
            for pos, kind in context_markers
            if check_start <= pos <= plot_start and pos < check_end
        ]

        session_positions = [pos for pos, kind in markers if kind == "session"]
        monitoring_positions = [pos for pos, kind in markers if kind == "monitoring"]

        if session_positions:
            latest_session = max(session_positions)

            # If a Monitoring line occurs after the latest session marker,
            # that monitoring line belongs to the same planting session.
            # Example: Monitoring ... -> Session ID -> Plot.
            monitoring_after_session = [
                pos for pos in monitoring_positions
                if latest_session <= pos <= plot_start
            ]

            if monitoring_after_session:
                context_start = max(monitoring_after_session)
            else:
                # Example: Monitoring ... -> Session ID -> Plot, where the
                # monitoring date is before the ID. Keep the monitoring line
                # as well as the ID so planting_date is not lost.
                previous_monitoring = [
                    pos for pos in monitoring_positions
                    if pos < latest_session
                ]

                if previous_monitoring:
                    # Use the most recent monitoring line, but only if there
                    # was no newer session marker after it. This correctly
                    # pairs Rabai's Monitoring date with its Session ID.
                    context_start = max(previous_monitoring)
                else:
                    context_start = latest_session
        elif monitoring_positions:
            context_start = max(monitoring_positions)
        else:
            # If no explicit session marker precedes the plot, the Check-level
            # context can still contain Planting ID / Total planted fields.
            context_start = check_start

        return text[context_start:check_end]

    # --------------------------------------------------------
    # Build each plot independently.
    # --------------------------------------------------------
    for i, match in enumerate(plot_matches):
        plot_start = match.start()

        # A new Monitoring line can occur between two Plot headers when the
        # report starts a new planting session. Do not allow that next session
        # header to become part of the previous plot's text.
        next_plot_start = (
            plot_matches[i + 1].start()
            if i + 1 < len(plot_matches)
            else len(text)
        )

        next_monitoring_positions = [
            m.start()
            for m in monitoring_marker.finditer(text)
            if plot_start < m.start() < next_plot_start
        ]

        # A Monitoring line before the next Plot is a session boundary.
        # A Monitoring line belonging to the current plot would normally be
        # before its first observation and is therefore handled by this test:
        # if it appears after the plot header, it is still kept because the
        # current plot begins with its own header. Only the LAST monitoring
        # before the next plot is a boundary when there is no plot content
        # after it. In practice, reports such as Rabai/Chara put the next
        # session Monitoring after the preceding plot's observations.
        plot_end = next_plot_start
        if next_monitoring_positions:
            first_monitoring_after_plot = next_monitoring_positions[0]
            # Treat it as a boundary if it occurs after a coordinate/observation
            # field in the current plot. This avoids cutting Kuchi-style plots
            # that begin with Monitoring immediately after their Plot header.
            prefix = text[plot_start:first_monitoring_after_plot]
            if re.search(
                r'^\s*(?:Coordinates?|Alive|Dead|Dormant|Species|Tree\s+Species|Trees\s+species)',
                prefix,
                flags=re.IGNORECASE | re.MULTILINE,
            ):
                plot_end = first_monitoring_after_plot

        plot_text = text[plot_start:plot_end].strip()
        plot_number = int(match.group(1))
        plot_header = match.group(2).strip() or None

        current_check = current_check_for_position(plot_start)
        context_text = context_for_plot(plot_start)

        # Plot data always has priority. Context only fills missing fields.
        plot_info = extract_block_information(plot_text)
        context_info = extract_block_information(context_text)

        merged_info = dict(context_info)
        for key, value in plot_info.items():
            if value is not None:
                merged_info[key] = value

        # If the plot itself contains no planting ID/date but the session
        # context does, the context is inherited. This is what Chara-style
        # reports require. Kuchi-style repeated fields remain plot-specific.
        row = create_record(
            plot_text,
            plot_number,
            plot_header,
            general_info,
            merged_info,
            current_check,
        )
        rows.append(row)

    df = pd.DataFrame(rows, columns=COLUMNS)
    return clean_records(df)


# ============================================================
# CLEAN RECORDS
# ============================================================

def clean_records(df):

    if df.empty:

        return df

    # --------------------------------------------------------
    # Keep actual monitoring records
    # --------------------------------------------------------

    observation_columns = [

        "latitude",
        "longitude",
        "total_alive",
        "dead",
        "dormant"
    ]

    df["_has_observation"] = (
        df[
            observation_columns
        ]
        .notna()
        .any(axis=1)
    )

    df = df[
        df["_has_observation"]
    ].copy()

    df.drop(
        columns="_has_observation",
        inplace=True
    )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    numeric_columns = [

        "Check",
        "plot_number",
        "latitude",
        "longitude",
        "trees_age",
        "re_planted_alive",
        "old_samplings_alive",
        "total_alive",
        "dead",
        "dormant",
        "total_planted",
        "area_restored_ha",
        "spacing_m",
        "salinity",
        "dbh_mm",
        "height_cm",
        "no_of_leaves",
        "branches"
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # Tree age must be whole numbers
    if "trees_age" in df.columns:

        df["trees_age"] = (
            pd.to_numeric(
                df["trees_age"],
                errors="coerce"
            )
            .round()
            .astype("Int64")
        )

    # --------------------------------------------------------
    # Recalculate Total Alive
    #
    # This is deliberately done after extraction so the
    # final dataset cannot retain an incorrect Total Alive.
    # --------------------------------------------------------

    replanted = pd.to_numeric(
        df["re_planted_alive"],
        errors="coerce"
    ).fillna(0)

    old = pd.to_numeric(
        df["old_samplings_alive"],
        errors="coerce"
    ).fillna(0)

    has_alive = (
        df[
            [
                "re_planted_alive",
                "old_samplings_alive"
            ]
        ]
        .notna()
        .any(axis=1)
    )

    df.loc[
        has_alive,
        "total_alive"
    ] = (
        replanted
        + old
    )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    duplicate_columns = [

        "planting_site",

        "planting_id",

        "Check",

        "plot_number",

        "latitude",

        "longitude",

        "monitoring_date"
    ]

    existing_columns = [
        c
        for c in duplicate_columns
        if c in df.columns
    ]

    df = df.drop_duplicates(
        subset=existing_columns,
        keep="first"
    )

    df.reset_index(
        drop=True,
        inplace=True
    )

    return df


# ============================================================
# SESSION STATE
# ============================================================

if "all_reports" not in st.session_state:

    st.session_state.all_reports = pd.DataFrame(
        columns=COLUMNS
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "Instructions"
    )

    st.markdown(
        """
### How to use

1. Paste **one WhatsApp monitoring report**.
2. Click **Extract & Add Report**.
3. The report is added to the accumulated dataset.
4. Paste the next report.
5. Continue with all reports.
6. Use **Site Filter** to analyse individual sites.

### Extraction rules

- `Session ID` is treated as the planting ID.
- `Planting ID` is also supported.
- `Task ID` is ignored.
- `Check 1`, `Check 2`, `Check 3`, etc. are captured.
- `Check 3*` is also captured as Check 3.
- Each planting group is anchored on its own
  `Monitoring of <date> planting` line, so species,
  planting date, total planted and Session/Planting ID
  are kept together even when the ID line appears
  after them in the report.
- Planting information is inherited by plots.
- `Alive` alone = **Replanted Alive**.
- `Total live trees` alone = **Replanted Alive**.
- `Total alive` alone = **Replanted Alive**.
- `Total Alive = Replanted Alive + Old Samplings Alive`.
- Planting date is extracted from the planting/monitoring-of date.
- Report `Date` is the monitoring date.
- Tree age is completed years:
  - <12 months = 0
  - 12–23 months = 1
  - 24–35 months = 2
  - 36–47 months = 3
  - etc.
"""
    )

    st.divider()

    st.subheader(
        "Site Filter"
    )

    all_data = (
        st.session_state.all_reports
    )

    if not all_data.empty:

        available_sites = sorted(
            all_data[
                "planting_site"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_site = st.selectbox(
            "Select site",
            ["All Sites"] + available_sites
        )

    else:

        selected_site = "All Sites"

        st.info(
            "Extract reports to activate "
            "the site filter."
        )

    st.divider()

    if st.button(
        "Clear All Reports",
        use_container_width=True
    ):

        st.session_state.all_reports = (
            pd.DataFrame(
                columns=COLUMNS
            )
        )

        st.rerun()


# ============================================================
# TITLE
# ============================================================

st.title(
    "ELRF WhatsApp Monitoring Data Extractor"
)

st.write(
    "Paste monitoring reports individually. "
    "Each report is automatically added to the "
    "accumulated dataset."
)


# ============================================================
# INPUT
# ============================================================

st.subheader(
    "1. Paste WhatsApp Report"
)

whatsapp_text = st.text_area(
    "WhatsApp report",
    height=550,
    placeholder=(
        "Paste one complete WhatsApp monitoring "
        "report here..."
    ),
    key="report_input"
)


# ============================================================
# EXTRACT REPORT
# ============================================================

if st.button(
    "Extract & Add Report",
    type="primary",
    use_container_width=True
):

    if not whatsapp_text.strip():

        st.warning(
            "Please paste a WhatsApp report first."
        )

    else:

        try:

            with st.spinner(
                "Extracting monitoring plots..."
            ):

                new_df = parse_report(
                    whatsapp_text
                )

            if new_df.empty:

                st.error(
                    "No monitoring plots were detected."
                )

                st.info(
                    "The parser looks for formats such as "
                    "`Plot 1`, `Plot 1:`, `Plot 1: Temporary plot`, "
                    "`Temporary Plot 1`, etc."
                )

            else:

                # Add report
                st.session_state.all_reports = (
                    pd.concat(
                        [
                            st.session_state.all_reports,
                            new_df
                        ],
                        ignore_index=True
                    )
                )

                # Clean accumulated dataset
                st.session_state.all_reports = (
                    clean_records(
                        st.session_state.all_reports
                    )
                )

                st.success(
                    f"Successfully extracted "
                    f"{len(new_df)} monitoring plot(s). "
                    f"Added to accumulated dataset."
                )

                # Show immediate preview
                st.dataframe(
                    new_df,
                    use_container_width=True
                )

        except Exception as e:

            st.error(
                f"Extraction failed: {e}"
            )

            st.exception(e)


# ============================================================
# ACCUMULATED DATA
# ============================================================

all_df = (
    st.session_state.all_reports
)

if all_df.empty:

    st.info(
        "No reports have been added yet."
    )

    st.stop()


# ============================================================
# FILTER DATA
# ============================================================

if selected_site == "All Sites":

    filtered_df = (
        all_df.copy()
    )

else:

    filtered_df = (
        all_df[
            all_df["planting_site"]
            .astype(str)
            .eq(selected_site)
        ]
        .copy()
    )


# ============================================================
# DASHBOARD KPIs
# ============================================================

st.subheader(
    "Monitoring Summary"
)

k1, k2, k3, k4 = st.columns(4)


k1.metric(
    "Monitoring Plots",
    len(filtered_df)
)


k2.metric(
    "Sites",
    filtered_df[
        "planting_site"
    ]
    .nunique()
)


planting_sessions = (
    filtered_df[
        "planting_id"
    ]
    .dropna()
    .astype(str)
    .nunique()
)

k3.metric(
    "Planting Sessions",
    planting_sessions
)


checks = (
    filtered_df[
        "Check"
    ]
    .dropna()
    .nunique()
)

k4.metric(
    "Checks",
    checks
)


# ============================================================
# SECOND KPI ROW
# ============================================================

k7, k8, k9, k10 = st.columns(4)


total_alive = (
    pd.to_numeric(
        filtered_df[
            "total_alive"
        ],
        errors="coerce"
    )
    .sum()
)

k7.metric(
    "Total Alive",
    f"{total_alive:,.0f}"
)


total_dead = (
    pd.to_numeric(
        filtered_df[
            "dead"
        ],
        errors="coerce"
    )
    .sum()
)

k8.metric(
    "Dead",
    f"{total_dead:,.0f}"
)


total_dormant = (
    pd.to_numeric(
        filtered_df[
            "dormant"
        ],
        errors="coerce"
    )
    .sum()
)

k9.metric(
    "Dormant",
    f"{total_dormant:,.0f}"
)


# ------------------------------------------------------------
# Area
#
# Count area once per planting session rather than once
# per monitoring plot.
# ------------------------------------------------------------

area_columns = [
    "planting_site",
    "planting_id",
    "area_restored_ha"
]

area_data = (
    filtered_df[
        area_columns
    ]
    .drop_duplicates()
)

area_total = (
    pd.to_numeric(
        area_data[
            "area_restored_ha"
        ],
        errors="coerce"
    )
    .sum()
)

k10.metric(
    "Area (ha)",
    f"{area_total:,.3f}"
)


# ============================================================
# SELECTED SITE INFORMATION
# ============================================================

if selected_site != "All Sites":

    st.subheader(
        f"Site: {selected_site}"
    )

    site_info = filtered_df

    info1, info2, info3, info4 = st.columns(4)

    monitoring_dates = (
        site_info[
            "monitoring_date"
        ]
        .dropna()
    )

    if not monitoring_dates.empty:

        latest_monitoring = (
            monitoring_dates.max()
        )

        earliest_monitoring = (
            monitoring_dates.min()
        )

        info1.metric(
            "First Monitoring",
            earliest_monitoring.strftime(
                "%d %b %Y"
            )
        )

        info2.metric(
            "Latest Monitoring",
            latest_monitoring.strftime(
                "%d %b %Y"
            )
        )

    else:

        info1.metric(
            "First Monitoring",
            "N/A"
        )

        info2.metric(
            "Latest Monitoring",
            "N/A"
        )

    info3.metric(
        "Planting Sessions",
        site_info[
            "planting_id"
        ]
        .dropna()
        .nunique()
    )

    info4.metric(
        "Checks",
        site_info[
            "Check"
        ]
        .dropna()
        .nunique()
    )


# ============================================================
# ACCUMULATED TABLE
# ============================================================

st.subheader(
    "Accumulated Monitoring Data"
)

st.caption(
    f"Showing {len(filtered_df):,} monitoring records."
)

st.dataframe(
    filtered_df,
    use_container_width=True,
    height=650
)


# ============================================================
# PLANTING SESSION SUMMARY
# ============================================================

st.subheader(
    "Planting Session Summary"
)

summary = pd.DataFrame()

if not filtered_df.empty:

    summary = (
        filtered_df
        .groupby(
            [
                "planting_site",
                "Check",
                "planting_id"
            ],
            dropna=False
        )
        .agg(

            monitoring_records=(
                "plot_number",
                "count"
            ),

            plots=(
                "plot_number",
                "nunique"
            ),

            monitoring_date=(
                "monitoring_date",
                "first"
            ),

            planting_date=(
                "planting_date",
                "first"
            ),

            tree_age=(
                "trees_age",
                "first"
            ),

            species=(
                "species_planted",
                "first"
            ),

            planting_material=(
                "planting_materials",
                "first"
            ),

            total_planted=(
                "total_planted",
                "first"
            ),

            area_ha=(
                "area_restored_ha",
                "first"
            ),

            total_alive=(
                "total_alive",
                "sum"
            ),

            dead=(
                "dead",
                "sum"
            ),

            dormant=(
                "dormant",
                "sum"
            )
        )
        .reset_index()
    )

    st.dataframe(
        summary,
        use_container_width=True
    )


# ============================================================
# CHECK SUMMARY
# ============================================================

st.subheader(
    "Check Summary"
)

check_summary = pd.DataFrame()

if not filtered_df.empty:

    check_summary = (
        filtered_df
        .groupby(
            [
                "planting_site",
                "Check"
            ],
            dropna=False
        )
        .agg(

            monitoring_plots=(
                "plot_number",
                "count"
            ),

            planting_sessions=(
                "planting_id",
                "nunique"
            ),

            total_alive=(
                "total_alive",
                "sum"
            ),

            dead=(
                "dead",
                "sum"
            ),

            dormant=(
                "dormant",
                "sum"
            )
        )
        .reset_index()
    )

    st.dataframe(
        check_summary,
        use_container_width=True
    )


# ============================================================
# DATA QUALITY
# ============================================================

st.subheader(
    "Data Quality Check"
)

quality_fields = [

    "planting_site",

    "Check",

    "planting_id",

    "planting_date",

    "monitoring_date",

    "latitude",

    "longitude",

    "total_planted",

    "total_alive",

    "dead",

    "dormant",

    "species_planted",

    "planting_materials",

    "trees_age",

    "spacing_m",

    "zonation",

    "Disturbance"
]

quality_rows = []

for field in quality_fields:

    complete = (
        filtered_df[
            field
        ]
        .notna()
        .sum()
    )

    missing = (
        len(filtered_df)
        - complete
    )

    quality_rows.append({

        "Field":
            field,

        "Complete":
            complete,

        "Missing":
            missing,

        "Total":
            len(filtered_df),

        "Completeness %":
            round(
                complete
                / len(filtered_df)
                * 100,
                1
            )
            if len(filtered_df) > 0
            else 0
    })


quality_df = pd.DataFrame(
    quality_rows
)

st.dataframe(
    quality_df,
    use_container_width=True
)


# ============================================================
# PLOT LEVEL CHECK
# ============================================================

st.subheader(
    "Plot-Level Check"
)

plot_check_columns = [

    "planting_site",

    "Check",

    "planting_id",

    "plot_number",

    "monitoring_date",

    "planting_date",

    "trees_age",

    "species_planted",

    "planting_materials",

    "total_planted",

    "area_restored_ha",

    "latitude",

    "longitude",

    "re_planted_alive",

    "old_samplings_alive",

    "total_alive",

    "dead",

    "dormant",

    "natural_regenation",

    "spacing_m",

    "zonation",

    "Disturbance"
]

st.dataframe(
    filtered_df[
        plot_check_columns
    ],
    use_container_width=True,
    height=500
)


# ============================================================
# EXPORT
# ============================================================

st.subheader(
    "Export Data"
)

output = BytesIO()

with pd.ExcelWriter(
    output,
    engine="openpyxl"
) as writer:

    # All reports
    all_df.to_excel(
        writer,
        index=False,
        sheet_name="All Monitoring Data"
    )

    # Selected site
    filtered_df.to_excel(
        writer,
        index=False,
        sheet_name="Selected Site"
    )

    # Planting summary
    if not summary.empty:

        summary.to_excel(
            writer,
            index=False,
            sheet_name="Planting Summary"
        )

    # Check summary
    if not check_summary.empty:

        check_summary.to_excel(
            writer,
            index=False,
            sheet_name="Check Summary"
        )

    # Data quality
    quality_df.to_excel(
        writer,
        index=False,
        sheet_name="Data Quality"
    )

output.seek(0)

st.download_button(

    label="Download Excel",

    data=output,

    file_name=(
        "ELRF_WhatsApp_Monitoring_Data.xlsx"
    ),

    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),

    use_container_width=True
)


# ============================================================
# CURRENT DATASET STATUS
# ============================================================

st.divider()

st.caption(
    f"Accumulated dataset: "
    f"{len(all_df):,} monitoring records "
    f"from "
    f"{all_df['planting_site'].nunique()} site(s)."
)