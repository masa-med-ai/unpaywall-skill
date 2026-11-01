#!/usr/bin/env python3
"""Look up legal open-access copies of a paper via Unpaywall; optionally save the PDF."""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.unpaywall.org/v2/"
UA = "unpaywall-skill/1.0 (python urllib)"
MAX_PDF_BYTES = 100 * 1024 * 1024
EXIT_SETUP_NEEDED = 2
SETUP_MESSAGE = """SETUP_REQUIRED: UNPAYWALL_EMAIL is not set.
Unpaywall identifies API users by email address. Set your own address once.

macOS (zsh):
  echo 'export UNPAYWALL_EMAIL="you@your-domain"' >> ~/.zshrc
Linux (bash):
  echo 'export UNPAYWALL_EMAIL="you@your-domain"' >> ~/.bashrc
Windows (PowerShell):
  setx UNPAYWALL_EMAIL "you@your-domain"

Then restart Claude and any open terminals so the setting is picked up."""


def normalize_doi(raw):
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", raw.strip(), flags=re.I)
    if not re.match(r"^10\.\d{4,9}/\S+$", doi):
        sys.exit(f"Not a DOI: {raw}")
    return doi


def lookup(doi, email):
    query = urllib.parse.urlencode({"email": email})
    url = f"{API}{urllib.parse.quote(doi, safe='/')}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 422:
            sys.exit("Unpaywall rejected the email address. Set UNPAYWALL_EMAIL to your own real address.")
        body = e.read().decode("utf-8", "replace")[:300]
        sys.exit(f"Unpaywall API error {e.code}: {body}")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach Unpaywall: {e.reason}")


def summarize(rec):
    locations = [
        {
            "host_type": loc.get("host_type"),
            "version": loc.get("version"),
            "license": loc.get("license"),
            "url_for_pdf": loc.get("url_for_pdf"),
            "url_for_landing_page": loc.get("url_for_landing_page"),
        }
        for loc in rec.get("oa_locations") or []
    ]
    first = (rec.get("z_authors") or [{}])[0]
    return {
        "doi": rec.get("doi"),
        "title": rec.get("title"),
        "first_author": first.get("family") or first.get("raw_author_name"),
        "journal": rec.get("journal_name"),
        "year": rec.get("year"),
        "is_oa": rec.get("is_oa"),
        "oa_status": rec.get("oa_status"),
        "best_location": (rec.get("best_oa_location") or {}).get("url"),
        "locations": locations,
    }


def safe_name(info):
    parts = [info.get("first_author") or "paper", str(info.get("year") or ""), info["doi"]]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", "_".join(p for p in parts if p))
    return stem.strip("._")[:120] + ".pdf"


def unique_path(path):
    base, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(path):
        path = f"{base}_{n}{ext}"
        n += 1
    return path


def fetch_pdf(url, dest):
    """Return an error string, or None once a real PDF has been written to dest."""
    if not url.lower().startswith(("http://", "https://")):
        return "unsupported URL scheme"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            head = res.read(1024)
            if not head.lstrip().startswith(b"%PDF-"):
                return "response is not a PDF (likely an HTML page or bot check)"
            total = len(head)
            with open(tmp, "wb") as out:
                out.write(head)
                while chunk := res.read(1024 * 256):
                    total += len(chunk)
                    if total > MAX_PDF_BYTES:
                        raise ValueError("file exceeds 100 MB limit")
                    out.write(chunk)
        os.replace(tmp, dest)
        return None
    except (urllib.error.URLError, OSError, ValueError) as e:
        return str(e)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    # Windows consoles often default to cp932/cp1252, which cannot encode every title.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doi", help="DOI, doi: prefix or doi.org URL")
    parser.add_argument("--download", action="store_true", help="save the first PDF that works")
    parser.add_argument("--out-dir", default=".", help="directory for the PDF")
    args = parser.parse_args()

    email = os.environ.get("UNPAYWALL_EMAIL", "").strip()
    if not email:
        print(SETUP_MESSAGE, file=sys.stderr)
        sys.exit(EXIT_SETUP_NEEDED)

    doi = normalize_doi(args.doi)
    rec = lookup(doi, email)
    if rec is None:
        print(json.dumps({"doi": doi, "found": False}, ensure_ascii=False, indent=2))
        return

    info = summarize(rec)
    if args.download:
        pdf_urls = [loc["url_for_pdf"] for loc in info["locations"] if loc["url_for_pdf"]]
        attempts = []
        info["saved_to"] = None
        if pdf_urls:
            os.makedirs(args.out_dir, exist_ok=True)
            dest = unique_path(os.path.join(args.out_dir, safe_name(info)))
            for url in dict.fromkeys(pdf_urls):
                error = fetch_pdf(url, dest)
                if error is None:
                    info["saved_to"] = os.path.abspath(dest)
                    info["saved_from"] = url
                    break
                attempts.append({"url": url, "error": error})
        info["failed_attempts"] = attempts
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
