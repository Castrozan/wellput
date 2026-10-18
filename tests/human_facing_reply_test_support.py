import sys
from pathlib import Path

REPLY_RULE_MODULE_DIRECTORY = Path(__file__).resolve().parents[1] / "hooks/rules"
sys.path.insert(0, str(REPLY_RULE_MODULE_DIRECTORY))
sys.path.insert(0, str(REPLY_RULE_MODULE_DIRECTORY.parent / "vendor"))

from reply_rule_catalog import template_violations_in_reply
from reply_rule_feedback import bounce_guidance

LABELED_REPLY = (
    "**what is this session about?:** the release gate.\n\n"
    "**done:** measured the candidate.\n\n"
    "**next:** push."
)


def labeled_reply_of(body_words: int) -> str:
    body = " ".join(["evidence"] * body_words)
    return f"{body}\n\n{LABELED_REPLY}"


def reply_with_label_content_word_counts(
    session: int, done: int, next_block: int
) -> str:
    def block(label: str, words: int) -> str:
        filler = " ".join(["evidence"] * words)
        return f"**{label}** {filler}".strip()

    return "\n\n".join(
        (
            block("what is this session about?:", session),
            block("done:", done),
            block("next:", next_block),
        )
    )
