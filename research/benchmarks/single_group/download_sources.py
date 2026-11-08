"""Download the three larger public source archives and verify exact hashes."""
from pathlib import Path
import json
import urllib.request
import hashlib

ROOT=Path(__file__).resolve().parent

def main():
    directory=ROOT/"data/source"
    for item in json.loads((directory/"download_manifest.json").read_text()):
        path=directory/item["name"]
        if not path.exists():
            partial=path.with_suffix(path.suffix+".partial")
            try:
                with urllib.request.urlopen(item["url"],timeout=120) as response,partial.open("wb") as out:
                    while chunk:=response.read(1024*1024):out.write(chunk)
                with partial.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
                if digest!=item["sha256"]:raise ValueError(f"Source hash mismatch: {path.name}")
                partial.replace(path)
            finally:
                if partial.exists():partial.unlink()
        with path.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=item["sha256"]:raise ValueError(f"Source hash mismatch: {path.name}")
        print(f"Verified {path.name}",flush=True)

if __name__=="__main__":main()
