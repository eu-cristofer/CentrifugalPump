"""
``.pumpflow`` schema v2 — migration + settings codec (Sprint 2b).

Qt-free layers (codec, ``migrate``, fixtures) run everywhere; the scene layer
skips cleanly without PySide6.  Fixtures in ``tests/fixtures/v1`` are real v1
project files; ``expected.json`` holds the per-node state/status (and
compliance values) a v1 load produced before the schema change.
"""

import copy
import json
import os
from pathlib import Path

import pytest

from pumpflow import settings_codec as codec
from pumpflow import units
from pumpflow.persistence import migrate, read_json, read_project

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "v1"
FILES = sorted(FIXTURES.glob("*.pumpflow"))

RATED = {
    "tag": "B-2351105",
    "service": "",
    "standard": "API610 (12a ed.) / ISO 13709 + N-553",
    "q": 833.0,
    "q_unit": "m³/h",
    "head": 73.0,
    "head_unit": "m",
    "n": 1750.0,
    "power": 252.0,
    "power_unit": "kW",
    "eff": 61.0,
    "head_shutoff": 117.0,
    "npsha": 0.0,
    "n_unit": "rpm",
    "eff_unit": "%",
    "head_shutoff_unit": "m",
    "npsha_unit": "m",
    "dens_rel": 0.736,
    "dens_unit": "kg/m³",
    "visc": 0.567,
    "visc_unit": "cSt",
    "parallel": False,
    "fluid_name": "Rated fluid",
    "fluid_choice": "",
}
FLUID = {
    "source": "manual",
    "name": "Service fluid",
    "temp": 25.0,
    "temp_unit": "°C",
    "dens": 736.0,
    "dens_unit": "kg/m³",
    "visc": 0.567,
    "visc_unit": "cSt",
}
TEST_POINTS = {
    "pump_tag": "B-2351105A",
    "fluid_choice": "",
    "columns": {
        "q": "m³/h",
        "p_suc": "bar",
        "p_dis": "bar",
        "temp_c": "°C",
        "n": "rpm",
        "power": "kW",
        "head": "m",
        "eff": "%",
    },
    "pressure_ref": "g",
    "rows": [
        {
            "q": 300.0,
            "p_suc": 1.8,
            "p_dis": 12.53,
            "temp_c": 34.0,
            "n": 1799.0,
            "power": 248.0,
            "head": None,
            "eff": None,
        },
        {
            "q": 500.0,
            "p_suc": 1.8,
            "p_dis": 11.56,
            "temp_c": 34.0,
            "n": 1800.0,
            "power": 270.0,
            "head": 78.5,
            "eff": 55.0,
        },
    ],
}
POINT = {
    "label": "Point",
    "mode": "direct",
    "q": 800.0,
    "q_unit": "m³/h",
    "head": 75.0,
    "head_unit": "m",
    "p_suc": 0.5,
    "p_dis": 8.0,
    "p_unit": "bar",
    "fluid_choice": "",
    "power": 0.0,
    "power_unit": "kW",
    "eff": 0.0,
    "eff_unit": "%",
    "p_ref": "g",
}
CORRECTION = {
    "lock_to_rated": True,
    "target_speed": 1750.0,
    "target_speed_unit": "rpm",
    "apply_speed": True,
    "apply_density": True,
    "apply_viscosity": False,
    "degree": 3,
    "fluid_choice": "",
}
PLOT = {
    "show_poly": True,
    "show_spline": True,
    "show_points": True,
    "head_ylim": None,
    "power_ylim": None,
    "eff_ylim": None,
}
DEFAULTS = {
    "rated_point": RATED,
    "fluid": FLUID,
    "test_points": TEST_POINTS,
    "point": POINT,
    "correction": CORRECTION,
    "performance_plot": PLOT,
}

QUANTITY_KEYS = {
    "rated_point": ("q", "head", "power", "visc", "n", "eff", "head_shutoff", "npsha"),
    "fluid": ("temp", "dens", "visc"),
    "point": ("q", "head", "power", "eff", "p_suc", "p_dis"),
    "correction": ("target_speed",),
}


