#!/usr/bin/env python3
"""
Download SRTR PSR National Center-Level Summary Data Excel files.

Source: https://www.srtr.org/reports/program-specific-reports/
Auth: None (public data, no API key required)
Schedule: Biannual (January + July releases)
Output: data/srtr-raw/*.xls

SRTR publishes center-level transplant data as Excel files, one per organ.
These contain wait time percentiles (Table B10), waitlist outcomes (Table B7),
and pre-transplant mortality (Tables B4-B5) for every US transplant center.
"""

import os
import sys
import time
import urllib.request
import urllib.error

# SRTR PSR download URL pattern
# The '2511' prefix = January 2025 release. Updates biannually.
# FIXME: Auto-detect the latest release prefix from the PSR page.
RELEASE_PREFIX = "2511"
BASE_URL = "https://www.srtr.org/assets/media/PSRdownloads/csrs_tables"

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


def download_file(url: str, dest: str) -> bool:
    """Download a file with retry logic."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TransPlan/2.0 (transplant research tool)"
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
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


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    organs = sys.argv[1:] if len(sys.argv) > 1 else list(ORGAN_CODES.keys())
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

    print(f"\nDone: {success}/{len(organs)} downloaded")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
