"""Formula explanations (sprint 13, UC-10)."""

import pytest

from pumpflow import explain

REQUIRED = {"head", "affinity", "efficiency", "npsha", "viscosity_b", "operating_point"}


def test_required_keys_present():
    assert REQUIRED <= set(explain.FORMULAS)


def test_every_entry_is_a_non_empty_title_and_text():
    for key, (title, text) in explain.FORMULAS.items():
        assert isinstance(title, str) and title.strip(), key
        assert isinstance(text, str) and text.strip(), key


def test_tooltip_contains_title_and_text():
    for key, (title, text) in explain.FORMULAS.items():
        tip = explain.tooltip(key)
        assert title in tip and text in tip


def test_tooltip_unknown_key_raises_keyerror():
    with pytest.raises(KeyError):
        explain.tooltip("no-such-formula")
