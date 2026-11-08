"""Publish complete compressed records without exposing partially written files."""

import gzip
import io
import json
import os
import tempfile
from pathlib import Path


def save_gzip_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8") as stream:
                    json.dump(obj, stream, sort_keys=True, allow_nan=False, separators=(",", ":"))
            raw.flush()
            os.fsync(raw.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
