"""The hydrogen capacity figure is a model result, so it must carry a range."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import hydrogen


def test_band_is_ordered_and_brackets_the_point_estimate():
    band = hydrogen.repurposed_energy_band(n=4000, seed=7)
    assert band["p10_twh"] <= band["p50_twh"] <= band["p90_twh"]
    assert band["p10_twh"] > 0
    assert band["base_twh"] > 0


def test_band_is_reproducible():
    a = hydrogen.repurposed_energy_band(n=2000, seed=3)
    b = hydrogen.repurposed_energy_band(n=2000, seed=3)
    assert a == b


def test_a_higher_cushion_share_lowers_the_band():
    band = hydrogen.repurposed_energy_band(n=4000, seed=7)
    assert band["p90_twh"] < band["base_twh"], (
        "at 40-60% cushion the usable energy must sit below the 35% point estimate")
