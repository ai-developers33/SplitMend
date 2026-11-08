import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from artifact_io import save_gzip_json  # noqa: E402


def test_failed_write_preserves_existing_record(tmp_path):
    target = tmp_path / "result.json.gz"
    save_gzip_json(target, {"complete": True})
    original = target.read_bytes()
    with pytest.raises(ValueError):
        save_gzip_json(target, {"bad": float("nan")})
    assert target.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == [target.name]


def test_complete_record_is_readable_and_deterministic(tmp_path):
    target = tmp_path / "nested" / "record.json.gz"
    record = {"assignments": {str(i): "train" for i in range(1000)}, "label": "été"}
    save_gzip_json(target, record)
    original = target.read_bytes()
    with gzip.open(target, "rt", encoding="utf-8") as stream:
        assert json.load(stream) == record
    save_gzip_json(target, record)
    assert target.read_bytes() == original
