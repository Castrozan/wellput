import json
import os
from dataclasses import dataclass, field


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


TOOL_OUTPUT_PAYLOAD_TYPES = ("function_call_output", "custom_tool_call_output")
TOOL_OUTPUT_TEXT_TYPES = ("input_text", "output_text", "text")


@dataclass
class FinalTurn:
    request: str = ""
    reply: str = ""
    tool_outputs: list[str] = field(default_factory=list)

    def record(self, role, message_text):
        if role == "user":
            self.reply = ""
            if message_text and not _is_hook_feedback(message_text):
                self.request = message_text
                self.tool_outputs = []
        elif role == "assistant" and message_text:
            self.reply = message_text


def _codex_tool_output(output) -> str:
    if isinstance(output, str):
        try:
            decoded = json.loads(output)
        except json.JSONDecodeError:
            return output
        return decoded.get("output", output) if isinstance(decoded, dict) else output
    return text_from_content(output, TOOL_OUTPUT_TEXT_TYPES)


def tool_outputs_in_event(transcript_event: dict) -> list[str]:
    if transcript_event.get("type") == "response_item":
        payload = transcript_event.get("payload", {})
        if payload.get("type") in TOOL_OUTPUT_PAYLOAD_TYPES:
            return [_codex_tool_output(payload.get("output", ""))]
        return []
    content = transcript_event.get("message", {}).get("content", "")
    if transcript_event.get("type") != "user" or not isinstance(content, list):
        return []
    return [
        text_from_content(block.get("content", ""), TOOL_OUTPUT_TEXT_TYPES)
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_result"
    ]


def read_final_turn(transcript_path: str) -> FinalTurn:
    turn = FinalTurn()
    if not transcript_path or not os.path.exists(transcript_path):
        return turn
    with open(transcript_path, encoding="utf-8") as transcript_file:
        for transcript_line in transcript_file:
            event_is_valid, transcript_event = _transcript_event_from_line(
                transcript_line
            )
            if not event_is_valid or not isinstance(transcript_event, dict):
                continue
            turn.record(*normalized_transcript_message(transcript_event))
            turn.tool_outputs += tool_outputs_in_event(transcript_event)
    return turn


def final_turn(hook_input: dict) -> FinalTurn:
    turn = read_final_turn(hook_input.get("transcript_path", ""))
    request = hook_input.get("user_request_text", "") or turn.request
    reply = (
        hook_input.get("reply_text", "")
        or hook_input.get("last_assistant_message", "")
        or turn.reply
    )
    return FinalTurn(request.strip(), reply.strip(), turn.tool_outputs)
