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
