# SRTR PSR Raw Archive (preserved copy)

Permanent in-repo copy of the **raw SRTR Program-Specific Report (PSR)
"National Center-Level Summary Data"** Excel bundles, so the project never
again depends on SRTR's hosting. SRTR has already relocated this data once
(www.srtr.org → srtr.hrsa.gov, 2024 migration); this archive removes that risk.

## What's here

15 all-organ zip bundles, one per release (2018–2025):

```
csrs_final_tables_<CODE>all.zip
```

`<CODE>` is the SRTR release code in YYMM form. Releases are **May (05) and
November (11)**, plus the early **June (06)** release — there is **no January
release** (a `2401`-style code does not exist; probing one returns 404).

Each zip contains 8 per-organ workbooks: `csrs_final_tables_<CODE>_<ORG>.xls`
for ORG in {KI, LI, HR, LU, PA, IN, HL, KP}. Legacy `.xls` (OLE2) — open with
`xlrd`, not `openpyxl`. Note: members are sometimes at the zip root and
sometimes nested under `csrs_final_tables_<CODE>all/`; extract with junked
paths or glob `*_<ORG>.xls`.

Releases: 1811, 1905, 1911, 2006, 2011, 2105, 2111, 2205, 2211, 2305, 2311,
2405, 2411, 2505, 2511.

## Schema eras (for parsing the transplant-rate column `SAL_TOTTX_C12`)

- **2111 → 2511:** dedicated `Table B7` sheet.
- **1811 → 2105:** no usable `Table B7`; the column lives in `Table B6`.
- The parser in `scripts/fetch-srtr-observed-rates.py` scans for whichever
  sheet carries `SAL_TOTTX_C12` rather than hardcoding a sheet name, so all
  eras are handled automatically.

## Integrity

`SHA256SUMS.txt` holds checksums for all 15 zips. Verify with:

```bash
cd data/srtr-archive && shasum -a 256 -c SHA256SUMS.txt
```

## Provenance & re-fetch

Source: `https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables_all/csrs_final_tables_<CODE>all.zip`
(public data, no auth). Re-fetchable via `scripts/fetch-srtr-excel.py --historical`.

## Derived artifacts (what the app/validation actually use)

- `data/srtr-observed-rates-historical.json` — per-center observed transplant/
  death/delisting rates, all releases (built by `fetch-srtr-observed-rates.py --historical`).
- `data/srtr-observed-rates.json` — current release only (calibration input).
- `data/srtr-historical.json` — city-level trend series.