# --------------------------------------------------------------------------- #
# Fixtures: every v1 file migrates, idempotently, to v2 shapes
# --------------------------------------------------------------------------- #
def test_fixtures_present():
    assert len(FILES) >= 8


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_migrate_idempotent_and_v2_shapes(path):
    raw = read_json(path)
    before = copy.deepcopy(raw)
    m1 = migrate(raw)
    assert raw == before  # input never mutated
    assert m1["meta"]["schema_version"] == 2
    assert migrate(m1) == m1
    assert read_project(path) == m1
    for node in m1["nodes"]:
        st = node["settings"]
        for key in QUANTITY_KEYS.get(node["kind"], ()):
            if st.get(key) is not None:
                assert isinstance(st[key], dict), (node["id"], key)
                assert {"value", "unit"} <= set(st[key]), (node["id"], key)
        if node["kind"] == "test_points":
            assert "columns" in st and st["pressure_ref"] == "g" and "unit" not in st
        if node["kind"] == "rated_point":
            assert "unit" not in st and "q_unit" not in st


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_codec_fixed_point_on_shipped_files(path):
    for node in migrate(read_json(path))["nodes"]:
        stored = node["settings"]
        runtime = codec.decode(node["kind"], stored)
        assert codec.encode(node["kind"], runtime) == stored, node["id"]


def test_float_magnitudes_not_perturbed():
    for kind, rt in DEFAULTS.items():
        back = codec.decode(kind, codec.encode(kind, rt))
        for k, v in rt.items():
            assert back[k] == v and type(back[k]) is type(v), (kind, k)


# --------------------------------------------------------------------------- #
# Hazard regression: missing *_unit under a US preset is canonical, not gpm
# --------------------------------------------------------------------------- #
def test_missing_unit_key_is_canonical_not_preset():
    v1 = {
        "meta": {"unit_preset": "US"},
        "nodes": [
            {
                "id": "r",
                "kind": "rated_point",
                "x": 0,
                "y": 0,
                "settings": {"q": 833.0, "head": 73.0, "unit": "bar"},
            }
        ],
        "edges": [],
    }
    out = migrate(v1)
    st = out["nodes"][0]["settings"]
    assert st["q"] == {"value": 833.0, "unit": "m**3/h"}
    assert st["head"] == {"value": 73.0, "unit": "m"}
    assert "unit" not in st  # stale rated key dropped
    assert out["meta"] == {"unit_preset": "US", "schema_version": 2}


# --------------------------------------------------------------------------- #
# Codec round-trips
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", sorted(DEFAULTS))
def test_codec_roundtrip_defaults(kind):
    rt = DEFAULTS[kind]
    v2 = codec.encode(kind, rt)
    assert codec.decode(kind, v2) == rt
    assert codec.encode(kind, codec.decode(kind, v2)) == v2


def test_codec_roundtrip_ylim_lists_and_us_units():
    plot = dict(
        PLOT, head_ylim=[0.0, 100.0], power_ylim=[0.0, 300.0], eff_ylim=[0.0, 80.0]
    )
    v2 = codec.encode("performance_plot", plot)
    assert v2["head_ylim"] == {"value": [0.0, 100.0], "unit": "m"}
    assert v2["power_ylim"]["unit"] == "kW" and v2["eff_ylim"]["unit"] == "percent"
    assert codec.decode("performance_plot", v2) == dict(
        plot, head_ylim_unit="m", power_ylim_unit="kW", eff_ylim_unit="%"
    )
    rated = dict(
        RATED, q=3000.0, q_unit="US GPM", head=240.0, head_unit="ft", power_unit="hp"
    )
    assert codec.decode("rated_point", codec.encode("rated_point", rated)) == rated


def test_passthrough_kinds_and_unknown_keys():
    for kind in (
        "curve_fit",
        "compliance",
        "explore_plot",
        "report_export",
        "markdown_note",
    ):
        s = {"a": 1, "b": {"c": [1, 2]}}
        out = codec.encode(kind, s)
        assert out == s and out is not s
        assert codec.decode(kind, s) == s
    st = {"q": 1.0, "weird": {"x": 1}}  # missing optional keys are tolerated
    assert codec.decode("rated_point", codec.encode("rated_point", st))["weird"] == {
        "x": 1
    }


# --------------------------------------------------------------------------- #
# Unknown display units fall back sensibly
# --------------------------------------------------------------------------- #
def test_label_for():
    assert units.label_for("capacity", "m**3/h") == "m³/h"
    assert units.label_for("capacity", "gal/min") == "US GPM"
    assert units.label_for("head", "ft") == "ft"
    assert units.label_for("temperature", "degF") == "°F"
    assert units.label_for("head", "psi") is None


def test_decode_display_unit_kept_when_known():
    out = codec.decode("rated_point", {"head": {"value": 100, "unit": "ft"}})
    assert out["head"] == 100 and out["head_unit"] == "ft"


def test_decode_unknown_display_unit_goes_canonical():
    out = codec.decode("rated_point", {"q": {"value": 1.0, "unit": "m**3/s"}})
    assert out["q"] == pytest.approx(3600.0)
    assert out["q_unit"] == "m³/h"


