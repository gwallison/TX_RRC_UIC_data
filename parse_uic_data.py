"""
TX RRC UIC Data Parser
======================
Converts uif700a.txt.gz (fixed-width ASCII) to CSV files.

Data source: https://mft.rrc.texas.gov/link/d2438c05-b42f-45a8-b0c6-edceb0912767
Manual: uic_manual_uia010_3116.pdf (UIA010)

Record types in the file:
  01 - Well master record / UIC Root Segment (UIROOT) — one per well
  02 - Permit remarks (UIRMK)
  03 - Well monitoring parameters (UIMONTR)
  04 - H-10 monthly injection monitoring (UIMNH10) — regular injection wells
  05 - H-10 monthly monitoring (UIMNH10H) — storage wells
  07 - H-5 pressure test records
  08 - H-5 remarks
  09 - Enforcement records
  10 - Permit date records
  11 - Permit extension records
  12 - Enforcement remarks
  13 - Storage well master record
  14 - Annual monitoring records

Output CSVs (written to ./output/):
  uic_wells.csv               - Type 01 well master records (UIROOT)
  uic_h10_monitoring.csv      - Type 04 H-10 monthly injection data
  uic_h10_storage.csv         - Type 05 H-10 monthly storage well data

Usage:
  python parse_uic_data.py

All positions in field specs are 0-indexed (Python slice notation).
The layout file (manual UIA010) uses 1-based positions; subtract 1 for Python.
"""

import csv
import gzip
from pathlib import Path

DATA_FILE = "uif700a.txt.gz"
OUTPUT_DIR = Path("output")

# ---------------------------------------------------------------------------
# District code mapping (2-digit coded value → actual RRC district label)
# Source: UIA010 manual, UIC-DIST description
# ---------------------------------------------------------------------------
DIST_CODE_MAP = {
    "01": "01", "02": "02", "03": "03", "04": "04",
    "05": "05", "06": "06", "07": "6E", "08": "7B",
    "09": "7C", "10": "08", "11": "8A", "12": "8B",
    "13": "09", "14": "10",
}

# ---------------------------------------------------------------------------
# Field definitions
# Each entry: (field_name, start_0indexed, length, type)
# type: 'str' = strip whitespace; 'int' = strip + int (blank/zeros -> None)
# ---------------------------------------------------------------------------

