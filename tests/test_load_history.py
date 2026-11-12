from datetime import UTC, datetime

from synthetic_ward.load_history import history_encounters, history_events, history_patients

CUTOFF = datetime(2026, 5, 1, tzinfo=UTC)

def test_patients_born_after_cutoff_are_left_for_the_simulator():
    rows = [
        {"id": "a", "birthdate": "1980-01-01", "deathdate": None},
        {"id": "b", "birthdate": "2026-06-01", "deathdate": None},
    ]
    assert [p["id"] for p in history_patients(rows, CUTOFF)] == ["a"]

def test_encounter_open_at_cutoff_is_in_progress():
    rows = [
        {"id": "done", "start": "2026-04-01T10:00:00Z", "stop": "2026-04-01T11:00:00Z"},
        {"id": "open", "start": "2026-04-30T22:00:00Z", "stop": "2026-05-03T09:00:00Z"},
        {"id": "future", "start": "2026-05-02T10:00:00Z", "stop": "2026-05-02T11:00:00Z"},
    ]
    result = {e["id"]: e for e in history_encounters(rows, CUTOFF)}
    assert set(result) == {"done", "open"}
    assert result["done"]["status"] == "finished"
    assert result["open"]["status"] == "in-progress"
    assert result["open"]["stop"] is None

def test_death_after_cutoff_is_removed():
    rows = [{"id": "a", "birthdate": "1940-01-01", "deathdate": "2026-07-01"}]
    assert next(history_patients(rows, CUTOFF))["deathdate"] is None

def test_events_only_from_finished_encounters():
    rows = [
        {"encounter": "done", "date": "2026-04-01T10:30:00Z"},
        {"encounter": "open", "date": "2026-04-30T23:00:00Z"},
        {"encounter": None, "date": "2026-04-15T00:00:00Z"},
        {"encounter": None, "date": "2026-06-15T00:00:00Z"}
    ]
    kept = list(history_events(rows, {"done"}, CUTOFF))
    assert kept == [rows[0], rows[2]]