# TX RRC UIC Data Parser

Python tools to download and reformat **Underground Injection Control (UIC)** well data published monthly by the [Texas Railroad Commission (RRC)](https://www.rrc.texas.gov/). The raw data is delivered as a fixed-width mainframe-format file; these scripts convert it to usable CSV files.

---

## What Is This Data?

The RRC maintains records on all injection wells in Texas under the EPA's Class II Underground Injection Control program. This includes:

- **Saltwater disposal (SWD) wells** — the most common type; dispose of produced water from oil and gas operations
- **Enhanced recovery wells** — inject water, CO2, gas, or other fluids to maintain reservoir pressure and improve oil recovery
- **Storage wells** — store hydrocarbons underground

The dataset covers **126,532 wells** with monthly injection records going back to the 1970s — over **20 million H-10 monthly monitoring records** in total.

---

## Data Source

Data is published monthly (by the 3rd workday) at:

> https://mft.rrc.texas.gov/link/d2438c05-b42f-45a8-b0c6-edceb0912767

The portal requires a browser to download files (JavaScript-based). Download these files into the project directory:

| File | Size | Description |
|------|------|-------------|
| `uif700a.txt.gz` | ~267 MB | Main data file (ASCII, gzip compressed) |
| `uif700a.uimnh10_layout` | 3 KB | Field layout for H-10 monitoring records |
| `uif700a.uimnh10h_layout` | 3 KB | Field layout for H-10 storage well records |
| `uif700a.Readme.txt` | <1 KB | RRC notes on the file |
| `UIW700L2.txt` | 3 KB | Additional layout documentation |

The full field specifications are in the official manual:  
**Publication UIA010** — [UIC Magnetic Tape User's Guide (PDF)](https://www.rrc.texas.gov/media/v3onmigl/uic_manual_uia010_3116.pdf)

---

## Output

Running `parse_uic_data.py` produces three CSV files in an `output/` subdirectory:

### `uic_wells.csv` — 126,532 rows
One row per well. Key columns:

| Column | Description |
|--------|-------------|
| `uic_cntl_no` | Primary key — 9-digit unique control number |
| `api_number` | API well number: `42-CCC-NNNNN` (Texas + county + unique) |
| `og_type` | `O`=Oil well, `G`=Gas well, `A`=No lease assigned |
| `lease_id` | Oil lease number or gas well ID |
| `actual_district` | RRC district (01–10, 6E, 7B, 7C, 8A, 8B) |
| `well_no` | RRC-assigned well number |
| `oper_no` | Operator number (cross-reference with RRC operator master) |
| `county_no` | County code |
| `well_class` | `2`=Injection/disposal, `5`=Storage/geothermal |
| `appr_date` | Permit approval date (YYYY-MM-DD) |
| `cancel_date` | Cancellation date, if applicable |
| `activated_flag` | `Y`=is or was active, `N`=never active |
| `max_inj_pressure` | Maximum permitted injection pressure (PSIG) |
| `top_inj_zone` / `bot_inj_zone` | Depth to top/bottom of injection zone (feet) |
| `inj_sw`, `inj_fw`, `inj_co2`, ... | Authorized injection fluids (Y/N flags) |
| `bbl_vol_inj` / `mcf_vol_inj` | Maximum permitted injection volume (BBL or MCF per day) |
| `location` / `survey_lines` | Legal location description |

### `uic_h10_monitoring.csv` — ~20.9 million rows
Monthly H-10 injection reports for regular injection wells (record type 04). Key columns:

| Column | Description |
|--------|-------------|
| `uic_cntl_no` | Links to `uic_wells.csv` |
| `year_month` | Reporting period (YYYY-MM) |
| `avg_inj_pressure` | Average injection pressure (PSIG) |
| `max_inj_pressure` | Maximum injection pressure (PSIG) |
| `total_vol_bbl` | Total volume injected (barrels) |
| `total_vol_mcf` | Total volume injected (MCF, for gas injection) |
| `annulus_minimum` / `annulus_maximum` | Tubing-casing annulus pressure range (PSIG) |
| `annulus_count` | Number of annulus pressure readings |

### `uic_h10_storage.csv` — ~250,000 rows
Monthly H-10H reports for storage wells (record type 05). Includes signed net volumes (positive = injected, negative = withdrawn).

---

## Usage

### Requirements

Python 3.8+ with no external dependencies for the parser itself.  
`pdfplumber` is needed only if you want to read the PDF manual programmatically:

```bash
pip install pdfplumber
```

### Run the parser

```bash
# Download the data files from the RRC portal first, then:
python parse_uic_data.py
```

Processes ~25 million records; takes roughly 10 minutes. Output goes to `output/`.

### Exploration utilities

```bash
# Peek at the first 30 lines of the raw data
python peek_data.py

# Survey all record types and counts across the full file
python survey_data.py
```

---

## Raw File Structure

The file contains 25+ million fixed-width records (622 bytes each), organized hierarchically — each well's master record is followed by its child records:

| Type | Count | Description |
|------|------:|-------------|
| `01` | 126,532 | Well master (parsed → `uic_wells.csv`) |
| `02` | 1,261,142 | Permit remarks text |
| `03` | 126,532 | Well monitoring parameters |
| `04` | 20,926,669 | H-10 monthly injection monitoring (parsed) |
| `05` | 250,531 | H-10 monthly storage well monitoring (parsed) |
| `07` | 868,116 | H-5 pressure test records |
| `08` | 532,926 | H-5 remarks |
| `09` | 88,121 | Enforcement records |
| `10` | 500,989 | Permit date records |
| `11` | 147,057 | Permit extension records |
| `12` | 23,205 | Enforcement remarks |
| `13` | 21,423 | Storage well master records |
| `14` | 243,054 | Annual monitoring records |

Record types 07–14 are present in the file but not yet parsed to CSV.

---

## Dataset Highlights

- **126,532 total wells** — 92,983 ever-active, 52,967 cancelled
- **District 08 (Midland/Permian Basin)** has the most wells: 34,904 — nearly 3× the next district
- **Saltwater disposal** is the dominant use: 116,711 wells authorized
- **CO2 injection** (primarily EOR): 16,723 wells
- Monthly records span from the **1970s through early 2026**

---

## Cross-Reference

- Look up individual wells: https://webapps2.rrc.texas.gov/EWA/uicQueryAction.do
- The `api_number` column (`42-CCC-NNNNN`) is compatible with other Texas oil and gas datasets that use the standard API numbering system.
- The `oper_no` (operator number) can be cross-referenced with the RRC operator master file, available at the same data portal.

---

## Notes on the Format

- The raw file uses **1-based byte positions** in the COBOL copybook; the parser converts to 0-based Python slices.
- An EBCDIC version (`uif700.ebc.gz`) is also available on the portal but requires special decoding; the ASCII `.txt.gz` version is used here.
- Record types 04 and 05 store only 54–60 bytes of actual data; the rest of the 622-byte record is trailing spaces.
- The district field in type 01 records uses a **coded value** (01–14) that maps to actual district labels — see `DIST_CODE_MAP` in `parse_uic_data.py`.