# Type 01 - UIC Root Segment (UIROOT)
# Source: Manual UIA010, UIW700A4 copybook, pages II.1-II.5
# Record length: 622 bytes (620 data + 2-byte record ID prefix)
# All positions are 0-indexed; manual uses 1-based.
FIELDS_01 = [
    # Basic identifiers
    ("segment_id",          0,  2, "str"),  # RRC-TAPE-RECORD-ID ("01")
    ("uic_cntl_no",         2,  9, "str"),  # UIC-CNTL-NO: 9-digit primary key (unique per well)
    # UIC-ALT-KEY1 (secondary index, redefines positions 11-25):
    ("og_type",            11,  1, "str"),  # UIC-O-G-TYPE: O=Oil, G=Gas, A=No lease assigned
    ("lease_id",           12,  6, "str"),  # UIC-LEASE-ID: oil lease# or gas well ID
    ("dist_code",          18,  2, "str"),  # UIC-DIST: coded district (see DIST_CODE_MAP)
    ("well_no",            20,  6, "str"),  # UIC-WELL-NO: RRC-assigned well number
    # Other root fields
    ("oper_no",            26,  6, "str"),  # UIC-OPER: operator number
    ("county_no",          32,  3, "str"),  # UIC-CNTY-NO: county code (3 digits)
    ("api_no",             35,  5, "str"),  # UIC-API-NO: 5-digit API unique well code
    ("field_no",           40,  8, "str"),  # UIC-FIELD-NO: RRC field number
    ("well_class",         48,  1, "str"),  # UIC-CLASS: 2=injection/disposal, 5=storage/geothermal
    # Approval date (CCYYMMDD split)
    ("appr_cc",            49,  2, "str"),  # UIC-APPR-CC
    ("appr_yy",            51,  2, "str"),  # UIC-APPR-YY
    ("appr_mm",            53,  2, "str"),  # UIC-APPR-MONTH
    ("appr_dd",            55,  2, "str"),  # UIC-APPR-DAY
    # W-14 (saltwater disposal application) date
    ("w14_cc",             57,  2, "str"),
    ("w14_yy",             59,  2, "str"),
    ("w14_mm",             61,  2, "str"),
    ("w14_dd",             63,  2, "str"),
    # H-1 (injection into producing reservoir) date
    ("h1_cc",              65,  2, "str"),
    ("h1_yy",              67,  2, "str"),
    ("h1_mm",              69,  2, "str"),
    ("h1_dd",              71,  2, "str"),
    # Authorization letter date
    ("letter_cc",          73,  2, "str"),
    ("letter_yy",          75,  2, "str"),
    ("letter_mm",          77,  2, "str"),
    ("letter_dd",          79,  2, "str"),
    # Permit-added-to-system date
    ("pmt_added_cc",       81,  2, "str"),
    ("pmt_added_yy",       83,  2, "str"),
    ("pmt_added_mm",       85,  2, "str"),
    ("pmt_added_dd",       87,  2, "str"),
    # Status/cancel
    ("activated_flag",     89,  1, "str"),  # Y = is/was active, N = never active
    ("cancel_cc",          90,  2, "str"),
    ("cancel_yy",          92,  2, "str"),
    ("cancel_mm",          94,  2, "str"),
    ("cancel_dd",          96,  2, "str"),
    # W-2/G-1 completion report date
    ("w2g1_cc",            98,  2, "str"),
    ("w2g1_yy",           100,  2, "str"),
    ("w2g1_mm",           102,  2, "str"),
    ("w2g1_dd",           104,  2, "str"),
    # W-3 / other dates
    ("w3_cc",             106,  2, "str"),
    ("w3_yy",             108,  2, "str"),
    ("w3_mm",             110,  2, "str"),
    ("w3_dd",             112,  2, "str"),
    # Injection type and comments
    ("type_inj",          114,  1, "str"),  # UIC-TYPE-INJ numeric code
    ("type_inj_cmt",      115, 30, "str"),  # UIC-TYPE-INJ-CMT description
    ("type_flu_cmt",      145, 30, "str"),  # UIC-TYPE-FLU-CMT fluid comment
    # Permitted volumes and depths
    ("bbl_vol_inj",       175,  9, "str"),  # UIC-BBL-VOL-INJ: max permitted BBL/day
    ("mcf_vol_inj",       184,  9, "str"),  # UIC-MCF-VOL-INJ: max permitted MCF/day
    ("top_inj_zone",      193,  5, "str"),  # UIC-TOP-INJ-ZONE: depth to top of injection zone (ft)
    ("bot_inj_zone",      198,  5, "str"),  # UIC-BOT-INJ-ZONE: depth to bottom (ft)
    ("max_inj_pressure",  203,  5, "str"),  # UIC-MAX-INJ-PRESSURE: max liquid inj pressure (PSIG)
    ("h1_no",             208,  5, "str"),  # UIC-H1-NO: H-1 project number
    ("w14_no",            213,  5, "str"),  # UIC-W14-NO: W-14 number
    # Injection fluid flags (Y=authorized, N=not, 0=not reported)
    ("inj_sw",            218,  1, "str"),  # Salt water
    ("inj_fw",            219,  1, "str"),  # Fresh water
    ("inj_frac_water",    220,  1, "str"),  # Frac water
    ("inj_norm",          221,  1, "str"),  # NORM (naturally occurring radioactive material)
    ("inj_co2",           222,  1, "str"),  # CO2
    ("inj_gas",           223,  1, "str"),  # Gas
    ("inj_h2s",           224,  1, "str"),  # H2S
    ("inj_polymer",       225,  1, "str"),  # Polymer
    ("inj_steam",         226,  1, "str"),  # Steam
    ("inj_air",           227,  1, "str"),  # Air
    ("inj_nitrogen",      228,  1, "str"),  # Nitrogen
    ("inj_other",         229,  1, "str"),  # Other fluid
    ("inj_bw",            230,  1, "str"),  # Brackish water
    ("inj_lpg",           231,  1, "str"),  # LPG
    ("max_inj_pressure2", 232,  5, "str"),  # UIC-MAX-INJ-PRESSURE-2: max gas inj pressure
    # Location
    ("location",          364, 52, "str"),  # UIC-LOCATION: legal location string
    ("survey_lines",      416, 28, "str"),  # UIC-SURVEY-LINES
    # Administrative
    ("well_status",       444,  1, "str"),  # UIC-STATUS: 0=not received, I=incomplete, C=complete
    ("geothermal",        445,  1, "str"),  # UIC-GEOTHERMAL: 0=no, G=geothermal
    ("depth_boz",         447,  5, "str"),  # UIC-DEPTH-BOZ: depth to bottom of perforated zone (ft)
    ("depth_pkr",         452,  5, "str"),  # UIC-DEPTH-PKR: tubing packer depth (ft)
    ("inj_mode",          457,  1, "str"),  # UIC-INJ-MODE: C=casing, T=tubing
    ("docket_no_dist",    559,  2, "str"),  # UIC-DOCKET-NO-DIST
    ("docket_no",         563,  5, "str"),  # UIC-OLD-DOCKET-NO
]

