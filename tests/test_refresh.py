"""Tests for the snapshot refresh tool: structure is validated before anything is written."""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "refresh_snapshots", os.path.join(ROOT, "tools", "refresh_snapshots.py"))
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


def bundled():
    return json.load(open(refresh.newest()))


def test_bundled_snapshot_is_structurally_valid():
    assert refresh.validate(bundled()) == []


def test_impossible_fill_level_is_rejected():
    bad = json.loads(json.dumps(bundled()))
    bad["eu"]["full"] = 140.0
    assert any("disagrees" in p or "outside" in p for p in refresh.validate(bad))


def test_missing_countries_is_rejected():
    bad = json.loads(json.dumps(bundled()))
    bad["countries"] = []
    assert any("country" in p for p in refresh.validate(bad))


def test_snapshot_age_is_computed_from_the_filename():
    age = refresh.snapshot_age_days()
    assert age is None or age >= 0


def test_an_api_error_body_is_reported_as_an_access_problem():
    """AGSI returns HTTP 200 with an error object; that must not read as a parsing failure."""
    import importlib.util, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "refresh_snapshots", os.path.join(root, "tools", "refresh_snapshots.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    body = {"last_page": 0, "total": 0, "dataset": "storage ERROR",
            "error": "access denied", "message": "Invalid or missing API key", "data": []}
    assert "access denied" in mod.api_error(body)
    assert mod.api_error({"eu": {}, "countries": []}) is None


def test_a_single_day_snapshot_never_becomes_the_model_input(tmp_path, monkeypatch):
    """A CSV import has no winter block; it must not redefine the model by being newest."""
    import json
    import agsi

    full = json.load(open(agsi.SNAP))
    (tmp_path / "agsi_2026-01-01.json").write_text(json.dumps(full))
    (tmp_path / "agsi_2026-11-17.json").write_text(
        json.dumps({"_gas_day": "2026-11-17", "winter_2025_26": []}))

    monkeypatch.setattr(agsi, "DATA", str(tmp_path))
    assert agsi._latest_snapshot().endswith("agsi_2026-01-01.json")
