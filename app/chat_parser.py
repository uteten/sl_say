import re
from dataclasses import dataclass

from app.filter_config import FilterConfig

SYSTEM_SPEAKERS = {"Second Life", "Firestorm"}

_PARENS_RE = re.compile(r"\s*\([^)]*\)")
_PARENS_EXTRACT_RE = re.compile(r"\(([^)]+)\)")

CHAT_LINE_RE = re.compile(
    r"^\[(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}(?::\d{2})?)\]\s{2}(.+)$"
)

SPEAK_RE = re.compile(
    r"^(.+?)(?:\s+(shouts|whispers))?:\s(.*)$"
)


@dataclass
class ChatMessage:
    speaker: str
    body: str
    message_type: str  # "say" | "shout" | "whisper" | "emote"


class ChatParser:
    def __init__(self, filter_config: FilterConfig | None = None) -> None:
        self._filter = filter_config or FilterConfig()

    def parse_line(self, line: str) -> ChatMessage | None:
        line = line.strip()
        if not line:
            return None

        match = CHAT_LINE_RE.match(line)
        if not match:
            return None

        content = match.group(3)

        speak_match = SPEAK_RE.match(content)
        if speak_match:
            speaker = speak_match.group(1)
            modifier = speak_match.group(2)
            body = speak_match.group(3)

            if speaker in SYSTEM_SPEAKERS:
                return None

            if body in ("はオンラインです。", "はオフラインです。"):
                return None

            parens_match = _PARENS_EXTRACT_RE.search(speaker)
            exclude_target = parens_match.group(1) if parens_match else speaker
            if self._filter.should_exclude_speaker(exclude_target):
                return None

            if self._filter.should_exclude_body(body):
                return None

            if modifier == "shouts":
                message_type = "shout"
            elif modifier == "whispers":
                message_type = "whisper"
            else:
                message_type = "say"

            speaker = _PARENS_RE.sub("", speaker).strip()
            return ChatMessage(speaker=speaker, body=body, message_type=message_type)

        # Emote: no colon pattern — SL avatar names are typically "First Last"
        parts = content.split(" ", 2)
        if len(parts) >= 3:
            speaker = f"{parts[0]} {parts[1]}"
            body = parts[2]
            return ChatMessage(speaker=speaker, body=body, message_type="emote")
        elif len(parts) == 2:
            return ChatMessage(speaker=parts[0], body=parts[1], message_type="emote")
        elif len(parts) == 1:
            return ChatMessage(speaker=parts[0], body="", message_type="emote")

        return None
