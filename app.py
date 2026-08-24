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

    site = find_value(
        text,
        r"^\s*Site\s*:?\s*(.+)$",
        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    county = find_value(
        text,
        r"^\s*County\s*:?\s*(.+)$",
        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    forest_type = find_value(
        text,
        r"^\s*Forest\s+type\s*:?\s*(.+)$",
        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    # --------------------------------------------------------
    # Report / monitoring date
    #
    # Example:
    # Date: 17/08/2026
    # --------------------------------------------------------

    monitoring_date_text = find_value(
        text,
        r"^\s*Date\s*:?\s*"
        r"(\d{1,2}"
        r"(?:st|nd|rd|th)?"
        r"[\/\-]\d{1,2}"
        r"[\/\-]\d{2,4})",

        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    if not monitoring_date_text:

        monitoring_date_text = find_value(
            text,
            r"^\s*Date\s*:?\s*"
            r"(\d{1,2}"
            r"(?:st|nd|rd|th)?"
            r"\s+[A-Za-z]+"
            r"(?:,\s*|\s+)"
            r"\d{4})",

            flags=(
                re.IGNORECASE
                | re.MULTILINE
            )
        )

    monitoring_date = parse_date(
        monitoring_date_text
    )

    observation = find_value(
        text,
        r"^\s*(?:General\s+Observation|Observation)"
        r"\s*:?\s*(.+)$",
        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    recommendation = find_value(
        text,
        r"^\s*Recommendation"
        r"\s*:?\s*(.+)$",
        flags=(
            re.IGNORECASE
            | re.MULTILINE
        )
    )

    return {

        "site":
            site,

        "county":
            county,

        "forest_type":
            forest_type,

        "monitoring_date":
            monitoring_date,

        "observation":
            observation,

        "recommendation":
            recommendation
    }


# ============================================================
# SESSION / CHECK-SPECIFIC OBSERVATIONS
# ============================================================

def _ordinal_to_int(value):
    mapping = {
        "1": 1, "1st": 1,
        "2": 2, "2nd": 2,
        "3": 3, "3rd": 3,
        "4": 4, "4th": 4,
        "5": 5, "5th": 5,
        "6": 6, "6th": 6,
        "7": 7, "7th": 7,
        "8": 8, "8th": 8,
        "9": 9, "9th": 9,
        "10": 10, "10th": 10,
    }
    return mapping.get(str(value).lower())


def extract_session_observations(text):
    """Extract observations explicitly associated with a session/check.

    Supports both common styles:
      - ``Session 1's polygon ...``
      - ``... in the 1st session. ... in the 2nd session.``

    Only sentences that explicitly contain a session number are assigned.
    Unlabelled text is left to the existing report-level Comment behavior.
    """
    result = {}
    if not text:
        return result

    block_match = re.search(
        r"^\s*(?:General\s+Observation|Observation)\s*:?[ \t]*\n?(.*?)(?=^\s*Recommendation\b|\Z)",
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if not block_match:
        return result

    block = clean_text(block_match.group(1))
    if not block:
        return result

    # Split on sentence boundaries, including WhatsApp text where the next
    # sentence starts immediately after the period (``session.Growth``).
    sentences = re.split(r"(?<=[.!?])\s*", block)
    for sentence in sentences:
        sentence = clean_text(sentence)
        if not sentence:
            continue

        match = re.search(
            r"\bSession\s*(\d+)\b|\b(\d+)(?:st|nd|rd|th)\s+session\b",
            sentence,
            flags=re.IGNORECASE,
        )
        if not match:
            continue

        number = int(match.group(1) or match.group(2))
        result[number] = sentence

    return result


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
    """Extract the planting date from the SMALLEST available context.

    Priority:
      1. Explicit Planting date / Date planted inside the supplied text.
      2. Monitoring <date> planting inside the supplied text.
      3. Monitoring of <date> planting inside the supplied text.
      4. Monitoring <month> <year> planting.

    This function intentionally uses the first matching planting-date
    statement in the supplied plot/context only.  The parser never passes
    the entire report here when processing a Kuchi plot.
    """
    if not text:
        return None

    patterns = [
        r"^\s*(?:[-•*]\s*)?Planting\s+date\s*:?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        r"^\s*(?:[-•*]\s*)?Planting\s+date\s*:?\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:,\s*|\s+)\d{4})",
        r"^\s*(?:[-•*]\s*)?Date\s+planted\s*:?\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:,\s*|\s+)\d{4})",
        r"^\s*(?:[-•*]\s*)?Date\s+planted\s*:?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            parsed = parse_date(m.group(1))
            if parsed:
                return parsed

    monitoring_patterns = [
        r"^\s*(?:\d+[.)]\s*)?Monitoring\s+(?:of\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:,\s*|\s+)\d{4})(?:\s+planting)?",
        r"^\s*(?:\d+[.)]\s*)?Monitoring\s+(?:of\s+)?(\d{1,2}/\d{1,2}/\d{2,4})(?:\s+planting)?",
    ]
    for pattern in monitoring_patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            parsed = parse_date(m.group(1))
            if parsed:
                return parsed

    m = re.search(
        r"^\s*(?:\d+[.)]\s*)?Monitoring\s+([A-Za-z]+)\s+(\d{4})\s+planting",
        text, flags=re.IGNORECASE | re.MULTILINE
    )
    if m:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(f"1 {m.group(1)} {m.group(2)}", fmt).date()
            except ValueError:
                pass

    # Fallback: a standalone planting date written on its own line with
    # no explicit "Planting date" / "Date planted" / "Monitoring" label.
    # Some reports simply list the date (e.g. "03/06/2025") right under
    # the plot's ID / P.A lines:
    #
    #   Plot 1:
    #   Monitoring 2025 planting.
    #   ID:11462
    #   P.A :0.2576ha
    #   03/06/2025
    #   Trees species planted :C.tagal
    #
    # This is safe to use as the planting date here because plot_text is
    # always a single plot's own section (see split_into_plots) and never
    # includes the report header where the overall monitoring "Date:"
    # line lives, so it cannot be confused with the report/monitoring date.
    m = re.search(
        r"^\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*$",
        text, flags=re.MULTILINE
    )
    if m:
        parsed = parse_date(m.group(1))
        if parsed:
            return parsed

    m = re.search(
        r"^\s*(\d{1,2}-\d{1,2}-\d{2,4})\s*$",
        text, flags=re.MULTILINE
    )
    if m:
        parsed = parse_date(m.group(1))
        if parsed:
            return parsed

    return None


# ============================================================
# PLANTING ID / SESSION ID
# ============================================================

def extract_planting_id(text):
    """Extract planting/session ID from the supplied plot/context only."""
    if not text:
        return None

    patterns = [
        r"^\s*Planting\s+ID\s*:?\s*(\d+)",
        r"^\s*Planted\s+Session\s+ID\s*:?\s*(\d+)",
        r"^\s*Session\s+ID\s*:?\s*(\d+)",
        r"^\s*ID\s*:?\s*(\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1)

    # Kadzuhoni-style: Monitoring ... (ID:9747)
    m = re.search(
        r"^\s*Monitoring\b[^\n]*?\(\s*ID\s*:\s*(\d+)\s*\)",
        text, flags=re.IGNORECASE | re.MULTILINE
    )
    if m:
        return m.group(1)
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
    """Extract a coordinate pair without silently truncating malformed values.

    Important safety rule:
    If a line such as ``Coordinates:-2.68,40.40.193`` contains a malformed
    longitude/latitude, the function returns (None, None) instead of accepting
    the valid-looking prefix ``40.40``. This keeps bad GPS data visible for
    manual correction.
    """
    if not text:
        return None, None

    # First handle an explicit Coordinates line. Validate the entire pair so
    # malformed decimal values are not silently truncated by a regex prefix.
    coordinate_line = re.search(
        r"^\s*Coordinates?\s*:?\s*(.+?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if coordinate_line:
        raw = coordinate_line.group(1).strip()
        parts = re.split(r"\s*,\s*", raw)
        if len(parts) >= 2:
            lat_raw = parts[0].strip()
            lon_raw = parts[1].strip()
            number_pattern = r"^-?\d+(?:\.\d+)?$"
            if re.fullmatch(number_pattern, lat_raw) and re.fullmatch(number_pattern, lon_raw):
                return float(lat_raw), float(lon_raw)
            # A malformed explicit coordinate pair must not fall through to
            # the generic prefix-matching patterns below.
            return None, None

    # latitude / longitude format
    lat_match = re.search(
        r"\blat(?:itude)?\s*:?\s*(-?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    lon_match = re.search(
        r"\blong(?:itude)?\s*:?\s*(-?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )

    if lat_match and lon_match:
        return float(lat_match.group(1)), float(lon_match.group(1))

    # Fallback for separate bare Coordinates + Long/Longitude formats.
    if lon_match and not lat_match:
        bare_lat_match = re.search(
            r"^\s*Coordinates?\s*:?\s*(-?\d+\.\d+)\s*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if bare_lat_match:
            return float(bare_lat_match.group(1)), float(lon_match.group(1))

    if lat_match and not lon_match:
        bare_lon_match = re.search(
            r"^\s*Coordinates?\s*:?\s*(-?\d+\.\d+)\s*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if bare_lon_match and bare_lon_match.group(1) != lat_match.group(1):
            return float(lat_match.group(1)), float(bare_lon_match.group(1))

    # Bare coordinate line without the Coordinates label.
    bare_pair = re.search(
        r"^\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*$",
        text,
        flags=re.MULTILINE,
    )
    if bare_pair:
        return float(bare_pair.group(1)), float(bare_pair.group(2))

    return None, None


# ============================================================
# PLOT TYPE
# ============================================================

def extract_plot_type(plot_header, context_text=None, report_text=None):
    """Determine plot type using plot-level text first, then session context.

    Existing behavior is preserved for explicit headers such as
    ``Plot 2: Temporary Plot``. The new context fallback handles reports that
    declare ``2.5m radius Temporary Plots establishment`` once for a Check or
    session and then use plain ``Plot 1``, ``Plot 2`` headers.
    """
    header = plot_header or ""
    if re.search(r"\btemporary\b", header, re.IGNORECASE):
        return "Temporary"

    context = context_text or ""
    if re.search(r"\btemporary\s+plots?\b", context, re.IGNORECASE):
        return "Temporary"

    # Report-level establishment statement, normally before the first Check.
    # Only use it when it explicitly says Temporary Plot(s), so unrelated
    # uses of the word temporary are not promoted to a plot type.
    if report_text and re.search(
        r"(?:radius\s+)?temporary\s+plots?\s+establishment",
        report_text,
        re.IGNORECASE,
    ):
        return "Temporary"

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
    """Extract replanted/old alive counts without counting natural regeneration.

    Natural regeneration is a separate ecological category. Therefore an
    ``Alive`` value occurring inside a ``Natural regeneration`` section is
    NEVER added to replanted_alive, old_samplings_alive, or total_alive.
    """
    old_alive = 0
    new_alive = 0
    old_found = False
    new_found = False

    lines = text.splitlines()
    in_natural_regen = False

    natural_start = re.compile(
        r"^\s*(?:Natural\s+regeneration|Natural\s+regeneration\s*:|Natural)\b",
        re.IGNORECASE
    )
    natural_end = re.compile(
        r"^\s*(?:Coordinates?|Spacing|Disturbances?|Cause\s+mortality|Survival\s+rate|Zonation|Zone|Plot\b|Check\b|Recommendation|Observation|$)",
        re.IGNORECASE
    )

    for raw_line in lines:
        line = raw_line.strip()

        if natural_start.match(line):
            in_natural_regen = True
            continue

        if in_natural_regen and natural_end.match(line):
            in_natural_regen = False

        if in_natural_regen:
            continue

        match = re.match(r"^Old\s*:?\s*([\d,]+)", line, re.IGNORECASE)
        if match:
            old_alive += int(match.group(1).replace(",", ""))
            old_found = True
            continue

        match = re.match(r"^New\s*:?\s*([\d,]+)", line, re.IGNORECASE)
        if match:
            new_alive += int(match.group(1).replace(",", ""))
            new_found = True
            continue

        match = re.match(r"^Alive\s*:?\s*(.+)$", line, re.IGNORECASE)
        if match:
            value_text = match.group(1)

            explicit_old = re.findall(
                r"(\d[\d,]*)\s*(?:old|older)",
                value_text,
                re.IGNORECASE
            )
            explicit_new = re.findall(
                r"(\d[\d,]*)\s*(?:new|replanted)",
                value_text,
                re.IGNORECASE
            )

            for value in explicit_old:
                old_alive += int(value.replace(",", ""))
                old_found = True

            for value in explicit_new:
                new_alive += int(value.replace(",", ""))
                new_found = True

            if not explicit_old and not explicit_new:
                # Plain Alive: 0 is a legitimate observation.
                numbers = re.findall(r"\d[\d,]*", value_text)
                if numbers:
                    new_alive += sum(
                        int(v.replace(",", "")) for v in numbers
                    )
                    new_found = True

    # Total live trees / Total alive are only fallbacks when no explicit
    # Alive/Old/New values were found.
    if not old_found and not new_found:
        for pattern in [
            r"^\s*Total\s+live\s+trees\s*:?\s*([\d,]+)",
            r"^\s*Total\s+alive\s*:?\s*([\d,]+)",
        ]:
            for value in re.findall(
                pattern,
                text,
                flags=re.IGNORECASE | re.MULTILINE
            ):
                new_alive = int(value.replace(",", ""))
                new_found = True
                break
            if new_found:
                break

    return (
        new_alive if new_found else None,
        old_alive if old_found else None
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
            r"\d[\d,]*(?:\.\d+)?",
            value
        )

        values.extend(
            numbers
        )

    if not values:

        return None

    return sum(
        float(x.replace(",", ""))
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
    """Legacy helper retained for compatibility.

    The main parser now works plot-by-plot because WhatsApp reports can put
    the Monitoring/Session ID line either before or after the Plot header.
    """
    return []


# ============================================================
# SPLIT PLOTS - ROBUST PLOT-BY-PLOT PARSER
# ============================================================

def split_into_plots(text):
    """Split a report into plot sections without crossing Check/Session boundaries.

    The previous parser ended a plot only at the next Plot header. In reports
    where the next session's metadata appears between Plot 3 and the next Plot
    1, that metadata became part of Plot 3. We now stop a plot at the earliest
    of the next Plot header, next Check header, or next Session header.
    """
    anchor = re.compile(
        r"^\s*(?:Plot\s*:??\s*|Temporary\s+Plot\s*:??\s*)(\d+)\s*:?[ \t]*(.*)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    boundary = re.compile(
        r"^\s*(?:Check\s*\d+\b|Session\s*\d+\b|Session\s*:\s*\d+\b).*?$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    matches = list(anchor.finditer(text))
    boundaries = list(boundary.finditer(text))
    plots = []

    for i, match in enumerate(matches):
        start_pos = match.start()
        next_plot_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        next_boundary_pos = len(text)
        for b in boundaries:
            if b.start() > start_pos and b.start() < next_boundary_pos:
                next_boundary_pos = b.start()

        end_pos = min(next_plot_pos, next_boundary_pos)
        section = text[start_pos:end_pos].strip()
        header = match.group(2).strip() or None
        plots.append({
            "plot_number": int(match.group(1)),
            "plot_header": header,
            "plot_text": section,
            "start": start_pos,
            "end": end_pos,
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
    check_number,
    context_text="",
    session_number=None,
    report_text="",
    session_observations=None
):
    """Create one monitoring-plot record.

    IMPORTANT extraction priority:
    1. Plot-level text (the current plot)
    2. Surrounding Check/context information

    This prevents Kuchi-style reports from inheriting the previous
    plot's planting date/session ID when several planting sessions
    occur in the same Check.
    """

    row = {column: None for column in COLUMNS}

    row["County"] = general_info["county"]
    row["planting_site"] = general_info["site"]
    row["ecosystem type"] = general_info["forest_type"]
    row["monitoring_date"] = general_info["monitoring_date"]

    if row["monitoring_date"]:
        row["monitoring_month"] = row["monitoring_date"].strftime("%B")
        row["monitoring_year"] = row["monitoring_date"].year

    # The Kuchi structure puts CHECK 1 / CHECK 4 on the Plot header.
    # Prefer that plot-level value when present; otherwise use the
    # surrounding Check context.
    plot_check = extract_check_number(plot_header or "")
    row["Check"] = plot_check if plot_check is not None else check_number
    row["plot_number"] = plot_number
    row["type_of_plot"] = extract_plot_type(
        plot_header,
        context_text=context_text,
        report_text=report_text
    )
    row["partner"] = extract_partner(plot_text) or extract_partner(block_info.get("context_text", ""))

    # --------------------------------------------------------
    # PLOT-LEVEL FIRST, CONTEXT SECOND
    # --------------------------------------------------------
    def plot_first(extractor, key):
        value = extractor(plot_text)
        if value is None or value == "":
            value = block_info.get(key)
        return value

    row["planting_id"] = plot_first(extract_planting_id, "planting_id")
    row["planting_date"] = plot_first(extract_planting_date, "planting_date")

    species, material = extract_species_and_material(plot_text)
    if species is None:
        species = block_info.get("species")
    if material is None:
        material = extract_planting_material(plot_text)
    if material is None:
        material = block_info.get("planting_materials")

    row["species_planted"] = species
    row["planting_materials"] = material

    row["total_planted"] = plot_first(extract_total_planted, "total_planted")
    row["area_restored_ha"] = plot_first(extract_area, "area")
    row["zonation"] = plot_first(extract_zonation, "zonation")
    row["spacing_m"] = plot_first(extract_spacing, "spacing")
    row["Disturbance"] = plot_first(extract_disturbance, "disturbance")

    latitude, longitude = parse_coordinates(plot_text)
    row["latitude"] = latitude
    row["longitude"] = longitude

    replanted_alive, old_alive = extract_alive_values(plot_text)
    row["re_planted_alive"] = replanted_alive
    row["old_samplings_alive"] = old_alive

    # Natural regeneration is independent. It NEVER contributes to total_alive.
    components = []
    if replanted_alive is not None:
        components.append(replanted_alive)
    if old_alive is not None:
        components.append(old_alive)
    if components:
        row["total_alive"] = sum(components)

    row["dead"] = extract_dead(plot_text)
    row["dormant"] = extract_dormant(plot_text)
    row["natural_regenation"] = extract_natural_regeneration(plot_text)
    row["trees_age"] = calculate_age_years(
        row["planting_date"],
        row["monitoring_date"]
    )
    row["Recommendation"] = general_info["recommendation"]

    # Prefer a session/check-specific observation when the report explicitly
    # labels it (e.g. "1st session ..." / "Session 2 ..."). Otherwise keep
    # the existing report-level observation behavior.
    observation_key = session_number if session_number in (session_observations or {}) else check_number
    if session_observations and observation_key in session_observations:
        row["Comment"] = session_observations[observation_key]
    else:
        row["Comment"] = general_info["observation"]

    return row


# ============================================================
# PARSE ONE REPORT
# ============================================================

def _find_previous_context(text, position):
    """Return only the metadata immediately preceding this plot.

    Used for old reports where planting metadata is before Plot 1.
    The context begins at the latest Monitoring line, or latest Check line.
    """
    before = text[:position]
    monitoring_matches = list(re.finditer(
        r"^\s*(?:\d+[.)]\s*)?Monitoring\b.*$",
        before, flags=re.IGNORECASE | re.MULTILINE
    ))
    if monitoring_matches:
        return before[monitoring_matches[-1].start():]

    check_matches = list(re.finditer(
        r"^\s*Check\s*\d+\b.*$",
        before, flags=re.IGNORECASE | re.MULTILINE
    ))
    return before[check_matches[-1].start():] if check_matches else ""


def _extract_check_from_anywhere(text):
    match = re.search(r"\bCheck\s*(\d+)\b", text or "", flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return extract_check_number(text)


def _merge_block_info(primary, fallback):
    """Fill only genuinely missing metadata; never overwrite plot-local data."""
    merged = dict(primary or {})
    for key in [
        "planting_id", "planting_date", "species", "planting_materials",
        "total_planted", "area", "zonation", "spacing", "disturbance"
    ]:
        if merged.get(key) is None and fallback:
            merged[key] = fallback.get(key)
    return merged


def _metadata_for_plot(text, plot):
    """Resolve planting metadata for one plot without cross-contamination.

    Kuchi rule:
      Plot 1-4 -> 11 Feb / 18194
      Plot 5   -> 16 Feb / 18272
      Plot 6-8 -> 18 Feb / 18354
      Plot 9-10-> 31 Jul 2023 / 848

    The plot's own section always wins. Previous context is used only when a
    field is absent, which preserves Kadzuhoni/Chara and earlier formats.
    """
    plot_text = plot["plot_text"]
    local = extract_block_information(plot_text)

    # If the plot itself has its own Monitoring line, do NOT use a preceding
    # monitoring block for any field already extracted locally.
    previous = _find_previous_context(text, plot["start"])
    if previous:
        fallback = extract_block_information(previous)
        local = _merge_block_info(local, fallback)

    return local

def parse_report(text):
    """Parse a WhatsApp report into one row per monitoring plot.

    Maintains the existing plot-first extraction strategy while making the
    context explicitly Check/Session aware. Plot-local information always wins;
    context only fills missing fields.
    """
    text = clean_text(text)
    general_info = extract_general_information(text)
    session_observations = extract_session_observations(text)
    rows = []

    check_matches = list(re.finditer(
        r"^\s*Check\s*(\d+).*?$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ))
    session_matches = list(re.finditer(
        r"^\s*Session\s*(\d+)\b.*?$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ))

    plots = split_into_plots(text)
    if not plots:
        return pd.DataFrame(columns=COLUMNS)

    def context_for_position(position):
        """Return metadata before the plot within its current Check."""
        context_start = 0
        current_check = None
        for match in check_matches:
            if match.start() <= position:
                context_start = match.start()
                current_check = int(match.group(1))
            else:
                break

        current_session = None
        for match in session_matches:
            if match.start() <= position:
                current_session = int(match.group(1))
            else:
                break

        return text[context_start:position], current_check, current_session

    for plot in plots:
        plot_text = plot["plot_text"]
        plot_position = plot["start"]
        context_text, current_check, current_session = context_for_position(plot_position)

        context_info = extract_block_information(context_text)
        context_info["context_text"] = context_text

        row = create_record(
            plot_text=plot_text,
            plot_number=plot["plot_number"],
            plot_header=plot["plot_header"],
            general_info=general_info,
            block_info=context_info,
            check_number=current_check,
            session_number=current_session,
            context_text=context_text,
            report_text=text,
            session_observations=session_observations,
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
- Session/Check-level "Temporary Plots establishment" is inherited by plots that do not explicitly state their plot type.
- Plot sections stop at the next Check/Session boundary to prevent metadata from leaking into the previous plot.
- Malformed coordinate pairs are not silently truncated; invalid pairs are left blank for correction.
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

k1, k2, k3, k4, k5, k6 = st.columns(6)


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


coordinates = (
    filtered_df[
        [
            "latitude",
            "longitude"
        ]
    ]
    .notna()
    .all(axis=1)
    .sum()
)

k5.metric(
    "Coordinates",
    coordinates
)


species_count = (
    filtered_df[
        "species_planted"
    ]
    .dropna()
    .nunique()
)

k6.metric(
    "Species Entries",
    species_count
)


# ============================================================
# SECOND KPI ROW
# ============================================================

k7, k8, k9, k10, k11, k12 = st.columns(6)


total_planted = (
    pd.to_numeric(
        filtered_df[
            "total_planted"
        ],
        errors="coerce"
    )
    .sum()
)

k7.metric(
    "Trees Planted",
    f"{total_planted:,.0f}"
)


total_alive = (
    pd.to_numeric(
        filtered_df[
            "total_alive"
        ],
        errors="coerce"
    )
    .sum()
)

k8.metric(
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

k9.metric(
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

k10.metric(
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

k11.metric(
    "Area (ha)",
    f"{area_total:,.3f}"
)


avg_age = (
    pd.to_numeric(
        filtered_df[
            "trees_age"
        ],
        errors="coerce"
    )
    .mean()
)

if pd.isna(avg_age):

    age_display = "N/A"

else:

    age_display = (
        f"{avg_age:.0f} yrs"
    )

k12.metric(
    "Average Tree Age",
    age_display
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