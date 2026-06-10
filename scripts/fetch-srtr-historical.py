#!/usr/bin/env python3
"""
Download and extract historical SRTR PSR archive zip files.

Scrapes the SRTR PSR page to discover available archived releases,
downloads any that aren't already extracted locally, and unzips them
into data/srtr-raw/historical/{YYMM}/.

NOTE (2026-06): SRTR migrated from www.srtr.org to srtr.hrsa.gov. The bulk
historical archives are alive and well at the new host — every release's
all-organ zip is served at:
  https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables_all/csrs_final_tables_<CODE>all.zip
(verified: all 14 historical codes + the current 2511 download, unzip, and
parse). Release codes are MMM = 05 (May) / 11 (Nov), plus some 06 — there is
NO January (01) release, so probing e.g. '2401' will 404. The per-organ direct
path works only for the CURRENT release; historical data comes via the zips.

Usage:
    python3 scripts/fetch-srtr-historical.py          # download new releases only
    python3 scripts/fetch-srtr-historical.py --all     # re-download everything
    python3 scripts/fetch-srtr-historical.py --parse   # download + run parser
"""

import os
import re
import sys
import zipfile
import urllib.request

SRTR_URL = "https://srtr.hrsa.gov/transplant-professionals/program-specific-report/program-specific-reports-psr/"
BASE_DOWNLOAD_URL = "https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables_all/"
HISTORICAL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "srtr-raw", "historical")

# Only download releases from 2019 onward (code >= 1811)
MIN_RELEASE_CODE = "1811"


def discover_releases_from_page() -> list[str]:
    """Fetch the SRTR PSR page and extract archive release codes from the dropdown.

    The archive dropdown (id="releases") has option values like "1811all", "1905all", etc.
    We parse these to get the 4-digit release codes.
    """
    print(f"Fetching {SRTR_URL} ...")
    req = urllib.request.Request(SRTR_URL, headers={"User-Agent": "TransPlan-DataPipeline/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8")

    # Option values are like: <option value="1811all">January 2019</option>
    codes = re.findall(r'<option\s+value="(\d{4})all">', html)
    # Filter to 2019+ only
    codes = sorted(c for c in codes if c >= MIN_RELEASE_CODE)

    if codes:
        print(f"  Found {len(codes)} archive releases (>= {MIN_RELEASE_CODE}): {codes}")
    else:
        print("  WARNING: Could not find any release codes in page HTML.")
    return codes


def get_existing_releases() -> set[str]:
    """Return set of release codes already extracted locally."""
    existing = set()
    if not os.path.isdir(HISTORICAL_DIR):
        return existing
    for entry in os.listdir(HISTORICAL_DIR):
        entry_path = os.path.join(HISTORICAL_DIR, entry)
        if os.path.isdir(entry_path) and len(entry) == 4 and entry.isdigit():
            # Check it has .xls files
            if any(f.endswith(".xls") for f in os.listdir(entry_path)):
                existing.add(entry)
    return existing


def download_and_extract(code: str) -> bool:
    """Download a single archive zip and extract it."""
    url = f"{BASE_DOWNLOAD_URL}csrs_final_tables_{code}all.zip"
    target_dir = os.path.join(HISTORICAL_DIR, code)
    zip_path = os.path.join(HISTORICAL_DIR, f"csrs_final_tables_{code}all.zip")

    os.makedirs(target_dir, exist_ok=True)

    print(f"  Downloading {url} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TransPlan-DataPipeline/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        with open(zip_path, "wb") as f:
            f.write(data)
        print(f"    {len(data):,} bytes")
    except Exception as e:
        print(f"    FAILED: {e}")
        return False

    # Extract
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(target_dir)

        # Flatten if zip created a subdirectory
        for sub in os.listdir(target_dir):
            sub_path = os.path.join(target_dir, sub)
            if os.path.isdir(sub_path) and sub != "__MACOSX":
                for f in os.listdir(sub_path):
                    os.rename(os.path.join(sub_path, f), os.path.join(target_dir, f))
                os.rmdir(sub_path)

        xls_count = sum(1 for f in os.listdir(target_dir) if f.endswith(".xls"))
        print(f"    Extracted {xls_count} .xls files")
        return True
    except Exception as e:
        print(f"    EXTRACT FAILED: {e}")
        return False


def main():
    force_all = "--all" in sys.argv
    run_parser = "--parse" in sys.argv

    os.makedirs(HISTORICAL_DIR, exist_ok=True)

    # Discover available releases
    available_codes = discover_releases_from_page()
    existing_codes = get_existing_releases()

    if available_codes:
        new_codes = sorted(set(available_codes) - existing_codes)
    else:
        print("  Could not auto-discover release codes from page.")
        print("  Use the URL mapping in docs/data-provenance.md for manual downloads.")
        return

    if force_all:
        to_download = sorted(available_codes)
        print(f"\n--all flag: re-downloading all {len(to_download)} releases")
    elif new_codes:
        to_download = new_codes
        print(f"\n{len(new_codes)} new release(s) to download: {new_codes}")
        print(f"({len(existing_codes)} already present: {sorted(existing_codes)})")
    else:
        print(f"\nAll {len(existing_codes)} releases already downloaded. Nothing to do.")
        to_download = []

    # Download
    downloaded = 0
    for code in to_download:
        if download_and_extract(code):
            downloaded += 1

    if downloaded > 0:
        print(f"\nDownloaded {downloaded} new release(s).")
    elif to_download:
        print("\nWARNING: No releases were successfully downloaded.")

    # Run parser if requested
    if run_parser and (downloaded > 0 or existing_codes):
        print("\nRunning historical parser...")
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "parse-srtr-reports.py"), "--historical"],
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        sys.exit(result.returncode)
    elif run_parser:
        print("\nNo historical data available to parse.")


if __name__ == "__main__":
    main()
