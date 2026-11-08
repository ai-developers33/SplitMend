"""Download original public archives, cache atomically, and record checksums."""

import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    (
        "har",
        "https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip",
        "https://doi.org/10.24432/C54S4K",
    ),
    (
        "beijing",
        "https://archive.ics.uci.edu/static/public/501/beijing+multi+site+air+quality+data.zip",
        "https://doi.org/10.24432/C5RK5G",
    ),
    (
        "oulad",
        "https://ndownloader.figshare.com/files/8606371",
        "https://doi.org/10.6084/m9.figshare.5081998.v1",
    ),
]


def fetch(item):
    name, url, doi = item
    path = ROOT / "data" / "raw" / f"{name}.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temp = path.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        temp.replace(path)
    digest = hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
    print(name, path.stat().st_size, digest, flush=True)
    return {
        "dataset": name,
        "archive": str(path.relative_to(ROOT)),
        "url": url,
        "doi": doi,
        "license": "CC-BY-4.0",
        "bytes": path.stat().st_size,
        "sha256": digest,
    }


def main():
    target = ROOT / "data" / "sources.json"
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, SOURCES))
    if target.exists():
        previous = json.loads(target.read_text())
        known = {s["dataset"]: s["sha256"] for s in previous["sources"]}
        for s in records:
            if known.get(s["dataset"]) != s["sha256"]:
                raise ValueError(f"archive checksum changed: {s['dataset']}")
    else:
        target.write_text(
            json.dumps(
                {"retrieved_utc": datetime.now(timezone.utc).isoformat(), "sources": records},
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
