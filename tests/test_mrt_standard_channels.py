"""
MRT Log standard channels (Qt-free): the lubrication system and the optional
groups choose known columns, as the Test Points table does; custom channels
and entered readings are never lost.
"""

from pumpflow.nodes.mechanical_run import (
    apply_standard_channels,
    build_log,
    standard_channels,
)


def _names(cols):
    return [c["name"] for c in cols]


def test_each_lubrication_brings_the_channels_its_rules_need():
    assert _names(standard_channels("pressurized")) == [
        "Flow", "Oil inlet", "Oil outlet DE", "Oil outlet NDE",
    ]
    assert _names(standard_channels("ring_oil")) == ["Flow", "Oil sump", "Ambient"]
    assert _names(standard_channels("oil_mist")) == [
        "Flow", "Housing DE", "Housing NDE", "Ambient",
    ]
    assert _names(standard_channels(None)) == ["Flow"]


def test_vibration_follows_the_pump_type_locations():
    oh6 = standard_channels(None, ("vibration",), "OH6")
    assert [(c["name"], c["role"]) for c in oh6[1:]] == [
        ("Gearbox overall", "vibration_unfiltered"),
        ("Gearbox filt.", "vibration_filtered"),
    ]
    bb = standard_channels(None, ("vibration",), "BB1")
    assert [c["location"] for c in bb[1:]] == ["DE", "DE", "NDE", "NDE"]


def test_apply_adopts_a_custom_channel_with_the_same_name_and_keeps_its_unit():
    settings = {
        "lubrication": "ring_oil",
        "columns": [
            {"name": "Flow", "dimension": "capacity", "unit": "gal/min", "role": "flow"},
            {"name": "Seal", "dimension": "pressure", "unit": "psi", "role": "seal_pressure"},
        ],
        "rows": [{"time": "06:00", "values": {"Flow": 43.5, "Seal": 69.0}}],
    }
    cols = apply_standard_channels(settings)
    assert _names(cols) == ["Flow", "Oil sump", "Ambient", "Seal"]
    flow = cols[0]
    assert flow["key"] == "flow" and flow["unit"] == "gal/min"
    assert "key" not in cols[-1]  # custom channel untouched, after the standard ones


def test_unwanted_standard_channel_is_dropped_unless_it_holds_readings():
    settings = {"lubrication": "pressurized", "columns": [], "rows": []}
    settings["columns"] = apply_standard_channels(settings)
    settings["rows"] = [{"time": "06:00", "values": {"Oil outlet DE": 60.0}}]
    settings["lubrication"] = "ring_oil"
    names = _names(apply_standard_channels(settings))
    assert "Oil outlet DE" in names  # has a reading: kept
    assert "Oil inlet" not in names and "Oil outlet NDE" not in names
    assert "Oil sump" in names


def test_build_log_carries_lubrication_and_locations():
    settings = {"lubrication": "pressurized", "rows": [
        {"time": "06:00", "values": {}}, {"time": "06:15", "values": {}},
    ]}
    settings["columns"] = apply_standard_channels(settings)
    log = build_log(settings)
    assert log.lubrication == "pressurized"
    assert {c.name: c.location for c in log.channels}["Oil outlet NDE"] == "NDE"
    assert build_log({"lubrication": "bogus", "columns": [], "rows": []}).lubrication is None


# --------------------------------------------------------------------------- #
# Web boundary and report rows
# --------------------------------------------------------------------------- #
def test_webapi_offers_lubrication_groups_and_the_desktop_channel_rule():
    import json

    from pumpflow import webapi

    opts = webapi.mrt_options()
    assert ["pressurized", "Pressurized (forced-feed)"] in opts["lubrication"]
    assert [g for g, _ in opts["channel_groups"]][0] == "vibration"
    assert opts["role_dimensions"]["oil_outlet_temperature"] == "temperature"
    cols = webapi.mrt_standard_channels(
        {"lubrication": "pressurized", "channel_groups": ["vibration"], "columns": [],
         "rows": []},
        "OH6",
    )
    assert [c["name"] for c in cols][:3] == ["Flow", "Gearbox overall", "Gearbox filt."]
    json.dumps(cols, allow_nan=False)


def _pressurized_doc(lubrication="pressurized"):
    """A minimal graph: an MRT Log (pressurized oil) into an MRT Check."""
    from pumpflow import webapi

    log = webapi.default_settings("mechanical_run")
    runtime = webapi.decode_settings("mechanical_run", log)
    runtime["lubrication"] = lubrication
    runtime["columns"] = apply_standard_channels(
        {**runtime, "columns": [], "channel_groups": ["vibration"]}, "OH6"
    )
    names = [c["name"] for c in runtime["columns"]]
    times = [f"{6 + i // 4:02d}:{15 * (i % 4):02d}" for i in range(17)]
    values = {"Flow": 10.0, "Gearbox overall": 1.5, "Gearbox filt.": 1.0,
              "Oil inlet": 40.0, "Oil outlet DE": 62.0, "Oil outlet NDE": 66.0}
    runtime["rows"] = [
        {"time": t, "values": {n: values.get(n) for n in names}} for t in times
    ]
    return {
        "nodes": [
            {"id": "log", "kind": "mechanical_run", "x": 0, "y": 0,
             "settings": webapi.encode_settings("mechanical_run", runtime)},
            {"id": "chk", "kind": "mechanical_run_check", "x": 300, "y": 0,
             "settings": webapi.default_settings("mechanical_run_check")},
        ],
        "edges": [{"src_node": "log", "src_port": "MechanicalRunSet",
                   "dst_node": "chk", "dst_port": "MechanicalRunSet"}],
    }


def test_mrt_check_view_lists_the_rules():
    from pumpflow import webapi

    out = webapi.evaluate(_pressurized_doc())
    view = out["nodes"]["chk"]["view"]
    assert view["lubrication"] == "pressurized"
    rise = next(r for r in view["rules"] if r["key"] == "oil_rise_max")
    assert rise["status"] == "pass" and rise["value"]["value"] == 26.0
    assert out["nodes"]["log"]["status"].endswith("pressurized (forced-feed)")


def test_report_table_carries_the_rule_rows_and_notes():
    from pump import Q_
    from pump.mechanical_run import RuleResult
    from pump.utilities.report import mechanical_run_notes, mechanical_run_table

    class R:
        channels = ()
        lubrication = "ring_oil"
        source = ""
        verified = True
        rules = (
            RuleResult("sump_rise_max", "Oil sump rise above ambient", None,
                       Q_(40, "delta_degC"), "not evaluated",
                       "needs oil sump and ambient temperature channels"),
        )

    _header, rows = mechanical_run_table(str, R())
    assert rows == [["Oil sump rise above ambient", "Δ°C", "-", "-", "≤ 40", "NOT EVALUATED"]]
    notes = mechanical_run_notes(str, R())
    assert notes[0] == "Bearing lubrication: Ring-oil / splash."
    assert notes[1].startswith("Oil sump rise above ambient: needs oil sump")