# Type 04 - H-10 monthly injection monitoring (regular wells)
# Source: uif700a.uimnh10_layout (SEGMENT UIMNH10, Record Type=04)
# Record length: 622 bytes (54 data + 568 trailing spaces)
FIELDS_04 = [
    ("segment_id",         0,  2, "str"),
    ("century",            2,  2, "int"),   # e.g. 19, 20
    ("year",               4,  2, "int"),   # e.g. 80, 24
    ("month",              6,  2, "int"),   # 01-12
    ("avg_inj_pressure",   8,  4, "int"),   # Average injection pressure (PSIG)
    ("max_inj_pressure",  12,  4, "int"),   # Maximum injection pressure (PSIG)
    ("total_vol_bbl",     16,  8, "int"),   # Total volume injected (barrels)
    ("total_vol_mcf",     24,  8, "int"),   # Total volume injected (MCF, for gas)
    ("annulus_minimum",   32,  4, "int"),   # Annulus minimum pressure (PSIG)
    ("annulus_maximum",   36,  4, "int"),   # Annulus maximum pressure (PSIG)
    ("annulus_count",     40,  2, "int"),   # Number of annulus pressure readings
    ("doc_cycle",         42,  4, "int"),   # Document cycle
    ("doc_batch",         46,  4, "int"),   # Document batch
    ("doc_item",          50,  4, "int"),   # Document item
]

# Type 05 - H-10 monthly monitoring (storage wells)
# Source: UIW700L2.txt / uif700a.uimnh10h_layout (SEGMENT UIMNH10H, Record Type=05)
# Record length: 622 bytes (60 data + 562 trailing spaces)
# Note: sign fields are ' ' (positive/zero) or '-' (negative)
FIELDS_05 = [
    ("segment_id",              0,  2, "str"),
    ("century",                 2,  2, "int"),
    ("year",                    4,  2, "int"),
    ("month",                   6,  2, "int"),
    ("max_hydrocarb_psig",      8,  5, "int"),   # Max hydrocarbon pressure (PSIG)
    ("max_brine_psig",         13,  5, "int"),   # Max brine pressure (PSIG)
    ("inj_brine_bbls_sign",    18,  1, "str"),   # Sign for brine volume (' '=positive, '-'=negative)
    ("inj_brine_bbls",         19,  9, "int"),   # Net brine injected/withdrawn (barrels)
    ("inj_hydro_bbls_sign",    28,  1, "str"),   # Sign for hydrocarbon volume
    ("inj_hydrocarb_bbls",     29,  9, "int"),   # Net hydrocarbon injected/withdrawn (barrels)
    ("inj_gas_mcf_sign",       38,  1, "str"),   # Sign for gas volume
    ("inj_gas_mcf",            39,  9, "int"),   # Net gas injected/withdrawn (MCF)
    ("doc_cycle",              48,  4, "int"),
    ("doc_batch",              52,  4, "int"),
    ("doc_item",               56,  4, "int"),
]


