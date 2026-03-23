"""Fetch contact info for all 248 SRTR transplant centers.

Source: https://reportapi.srtr.org/psr/{CODE}TX1
Returns centerDetail with address, phone, website, city, state, zip.

Usage:
    python scripts/scrape_center_contacts.py
    python scripts/scrape_center_contacts.py --dry-run   # test first 5 only
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import urllib.request
import urllib.error

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "center-contacts.json"
CENTERS_FILE = DATA_DIR / "srtr-all-centers.json"

SRTR_API = "https://reportapi.srtr.org/psr/{code}TX1"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "TransPlan/1.0 (research tool; contact: transplant-research@example.com)",
}


def fetch_center(code: str) -> dict | None:
    url = SRTR_API.format(code=code)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        detail = data.get("centerDetail", {})
        if not detail:
            return None
        return {
            "code": code,
            "address": detail.get("address", "").strip(),
            "city": detail.get("city", "").strip(),
            "state": detail.get("state", "").strip(),
            "zip": detail.get("zipCode", "").strip(),
            "phone": detail.get("phoneNumber", "").strip(),
            "website": (detail.get("url") or "").strip(),
        }
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {code}")
        return None
    except Exception as e:
        print(f"  Error for {code}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Only fetch first 5 centers")
    parser.add_argument("--workers", type=int, default=8, help="Parallel workers (default 8)")
    parser.add_argument("--delay", type=float, default=0.1, help="Seconds between batches")
    args = parser.parse_args()

    with open(CENTERS_FILE) as f:
        all_centers = json.load(f).get("centers", {})

    codes = list(all_centers.keys())
    if args.dry_run:
        codes = codes[:5]
        print(f"Dry run: fetching {len(codes)} centers")
    else:
        print(f"Fetching contact info for {len(codes)} centers ({args.workers} workers)...")

    results = {}
    failed = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_center, code): code for code in codes}
        done = 0
        for future in as_completed(futures):
            code = futures[future]
            done += 1
            contact = future.result()
            if contact:
                results[code] = contact
                if done % 20 == 0 or args.dry_run:
                    print(f"  [{done}/{len(codes)}] {code}: {contact.get('phone', 'no phone')} | {contact.get('website', 'no website')[:50]}")
            else:
                failed.append(code)
                if args.dry_run:
                    print(f"  [{done}/{len(codes)}] {code}: FAILED")
            time.sleep(args.delay / args.workers)

    output = {
        "_meta": {
            "source": "https://reportapi.srtr.org/psr/{CODE}TX1",
            "fetched_centers": len(results),
            "failed_codes": failed,
            "total_attempted": len(codes),
        },
        "contacts": results,
    }

    if not args.dry_run:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nSaved {len(results)} contacts → {OUTPUT_FILE}")
        if failed:
            print(f"Failed ({len(failed)}): {', '.join(failed)}")
    else:
        print("\nDry-run output (not saved):")
        for code, c in list(results.items())[:5]:
            print(f"  {code}: {c}")

    return results


if __name__ == "__main__":
    main()
