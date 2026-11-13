from datetime import UTC, datetime

from synthetic_ward.simulator import build_events

CUTOFF = datetime(2026, 5, 1, tzinfo=UTC)

def enc(id, start, stop):
    return {"id": id, "start": start, "stop": stop, "patient": "p1"}

def test_future_encounter_is_admitted_then_discharged():
    events = build_events([], [enc("e1", "2026-06-01T10:00:00Z", "2026-06-01T11:00:00Z")], {}, CUTOFF)
    assert [(e.kind, e.row["id"]) for e in events] == [("admit", "e1"), ("discharge", "e1")]
    assert events[0].row["status"] == "in-progress"
    assert events[0].row["stop"] is None

def test_encounter_open_at_cutoff_is_only_discharged():
    events = build_events([], [enc("e1", "2026-04-30T22:00:00Z", "2026-05-02T09:00:00Z")], {}, CUTOFF)
    assert [e.kind for e in events] == ["discharge"]

def test_history_encounters_and_their_rows_are_skipped():
    encounters = [
        enc("in_history", "2026-04-01T10:00:00Z", "2026-04-01T11:00:00Z"),
        enc("in_replay", "2026-06-01T10:00:00Z", "2026-06-01T11:00:00Z"),
    ]
    observations = [
        {"encounter": "in_history", "date": "2026-04-01T10:30:00Z"},
        {"encounter": "in_replay", "date": "2026-06-01T10:30:00Z"},
    ]
    events = build_events([], encounters, {"observations": observations}, CUTOFF)
    assert len(events) == 2  # admit + discharge for in_replay only
    discharge = events[1]
    assert discharge.row["id"] == "in_replay"
    assert discharge.charts == [("observations", observations[1])]
    
def test_births_and_deaths_after_cutoff():
    patients = [
        {"id": "born_in_replay", "birthdate": "2026-06-01", "deathdate": None},
        {"id": "died_in_replay", "birthdate": "1940-01-01", "deathdate": "2026-07-01"},
        {"id": "died_in_history", "birthdate": "1930-01-01", "deathdate": "2020-01-01"},
    ]
    events = build_events(patients, [], {}, CUTOFF)
    assert [(e.kind, e.row["id"]) for e in events] == [
        ("birth", "born_in_replay"), 
        ("death", "died_in_replay")]