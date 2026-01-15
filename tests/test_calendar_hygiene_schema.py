import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from tools.calendar_hygiene import calendar_hygiene  # noqa: E402


def test_build_plan_schema():
    events = [
        calendar_hygiene.Event(
            event_id="evt-1",
            title="Medical appointment",
            start=datetime.now(timezone.utc),
            end=datetime.now(timezone.utc),
            description="",
        )
    ]
    plan = calendar_hygiene.build_plan(
        events=events,
        time_window={
            "start": datetime.now(timezone.utc).isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
        },
        calendar_id="primary",
        data_source="mock",
        errors=[],
        actions=[
            {
                "action_id": "act-test",
                "type": "create_block",
                "start": datetime.now(timezone.utc).isoformat(),
                "end": datetime.now(timezone.utc).isoformat(),
                "title": "Daily planning/admin",
                "reason": "Test",
                "reasoning": "Test",
                "confidence": 0.5,
                "risk": "low",
            }
        ],
    )

    assert plan["schema_version"] == 1
    assert plan["plan_id"]
    assert "summary" in plan
    assert "result" in plan
    assert "next_actions" in plan
    assert "errors" in plan
    assert isinstance(plan["proposed_actions"], list)
    json.dumps(plan)
