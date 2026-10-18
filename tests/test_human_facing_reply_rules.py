import json

from human_facing_reply_test_support import (
    LABELED_REPLY,
    template_violations_in_reply,
)


def test_raw_json_preserves_its_schema_without_conversational_labels():
    reply = json.dumps({"summary": "evidence " * 120, "source": "PR #17"})

    assert template_violations_in_reply(reply) == []


def test_a_standalone_table_preserves_its_column_schema():
    reply = "| Name | Value |\n| --- | --- |\n| timeout | 30 |"

    assert template_violations_in_reply(reply) == []


def test_a_standalone_answer_word_is_not_a_reaction_preamble():
    for reply in ("Absolutely", "Absolutely.", "**Absolutely**"):
        assert template_violations_in_reply(reply) == []


def test_a_table_is_exempt_from_the_word_count():
    header = "| # | " + " | ".join(["Column"] * 24) + " |\n"
    separator = "| " + " | ".join(["---"] * 25) + " |\n"
    table_rows = "\n".join(
        f"| {number} | " + " | ".join(["measured"] * 24) + " |"
        for number in range(1, 6)
    )
    reply = f"{header}{separator}{table_rows}\n\n{LABELED_REPLY}"

    assert template_violations_in_reply(reply) == []


def test_a_tree_or_diagram_is_exempt_from_the_word_count():
    tree_lines = "\n".join(["├── one module owning one measured responsibility"] * 40)
    reply = f"{LABELED_REPLY}\n\n{tree_lines}"

    assert template_violations_in_reply(reply) == []


def test_a_list_past_five_items_is_blocked():
    reply = "\n".join(["- one finding"] * 6) + f"\n\n{LABELED_REPLY}"

    violations = template_violations_in_reply(reply)

    assert violations == ["stacks 6 list items, past the 5-item ceiling for one list"]


def test_a_list_line_past_twenty_words_and_its_grace_is_blocked():
    long_line = "- " + " ".join(["evidence"] * 25)
    reply = f"{long_line}\n\n{LABELED_REPLY}"

    violations = template_violations_in_reply(reply)

    assert violations == [
        "runs a 26-word list item, past the 20-word ceiling and its 5-word grace "
        "for one item"
    ]


def test_five_short_list_lines_pass():
    reply = "\n".join(["- one finding"] * 5) + f"\n\n{LABELED_REPLY}"

    assert template_violations_in_reply(reply) == []


def test_a_label_without_bold_emphasis_is_blocked():
    context = " ".join(["evidence"] * 65)
    reply = (
        f"{context}\n\n"
        "what is this session about?: the release gate that decides whether the "
        "candidate policy ships.\n\n"
        "done: measured the candidate against the control across three epochs and "
        "recorded the paired interval.\n\n"
        "next: commit the refreshed baseline, then let the steward reconcile the "
        "diverged branch on its own loop."
    )

    assert template_violations_in_reply(reply) == [
        "writes the What is this session about?: label without bold emphasis"
    ]


def test_labels_crammed_into_one_block_are_blocked():
    context = " ".join(["evidence"] * 65)
    reply = (
        f"{context}\n\n"
        "**what is this session about?:** the release gate that decides whether the "
        "candidate policy ships.\n"
        "**done:** measured the candidate against the control across three epochs and "
        "recorded the paired interval.\n"
        "**next:** commit the refreshed baseline, then let the steward reconcile the "
        "diverged branch on its own loop."
    )

    assert template_violations_in_reply(reply) == [
        "runs the done: label into the line above it instead of starting its own block"
    ]


def test_a_label_word_inside_a_fence_is_not_a_reply_label():
    reply = (
        "The log line reads:\n```\nnext: retry scheduled\n```\nNothing else changed."
    )

    assert template_violations_in_reply(reply) == []