def extract_field(line, start, length, ftype):
    """Slice a field from a fixed-width line and convert to the specified type."""
    end = start + length
    raw = line[start:end] if len(line) >= end else line[start:]
    val = raw.strip()
    if ftype == "int":
        if not val:
            return None
        try:
            return int(val)
        except ValueError:
            return None
    return val  # 'str' — return stripped string (may be empty)


def parse_record(line, fields):
    """Parse a fixed-width line using a field spec list. Returns a dict."""
    return {name: extract_field(line, start, length, ftype)
            for name, start, length, ftype in fields}


def signed_volume(sign_val, vol_val):
    """Combine a sign field (' ' or '-') with a numeric value."""
    if vol_val is None:
        return None
    return -vol_val if sign_val == "-" else vol_val


def make_date(century, year, month):
    """Build a YYYY-MM string from century (e.g.19), year (e.g.83), month (e.g.01)."""
    if century is None or year is None or month is None:
        return None
    return f"{century:02d}{year:02d}-{month:02d}"


def make_date8(cc, yy, mm, dd):
    """Build a YYYY-MM-DD date from four 2-char string fields. Returns '' if all zero/blank."""
    if not cc or not yy or cc == "00" and yy == "00":
        return ""
    return f"{cc}{yy}-{mm or '00'}-{dd or '00'}"


