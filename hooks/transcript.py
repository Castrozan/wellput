import json
import os


def _text_from_content_blocks(content, accepted_block_types):
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") in accepted_block_types
    ).strip()


def text_from_content(content, accepted_block_types=("text",)) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return _text_from_content_blocks(content, accepted_block_types)
    return ""


def _normalized_response_item_message(message):
    if message.get("type") != "message":
        return "", ""
    role = message.get("role", "")
    if role == "user":
        return role, text_from_content(
            message.get("content", ""), ("input_text", "text")
        )
    if role == "assistant":
        return role, text_from_content(
            message.get("content", ""), ("output_text", "text")
        )
    return "", ""


def normalized_transcript_message(transcript_event: dict) -> tuple[str, str]:
    event_kind = transcript_event.get("type")
    if event_kind in ("user", "assistant"):
        message = transcript_event.get("message", {})
        return event_kind, text_from_content(message.get("content", ""))
    if event_kind != "response_item":
        return "", ""
    message = transcript_event.get("payload", {})
    return _normalized_response_item_message(message)


def _transcript_event_from_line(transcript_line):
    transcript_line = transcript_line.strip()
    if not transcript_line:
        return False, None
    try:
        return True, json.loads(transcript_line)
    except json.JSONDecodeError:
        return False, None


def _is_hook_feedback(message_text):
    return message_text.startswith(("Stop hook feedback:", "<hook_prompt"))


def _updated_transcript_texts(
    role, message_text, current_turn_user_request, final_reply_text
):
    if role == "user":
        final_reply_text = ""
        if message_text and not _is_hook_feedback(message_text):
            current_turn_user_request = message_text
    elif role == "assistant" and message_text:
        final_reply_text = message_text
    return current_turn_user_request, final_reply_text


def read_final_turn_request_and_reply(transcript_path: str) -> tuple[str, str]:
    if not transcript_path or not os.path.exists(transcript_path):
        return "", ""
    current_turn_user_request = ""
    final_reply_text = ""
    with open(transcript_path, encoding="utf-8") as transcript_file:
        for transcript_line in transcript_file:
            event_is_valid, transcript_event = _transcript_event_from_line(
                transcript_line
            )
            if not event_is_valid:
                continue
            role, message_text = normalized_transcript_message(transcript_event)
            current_turn_user_request, final_reply_text = _updated_transcript_texts(
                role, message_text, current_turn_user_request, final_reply_text
            )
    return current_turn_user_request, final_reply_text


def final_turn_request_and_reply(hook_input: dict) -> tuple[str, str]:
    transcript_request, transcript_reply = read_final_turn_request_and_reply(
        hook_input.get("transcript_path", "")
    )
    user_request_text = hook_input.get("user_request_text", "") or transcript_request
    reply_text = (
        hook_input.get("reply_text", "")
        or hook_input.get("last_assistant_message", "")
        or transcript_reply
    )
    return user_request_text.strip(), reply_text.strip()
