from human_facing_reply_test_support import (
    labeled_reply_of,
    reply_with_label_content_word_counts,
    template_violations_in_reply,
)


def test_a_hundred_word_confirmation_needs_no_labels():
    reply = " ".join(["evidence"] * 100)

    assert template_violations_in_reply(reply) == []


def test_a_reply_past_the_confirmation_and_its_grace_names_the_labels_it_omits():
    violations = template_violations_in_reply(" ".join(["evidence"] * 111))

    assert violations == [
        "runs 111 prose words, past the 100-word confirmation, but omits the "
        "What is this session about?:/done:/next: label",
        "spends 111 prose words above the labels, past their own 80-word budget and "
        "its 10-word grace; move suitable detail into a short list, table, tree or "
        "diagram, which is not counted",
    ]


def test_a_reply_inside_the_confirmation_grace_still_needs_no_labels():
    assert template_violations_in_reply(" ".join(["evidence"] * 110)) == []


def test_a_partially_labeled_reply_names_only_the_missing_label():
    body = " ".join(["evidence"] * 80)
    session = " ".join(["evidence"] * 15)
    done = " ".join(["evidence"] * 14)
    reply = f"{body}\n\n**what is this session about?:** {session}\n\n**done:** {done}"

    violations = template_violations_in_reply(reply)

    assert violations == [
        "runs 115 prose words, past the 100-word confirmation, but omits the next: label"
    ]


def test_a_labeled_reply_within_both_budgets_passes():
    assert template_violations_in_reply(labeled_reply_of(40)) == []


def test_prose_above_the_labels_past_its_budget_and_grace_is_blocked():
    violations = template_violations_in_reply(labeled_reply_of(100))

    assert any("past their own 80-word budget" in violation for violation in violations)


def test_prose_above_the_labels_inside_the_grace_passes():
    violations = template_violations_in_reply(labeled_reply_of(90))

    assert not any(
        "past their own 80-word budget" in violation for violation in violations
    )


def test_labeled_sections_past_their_shared_budget_and_grace_are_blocked():
    reply = reply_with_label_content_word_counts(session=25, done=20, next_block=20)

    violations = template_violations_in_reply(reply)

    assert any("50-word budget" in violation for violation in violations)


def test_labeled_sections_inside_the_shared_grace_pass():
    reply = reply_with_label_content_word_counts(session=20, done=20, next_block=20)

    violations = template_violations_in_reply(reply)

    assert not any("50-word budget" in violation for violation in violations)


def test_label_headings_do_not_consume_the_label_content_budgets():
    body = "context " * 91
    labels = reply_with_label_content_word_counts(session=30, done=15, next_block=15)

    assert template_violations_in_reply(f"{body}\n\n{labels}") == [
        "spends 91 prose words above the labels, past their own 80-word budget and "
        "its 10-word grace; move suitable detail into a short list, table, tree or "
        "diagram, which is not counted"
    ]


def test_label_content_past_its_own_budget_is_still_counted():
    body = "context " * 91
    labels = reply_with_label_content_word_counts(session=31, done=14, next_block=15)

    assert template_violations_in_reply(f"{body}\n\n{labels}") == [
        "spends 31 words of content on the What is this session about?: block, past "
        "its 25-word budget and its 5-word grace",
        "spends 91 prose words above the labels, past their own 80-word budget and "
        "its 10-word grace; move suitable detail into a short list, table, tree or "
        "diagram, which is not counted",
    ]


def test_one_label_past_its_own_budget_and_grace_is_blocked():
    reply = reply_with_label_content_word_counts(session=10, done=26, next_block=5)

    assert template_violations_in_reply(reply) == [
        "spends 26 words of content on the done: block, past its 20-word budget and "
        "its 5-word grace"
    ]


def test_one_label_inside_its_own_grace_passes():
    reply = reply_with_label_content_word_counts(session=10, done=25, next_block=5)

    assert template_violations_in_reply(reply) == []
