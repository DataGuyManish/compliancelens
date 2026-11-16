import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compliancelens.quality.drift import diff_schemas


def test_added_column_is_low():
    events = diff_schemas("patients", {"a": "int"}, {"a": "int", "b": "string"})
    assert len(events) == 1 and events[0].change_type == "column_added"
    assert events[0].severity == "low"


def test_type_change_is_high():
    events = diff_schemas("patients", {"age": "int"}, {"age": "string"})
    assert events[0].change_type == "type_changed" and events[0].severity == "high"


def test_dropped_column_is_critical():
    events = diff_schemas("patients", {"age": "int", "x": "string"}, {"age": "int"})
    assert events[0].change_type == "column_removed" and events[0].severity == "critical"


def test_no_change_no_events():
    assert diff_schemas("patients", {"a": "INT"}, {"a": "int"}) == []
