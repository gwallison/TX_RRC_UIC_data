# TX RRC UIC Data — Project Summary

## Source

- **Portal:** https://mft.rrc.texas.gov/link/d2438c05-b42f-45a8-b0c6-edceb0912767
- **Manual:** `uic_manual_uia010_3116 (1).pdf` (UIA010 — UIC Magnetic Tape User's Guide)
- **Data file:** `uif700a.txt.gz` (267 MB compressed, ~1.5 GB uncompressed)
- **Data date:** April 1, 2026 (monthly release)

---

## What the Data Is

Underground Injection Control (UIC) well data for all injection wells in Texas, maintained by the Railroad Commission of Texas (RRC). Covers:

- Well inventory and permit information
- Monthly H-10 injection monitoring reports (volumes and pressures)
- H-10H monthly monitoring for storage wells
- H-5 pressure testing, enforcement actions, and more (not yet parsed — see below)

---

## Raw File Structure

The file contains **25,117,090 records** of multiple types, organized hierarchically (one well master followed by its child records):

| Record Type | Count | Description |
|-------------|------:|-------------|
| `01` | 126,532 | Well master record (UIC Root Segment / UIROOT) |
| `02` | 1,261,142 | Permit remarks text |
| `03` | 126,532 | Well monitoring parameters |
| `04` | 20,926,669 | H-10 monthly injection monitoring |
| `05` | 250,531 | H-10 monthly storage well monitoring |
| `07` | 868,116 | H-5 pressure test records |
| `08` | 532,926 | H-5 remarks |
| `09` | 88,121 | Enforcement records |
| `10` | 500,989 | Permit date records |
| `11` | 147,057 | Permit extension records |
| `12` | 23,205 | Enforcement remarks |
| `13` | 21,423 | Storage well master records |
| `14` | 243,054 | Annual monitoring records |

Records are **fixed-width ASCII, 622 bytes per line**. Type 04 and 05 records use only the first 54/60 bytes; the rest is spaces.

---

## Output Files (in `output/`)

| File | Rows | Size | Description |
|------|-----:|-----:|-------------|
| `uic_wells.csv` | 126,532 | 44 MB | Well master records (type 01) |
| `uic_h10_monitoring.csv` | 20,926,669 | 2.0 GB | H-10 monthly injection data (type 04) |
| `uic_h10_storage.csv` | 250,531 | 26 MB | H-10 monthly storage well data (type 05) |

---

## Key Columns

### `uic_wells.csv`
| Column | Description |
|--------|-------------|
| `uic_cntl_no` | Primary key — 9-digit unique control number. Links to all child records. |
| `api_number` | Full API number: `42-CCC-NNNNN` (Texas state + county + unique well) |
| `og_type` | O=Oil well, G=Gas well, A=No lease assigned |
| `lease_id` | Oil lease number or gas well ID (6 digits) |
| `actual_district` | RRC district (01–10, 6E, 7B, 7C, 8A, 8B) after decoding |
| `well_no` | RRC-assigned well number |
| `oper_no` | Operator number (6 digits — cross-reference with operator master file) |
| `county_no` | County code (3 digits) |
| `well_class` | 2=Injection/disposal, 5=Storage/geothermal |
| `appr_date` | Original permit approval date (YYYY-MM-DD) |
| `cancel_date` | Cancellation date, if applicable |
| `activated_flag` | Y=is or was active, N=never active |
| `max_inj_pressure` | Maximum permitted injection pressure (PSIG) |
| `top_inj_zone` / `bot_inj_zone` | Depth to top/bottom of permitted injection zone (feet) |
| `inj_sw/fw/co2/gas/...` | Authorized injection fluids (Y/N flags) |
| `bbl_vol_inj` / `mcf_vol_inj` | Maximum permitted injection volume (BBL/day or MCF/day) |
| `location` / `survey_lines` | Legal location description |

### `uic_h10_monitoring.csv`
| Column | Description |
|--------|-------------|
| `uic_cntl_no` | Links to `uic_wells.csv` |
| `year_month` | Reporting period (YYYY-MM) |
| `avg_inj_pressure` | Average injection pressure that month (PSIG) |
| `max_inj_pressure` | Maximum injection pressure that month (PSIG) |
| `total_vol_bbl` | Total volume injected (barrels) |
| `total_vol_mcf` | Total volume injected (MCF, for gas injection) |
| `annulus_minimum` / `annulus_maximum` | Tubing-casing annulus pressure range (PSIG) |
| `annulus_count` | Number of annulus pressure readings |

### `uic_h10_storage.csv`
| Column | Description |
|--------|-------------|
| `uic_cntl_no` | Links to `uic_wells.csv` |
| `year_month` | Reporting period (YYYY-MM) |
| `max_hydrocarb_psig` | Maximum hydrocarbon pressure (PSIG) |
| `max_brine_psig` | Maximum brine pressure (PSIG) |
| `inj_brine_bbls_net` | Net brine injected/withdrawn (barrels; negative = withdrawn) |
| `inj_hydrocarb_bbls_net` | Net hydrocarbon injected/withdrawn (barrels) |
| `inj_gas_mcf_net` | Net gas injected/withdrawn (MCF) |

---

## Dataset Statistics

| Metric | Value |
|--------|------:|
| Total wells | 126,532 |
| Ever-active wells | 92,983 |
| Cancelled wells | 52,967 |
| Class 2 (injection/disposal) | 126,531 |
| Class 5 (storage/geothermal) | 1 |

**Wells by district (top 5):**

| District | Wells | Notes |
|----------|------:|-------|
| 08 (Midland) | 34,904 | Permian Basin — largest |
| 8A (Lubbock) | 24,728 | Permian Basin |
| 09 (San Angelo) | 19,475 | |
| 7B (Abilene) | 13,712 | |
| 03 (Kilgore) | 6,832 | East Texas |

**Authorized injection fluids (wells):**

| Fluid | Wells |
|-------|------:|
| Salt water | 116,711 |
| Fresh water | 25,268 |
| CO2 | 16,723 |
| Gas | 7,838 |
| Frac water | 521 |
| Steam | 184 |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `parse_uic_data.py` | Main parser — reads `uif700a.txt.gz`, writes the three CSV files |
| `survey_data.py` | Surveys all record types and counts in the raw file |
| `peek_data.py` | Shows the first N lines of the compressed file |

To re-run the parser (takes ~10 minutes):
```
cd C:\MyDocs\sandbox\TX_RRC_UIC_data
python parse_uic_data.py
```

---

## Not Yet Parsed

The following record types are in the raw file but not yet converted to CSV:

| Type | Count | Description |
|------|------:|-------------|
| `02` | 1,261,142 | Permit remarks (free text) |
| `03` | 126,532 | Well monitoring parameters (H-10 form details) |
| `07` | 868,116 | H-5 pressure test records |
| `08` | 532,926 | H-5 remarks |
| `09` | 88,121 | Enforcement records |
| `10` | 500,989 | Permit date records |
| `11` | 147,057 | Permit extension records |
| `12` | 23,205 | Enforcement remarks |
| `13` | 21,423 | Storage well master records |
| `14` | 243,054 | Annual monitoring records |

Field layouts for these types are in the manual (`uic_manual_uia010_3116 (1).pdf`), which is now readable via `pdfplumber`.

---

## Cross-Reference

- **Online well lookup:** https://webapps2.rrc.texas.gov/EWA/uicQueryAction.do
- The `api_number` column (`42-CCC-NNNNN`) can cross-reference with other Texas oil/gas datasets.
- The `oper_no` links to the RRC operator master file (separate download).