def test_decode_keeps_stored_units_for_former_fixed_fields():
    """Since S3, n / η / shut-off / NPSHa have their own unit keys: decode keeps
    the stored unit (as a display label) and the value untouched; the standard
    magnitude is what to_signal sees."""
    out = codec.decode(
        "rated_point",
        {
            # revolution/second, NOT Hz: Pint's Hz is 1/s while rpm is rev/min
            # (1 rev = 2π rad), so Hz -> rpm would be off by 2π.
            "n": {"value": 29.1666666667, "unit": "revolution/second"},
            "head_shutoff": {"value": 300.0, "unit": "ft"},
            "eff": {"value": 0.61, "unit": "dimensionless"},
        },
    )
    assert (out["n"], out["n_unit"]) == (29.1666666667, "rev/s")
    assert (out["head_shutoff"], out["head_shutoff_unit"]) == (300.0, "ft")
    assert (out["eff"], out["eff_unit"]) == (0.61, "fraction")
    assert units.to_standard(out["n"], "speed", "rev/s") == pytest.approx(1750.0)
    assert units.to_standard(300.0, "head", "ft") == pytest.approx(91.44)


# --------------------------------------------------------------------------- #
# test_points columns
# --------------------------------------------------------------------------- #
def _tp_stored(**over):
    cols = {
        "q": "gal/min",
        "p_suc": "psi",
        "p_dis": "psi",
        "temp_c": "degF",
        "n": "rpm",
        "power": "kW",
        "head": "m",
        "eff": "percent",
    }
    st = {
        "pump_tag": "A",
        "fluid_choice": "",
        "columns": cols,
        "pressure_ref": "g",
        "rows": [
            {
                "q": 100.0,
                "p_suc": 14.5037738,
                "p_dis": 145.037738,
                "temp_c": 212.0,
                "n": 1800.0,
                "power": 10.0,
                "head": None,
                "eff": None,
            }
        ],
    }
    st.update(over)
    return st


def test_test_points_columns_keep_their_units():
    """Since S3 the table works in per-column units: decode maps Pint strings to
    display labels and leaves every row value untouched."""
    rt = codec.decode("test_points", _tp_stored())
    assert "unit" not in rt and rt["pressure_ref"] == "g"
    assert rt["columns"] == {
        "q": "US GPM",
        "p_suc": "psi",
        "p_dis": "psi",
        "temp_c": "°F",
        "n": "rpm",
        "power": "kW",
        "head": "m",
        "eff": "%",
    }
    assert rt["rows"][0] == _tp_stored()["rows"][0]
    # Re-encoding writes the one compact on-disk spelling (as quantity_io does):
    back = codec.encode("test_points", rt)
    assert back["columns"]["q"] == "gal/min" and back["columns"]["temp_c"] == "°F"
    assert back["rows"] == _tp_stored()["rows"]
    assert codec.encode("test_points", codec.decode("test_points", back)) == back


def test_test_points_kgf_and_absolute_reference_are_kept():
    st = _tp_stored()
    st["columns"].update(p_suc="kgf/cm**2", p_dis="kgf/cm**2")
    st["pressure_ref"] = "a"
    rt = codec.decode("test_points", st)
    assert rt["columns"]["p_suc"] == rt["columns"]["p_dis"] == "kgf/cm²"
    assert rt["pressure_ref"] == "a"
    assert rt["rows"][0] == st["rows"][0]


# --------------------------------------------------------------------------- #
# Qt layer: v1 fixtures load identically; to_dict is v2 and a fixed point
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; scene tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def expected():
    return json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


def _scene():
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node

    return GraphScene(make_node)


def _summary(scene):
    out = {}
    for item in scene.nodes:
        lg = item.logic
        entry = [lg.kind, lg.state, lg.status]
        res = lg.outputs_cache.get("ComplianceResult")
        if res is not None:
            entry.append(
                [
                    [
                        p.name,
                        repr(p.predicted),
                        repr(p.minimum),
                        repr(p.maximum),
                        p.passed,
                    ]
                    for p in res.parameters
                ]
            )
        out[lg.node_id] = entry
    return out


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_v1_fixture_loads_with_same_results(qapp, expected, path):
    scene = _scene()
    scene.load_dict(read_json(path))  # raw v1: load_dict migrates
    assert _summary(scene) == expected[path.name]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_scene_to_dict_is_v2_fixed_point(qapp, path):
    scene = _scene()
    scene.load_dict(read_json(path))
    out = scene.to_dict()
    assert out["meta"]["schema_version"] == 2
    assert migrate(out) == out  # already v2
    scene.load_dict(out)
    assert scene.to_dict() == out
