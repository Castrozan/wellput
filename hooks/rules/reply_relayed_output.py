import re

MINIMUM_RELAYED_LINES = 3


def normalized_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines()]


def bounded_outputs(tool_outputs) -> list[str]:
    return [f"\n{chr(10).join(normalized_lines(output))}\n" for output in tool_outputs]


def is_relayed(lines: list[str], outputs: list[str]) -> bool:
    span = f"\n{chr(10).join(lines)}\n"
    return any(span in output for output in outputs)


def relayed_span_end(lines: list[str], start: int, outputs: list[str]) -> int:
    end = start
    while end < len(lines) and is_relayed(lines[start : end + 1], outputs):
        end += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return end


def fenced(lines: list[str]) -> list[str]:
    backtick_runs = re.findall(r"`+", "\n".join(lines))
    longest_backtick_run = max((len(run) for run in backtick_runs), default=0)
    fence = "`" * max(3, longest_backtick_run + 1)
    return [fence, *lines, fence]


def counts_as_relayed(span: list[str]) -> bool:
    return sum(1 for line in span if line.strip()) >= MINIMUM_RELAYED_LINES


def reply_with_relayed_output_fenced(reply_text: str, tool_outputs) -> str:
    outputs = bounded_outputs(output for output in tool_outputs if output.strip())
    if not outputs:
        return reply_text
    lines = normalized_lines(reply_text)
    reviewed = []
    start = 0
    while start < len(lines):
        end = relayed_span_end(lines, start, outputs) if lines[start].strip() else start
        if counts_as_relayed(lines[start:end]):
            reviewed += fenced(lines[start:end])
            start = end
        else:
            reviewed.append(lines[start])
            start += 1
    return "\n".join(reviewed)
