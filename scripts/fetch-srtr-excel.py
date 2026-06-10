#!/usr/bin/env python3
"""
Download SRTR PSR National Center-Level Summary Data Excel files.

Source: https://www.srtr.org/reports/program-specific-reports/
Auth: None (public data, no API key required)
Schedule: Biannual (January + July releases)
Output: data/srtr-raw/*.xls (current), data/srtr-raw/historical/{YYMM}/*.xls (historical)

SRTR publishes center-level transplant data as Excel files, one per organ.
These contain wait time percentiles (Table B10), waitlist outcomes (Table B7),
and pre-transplant mortality (Tables B4-B5) for every US transplant center.

Historical mode (--historical) downloads archived zip bundles for multi-year
trend analysis. Each zip contains per-organ xls files for that release.
"""

import os
import sys
import time
import urllib.request
import urllib.error
import zipfile
import io

# SRTR PSR download URL pattern.
# NOTE (2026-06): SRTR migrated from www.srtr.org to srtr.hrsa.gov. The old
# www.srtr.org/assets/media/PSRdownloads/... paths now 301-redirect and then
# 404. The working path is srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables/.
# Verified: the CURRENT release (2511) downloads; older release codes (2505,
# 2411, …) and the bulk csrs_tables_all/*.zip archives 404 — the migrated site
# only hosts the current release. Historical re-fetch is therefore no longer
# possible; data/srtr-historical.json is the committed source of record.
# FIXME: Auto-detect the latest release prefix from the PSR page.
RELEASE_PREFIX = "2511"
BASE_URL = "https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables"
# Bulk archive zips are no longer hosted post-migration (verified 404). Kept for
# reference / in case SRTR restores them; download_historical() warns on failure.
ARCHIVE_BASE_URL = "https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables_all"

# Organ codes matching our 6 supported organ types
ORGAN_CODES = {
    "kidney": "KI",
    "liver": "LI",
    "heart": "HR",
    "lung": "LU",
    "pancreas": "PA",
    "intestine": "IN",
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "srtr-raw")
HISTORICAL_DIR = os.path.join(OUTPUT_DIR, "historical")

# Historical releases: one per year (January release preferred, covers prior year).
# YYMM format. Maps release code → nominal year for trend labeling.
HISTORICAL_RELEASES = {
    "1901": 2019,
    "2001": 2020,
    "2101": 2021,
    "2201": 2022,
    "2301": 2023,
    "2401": 2024,
}
# Current release is handled separately (already in srtr-raw/)
CURRENT_RELEASE_YEAR = 2025


def download_file(url: str, dest: str) -> bool:
    """Download a file with retry logic."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TransPlan/2.0 (transplant research tool)"
            })
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                with open(dest, "wb") as f:
                    f.write(data)
                size_mb = len(data) / (1024 * 1024)
                print(f"  Downloaded {os.path.basename(dest)} ({size_mb:.1f} MB)")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"  Attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
    return False


def download_and_extract_zip(url: str, dest_dir: str) -> bool:
    """Download a zip file and extract its contents to dest_dir."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TransPlan/2.0 (transplant research tool)"
            })
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
                size_mb = len(data) / (1024 * 1024)
                print(f"  Downloaded zip ({size_mb:.1f} MB), extracting...")

            os.makedirs(dest_dir, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                # Extract only xls files, flatten into dest_dir
                extracted = 0
                for info in zf.infolist():
                    if info.filename.lower().endswith(".xls") and not info.is_dir():
                        # Use just the filename (no subdirectory paths)
                        basename = os.path.basename(info.filename)
                        target = os.path.join(dest_dir, basename)
                        with zf.open(info) as src, open(target, "wb") as dst:
                            dst.write(src.read())
                        extracted += 1
                print(f"  Extracted {extracted} xls files to {dest_dir}")
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"  Attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
        except zipfile.BadZipFile as e:
            print(f"  Bad zip file: {e}")
            return False
    return False


def download_current(organs: list[str]) -> tuple[int, list[str]]:
    """Download current release Excel files (one per organ)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    success = 0
    failed = []

    for organ in organs:
        code = ORGAN_CODES.get(organ)
        if not code:
            print(f"Unknown organ: {organ}. Valid: {list(ORGAN_CODES.keys())}")
            continue

        filename = f"csrs_final_tables_{RELEASE_PREFIX}_{code}.xls"
        url = f"{BASE_URL}/{filename}"
        dest = os.path.join(OUTPUT_DIR, filename)

        # Skip if already downloaded and > 1MB (valid file)
        if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
            print(f"  {filename} already exists ({os.path.getsize(dest) / 1024 / 1024:.1f} MB), skipping")
            success += 1
            continue

        print(f"Downloading {organ} ({code})...")
        if download_file(url, dest):
            success += 1
        else:
            failed.append(organ)

    return success, failed


def download_historical(releases: dict[str, int] | None = None) -> tuple[int, list[str]]:
    """
    Download historical SRTR releases as zip bundles.

    Each release is a zip containing per-organ xls files.
    Extracted to data/srtr-raw/historical/{YYMM}/.
    """
    if releases is None:
        releases = HISTORICAL_RELEASES

    os.makedirs(HISTORICAL_DIR, exist_ok=True)
    success = 0
    failed = []

    for release_code, year in sorted(releases.items()):
        dest_dir = os.path.join(HISTORICAL_DIR, release_code)

        # Skip if already extracted (check for at least one xls file)
        if os.path.isdir(dest_dir):
            xls_files = [f for f in os.listdir(dest_dir) if f.endswith(".xls")]
            if len(xls_files) >= len(ORGAN_CODES):
                print(f"  {release_code} (year {year}) already extracted ({len(xls_files)} files), skipping")
                success += 1
                continue

        filename = f"csrs_final_tables_{release_code}.zip"
        url = f"{ARCHIVE_BASE_URL}/{filename}"
        print(f"Downloading {release_code} (year {year})...")

        if download_and_extract_zip(url, dest_dir):
            success += 1
        else:
            failed.append(f"{release_code} (year {year})")

    return success, failed


def main():
    # Parse arguments
    historical = "--historical" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if historical:
        # Parse optional --releases flag
        custom_releases = None
        for i, a in enumerate(sys.argv):
            if a == "--releases" and i + 1 < len(sys.argv):
                codes = sys.argv[i + 1].split(",")
                custom_releases = {c.strip(): HISTORICAL_RELEASES.get(c.strip(), 2000 + int(c.strip()[:2]))
                                   for c in codes if c.strip()}
                break

        print("=== Downloading Historical SRTR Releases ===")
        success, failed = download_historical(custom_releases)
        print(f"\nHistorical: {success}/{success + len(failed)} downloaded")
        if failed:
            print(f"Failed: {', '.join(failed)}")

        # Also download current release
        print("\n=== Downloading Current Release ===")
        organs = args if args else list(ORGAN_CODES.keys())
        cur_success, cur_failed = download_current(organs)
        print(f"\nCurrent: {cur_success}/{len(organs)} downloaded")

        if failed or cur_failed:
            sys.exit(1)
    else:
        organs = args if args else list(ORGAN_CODES.keys())
        success, failed = download_current(organs)
        print(f"\nDone: {success}/{len(organs)} downloaded")
        if failed:
            print(f"Failed: {', '.join(failed)}")
            sys.exit(1)


if __name__ == "__main__":
    main()
