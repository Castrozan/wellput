import json
import subprocess
import sys

import pytest

from human_facing_reply_test_support import template_violations_in_reply

FIFTEEN_ROW_TABLE = "| # | Finding |\n| --- | --- |\n" + "\n".join(
    f"| {number} | finding-{number} |" for number in range(1, 16)
)


@pytest.mark.parametrize(
    "user_request,exempt",
    [
        ("show the 15 findings as a table", True),
        ("Tables, please", True),
        ("monte uma tabela com tudo", True),
        ("list every finding", False),
        ("check the timetable", False),
    ],
)
def test_a_table_request_lifts_the_row_ceiling(user_request, exempt):
    violations = template_violations_in_reply(
        FIFTEEN_ROW_TABLE, user_request=user_request
    )

    assert (violations == []) == exempt


def test_a_table_request_keeps_the_index_column_rule():
    reply = "Summary:\n\n| Finding |\n| --- |\n" + "\n".join(
        "| finding |" for _ in range(15)
    )

    violations = template_violations_in_reply(reply, user_request="as a table")

    assert any("index column" in item for item in violations)
    assert not any("data rows" in item for item in violations)


def user_event(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def assistant_event(text):
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def stop_hook_output(plugin_root, tmp_path, events):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(event) for event in events))
    payload = {
        "hook_event_name": "Stop",
        "last_assistant_message": events[-1]["message"]["content"][0]["text"],
        "transcript_path": str(transcript),
    }
    result = subprocess.run(
        [sys.executable, "-S", str(plugin_root / "hooks/reply_hook.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
        cwd="/",
        check=True,
    )
    return json.loads(result.stdout)


def test_stop_hook_accepts_a_long_table_the_user_asked_for(plugin_root, tmp_path):
    events = [user_event("one table, please"), assistant_event(FIFTEEN_ROW_TABLE)]

    assert stop_hook_output(plugin_root, tmp_path, events) == {}


@pytest.mark.parametrize(
    "hook_feedback",
    [
        "Stop hook feedback:\nReply breaks the enforced interactive rules "
        "(table 1 has 15 data rows, past its 5-row ceiling).",
        '<hook_prompt hook_run_id="stop:1">table 1 has 15 data rows</hook_prompt>',
    ],
)
def test_hook_feedback_naming_a_table_is_not_a_table_request(
    plugin_root, tmp_path, hook_feedback
):
    events = [
        user_event("list every finding"),
        assistant_event(FIFTEEN_ROW_TABLE),
        user_event(hook_feedback),
        assistant_event(FIFTEEN_ROW_TABLE),
    ]

    output = stop_hook_output(plugin_root, tmp_path, events)

    assert output["decision"] == "block"
    assert "data rows" in output["reason"]
