import json
import sys

import pytest

STATUS_TABLE = "\n".join(
    [
        "### Sessions",
        "",
        "| # | Session | State | This round |",
        "|---|---|---|---|",
        *(
            f"| {index} | Servant{index} | working | ported step {index} |"
            for index in range(1, 9)
        ),
        "",
        "Full view: `status show <session>`",
    ]
)
REPLY = f"The rebuild passed.\n\n{STATUS_TABLE}"


def claude_events(tool_output, request="Rebuild and show the round."):
    return [
        {"type": "user", "message": {"content": request}},
        {
            "type": "user",
            "message": {
                "content": [{"type": "tool_result", "content": tool_output}],
            },
        },
    ]


def codex_events(tool_output):
    return [
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Rebuild and show it."}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "output": [
                    {"type": "input_text", "text": "Script completed\nOutput:\n"},
                    {"type": "input_text", "text": tool_output},
                ],
            },
        },
    ]


def stop(invoke, tmp_path, events, reply=REPLY):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(event) for event in events))
    return invoke(
        {
            "hook_event_name": "Stop",
            "transcript_path": str(transcript),
            "last_assistant_message": reply,
        }
    )


def test_an_oversized_table_written_by_hand_is_blocked(invoke, tmp_path):
    output = stop(invoke, tmp_path, claude_events("rebuild ok"))
    assert output["decision"] == "block"


@pytest.mark.parametrize("events", [claude_events, codex_events])
def test_a_table_relayed_verbatim_from_this_turns_tool_output_passes(
    invoke, tmp_path, events
):
    assert stop(invoke, tmp_path, events(f"{STATUS_TABLE}\n")) == {}


def test_trailing_spaces_in_the_tool_output_still_count_as_verbatim(invoke, tmp_path):
    padded = "\n".join(f"{line}   " for line in STATUS_TABLE.splitlines())
    assert stop(invoke, tmp_path, claude_events(padded)) == {}


def test_output_from_an_earlier_turn_is_not_evidence_for_this_reply(invoke, tmp_path):
    events = [*claude_events(STATUS_TABLE), *claude_events("ok", "Show it again.")]
    assert stop(invoke, tmp_path, events)["decision"] == "block"


def test_an_edited_relay_is_judged_as_written(invoke, tmp_path):
    edited = REPLY.replace("Session |", "Peer |").replace("working", "busy")
    output = stop(invoke, tmp_path, claude_events(STATUS_TABLE), edited)
    assert output["decision"] == "block"


def test_prose_around_the_relay_still_counts(invoke, tmp_path):
    prose = " ".join(["word"] * 120)
    output = stop(invoke, tmp_path, claude_events(STATUS_TABLE), f"{prose}\n\n{REPLY}")
    assert output["decision"] == "block"


def test_a_relay_containing_a_fence_stays_one_fenced_span(plugin_root):
    sys.path.insert(0, str(plugin_root / "hooks/rules"))
    from reply_relayed_output import reply_with_relayed_output_fenced

    relayed = "one\n```\ntwo\n```\nthree"
    fenced = reply_with_relayed_output_fenced(f"intro\n{relayed}", [relayed])
    assert fenced == f"intro\n````\n{relayed}\n````"