def decode_district(dist_code):
    """Convert coded 2-digit district to actual RRC district label."""
    return DIST_CODE_MAP.get(dist_code, dist_code)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    wells_path = OUTPUT_DIR / "uic_wells.csv"
    h10_path = OUTPUT_DIR / "uic_h10_monitoring.csv"
    h10h_path = OUTPUT_DIR / "uic_h10_storage.csv"

    # Wells CSV: all parsed fields + computed columns
    wells_headers = (
        [f[0] for f in FIELDS_01]
        + ["actual_district", "api_number", "appr_date", "cancel_date",
           "pmt_added_date", "h1_date", "w14_date"]
    )
    # Key fields carried into H-10 rows for cross-referencing
    well_key_headers = ["uic_cntl_no", "og_type", "lease_id", "actual_district",
                        "well_no", "oper_no", "county_no", "api_number", "well_class"]
    h10_headers = (
        well_key_headers + ["year_month"]
        + [f[0] for f in FIELDS_04]
    )
    h10h_headers = (
        well_key_headers + ["year_month"]
        + [f[0] for f in FIELDS_05]
        + ["inj_brine_bbls_net", "inj_hydrocarb_bbls_net", "inj_gas_mcf_net"]
    )

    total_lines = 0
    type_counts = {}
    skipped = 0

    current_well = {k: None for k in well_key_headers}

    print(f"Reading {DATA_FILE} ...")
    print(f"Writing output to {OUTPUT_DIR}/")

    with (
        gzip.open(DATA_FILE, "rt", encoding="ascii", errors="replace") as infile,
        open(wells_path, "w", newline="", encoding="utf-8") as wf,
        open(h10_path, "w", newline="", encoding="utf-8") as h10f,
        open(h10h_path, "w", newline="", encoding="utf-8") as h10hf,
    ):
        wells_writer = csv.DictWriter(wf, fieldnames=wells_headers)
        h10_writer = csv.DictWriter(h10f, fieldnames=h10_headers)
        h10h_writer = csv.DictWriter(h10hf, fieldnames=h10h_headers)

        wells_writer.writeheader()
        h10_writer.writeheader()
        h10h_writer.writeheader()

        for line in infile:
            total_lines += 1
            raw = line.rstrip("\n")

            if len(raw) < 2:
                skipped += 1
                continue

            rec_type = raw[0:2]
            type_counts[rec_type] = type_counts.get(rec_type, 0) + 1

            if rec_type == "01":
                row = parse_record(raw, FIELDS_01)
                # Decode district and build computed columns
                actual_dist = decode_district(row.get("dist_code", ""))
                api_number = ""
                cty = row.get("county_no", "")
                api = row.get("api_no", "")
                if cty and api:
                    api_number = f"42-{cty.zfill(3)}-{api.zfill(5)}"
                appr_date = make_date8(row.get("appr_cc"), row.get("appr_yy"),
                                       row.get("appr_mm"), row.get("appr_dd"))
                cancel_date = make_date8(row.get("cancel_cc"), row.get("cancel_yy"),
                                         row.get("cancel_mm"), row.get("cancel_dd"))
                pmt_added_date = make_date8(row.get("pmt_added_cc"), row.get("pmt_added_yy"),
                                             row.get("pmt_added_mm"), row.get("pmt_added_dd"))
                h1_date = make_date8(row.get("h1_cc"), row.get("h1_yy"),
                                     row.get("h1_mm"), row.get("h1_dd"))
                w14_date = make_date8(row.get("w14_cc"), row.get("w14_yy"),
                                      row.get("w14_mm"), row.get("w14_dd"))
                out = {
                    **row,
                    "actual_district": actual_dist,
                    "api_number": api_number,
                    "appr_date": appr_date,
                    "cancel_date": cancel_date,
                    "pmt_added_date": pmt_added_date,
                    "h1_date": h1_date,
                    "w14_date": w14_date,
                }
                wells_writer.writerow(out)
                current_well = {
                    "uic_cntl_no": row["uic_cntl_no"],
                    "og_type": row.get("og_type", ""),
                    "lease_id": row.get("lease_id", ""),
                    "actual_district": actual_dist,
                    "well_no": row.get("well_no", ""),
                    "oper_no": row.get("oper_no", ""),
                    "county_no": cty,
                    "api_number": api_number,
                    "well_class": row.get("well_class", ""),
                }

            elif rec_type == "04":
                row = parse_record(raw, FIELDS_04)
                out = {
                    **current_well,
                    "year_month": make_date(row["century"], row["year"], row["month"]),
                    **row,
                }
                h10_writer.writerow(out)

            elif rec_type == "05":
                row = parse_record(raw, FIELDS_05)
                out = {
                    **current_well,
                    "year_month": make_date(row["century"], row["year"], row["month"]),
                    **row,
                    "inj_brine_bbls_net": signed_volume(
                        row["inj_brine_bbls_sign"], row["inj_brine_bbls"]
                    ),
                    "inj_hydrocarb_bbls_net": signed_volume(
                        row["inj_hydro_bbls_sign"], row["inj_hydrocarb_bbls"]
                    ),
                    "inj_gas_mcf_net": signed_volume(
                        row["inj_gas_mcf_sign"], row["inj_gas_mcf"]
                    ),
                }
                h10h_writer.writerow(out)

            if total_lines % 1_000_000 == 0:
                print(f"  ...{total_lines:,} lines processed", flush=True)

    print(f"\nDone. {total_lines:,} total lines.")
    print(f"  Skipped (too short): {skipped}")
    print()
    print("Record type counts:")
    for rt, count in sorted(type_counts.items()):
        print(f"  {rt!r:6s}  {count:>10,}")
    print()
    print("Output files:")
    for path in [wells_path, h10_path, h10h_path]:
        size = path.stat().st_size if path.exists() else 0
        print(f"  {path}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
