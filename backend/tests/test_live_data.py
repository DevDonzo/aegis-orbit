from __future__ import annotations

import core.live_data as live_data


def test_live_data_fallback_to_sample(monkeypatch) -> None:
    monkeypatch.setattr(live_data, "_read_cache", lambda: None)
    monkeypatch.setattr(
        live_data,
        "_fetch_live_records",
        lambda catnr_list, group: (_ for _ in ()).throw(RuntimeError("network down")),
    )

    records, status = live_data.load_satellite_records(refresh=True, catnr_list=[25544])
    assert len(records) > 0
    assert status["mode"] == "sample"
    assert status["note"]
