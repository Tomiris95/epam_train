"""
Prompt injection and jailbreak filter for chat messages.
Runs before every ConversationalAgent call — the LLM never sees blocked input.
"""
import re
from typing import Tuple

MAX_MESSAGE_LENGTH = 500

# Common prompt-injection / jailbreak patterns
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|prior|your)\s+instructions?",
    r"forget\s+(your|all|previous|prior)",
    r"you\s+are\s+now\s+(a|an)",
    r"act\s+as\s+(if\s+you\s+are|a|an)",
    r"new\s+(instructions?|rules?|prompt|role)",
    r"override\s+(your|the)\s+(instructions?|rules?|prompt|guidelines?)",
    r"disregard\s+(all|your|previous|prior)",
    r"(ignore|bypass|skip)\s+(safety|guidelines?|rules?|restrictions?|filters?)",
    r"jailbreak",
    r"system\s*prompt",
    r"you\s+are\s+no\s+longer",
    r"pretend\s+you\s+(are|have\s+no)",
    r"do\s+anything\s+now",
    r"dan\s+mode",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def check_message(message: str) -> Tuple[bool, str]:
    """
    Returns (is_safe, rejection_reason).
    is_safe=True means the message is OK to send to the LLM.
    """
    if not message or not message.strip():
        return False, "Message cannot be empty."

    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message too long ({len(message)} chars, max {MAX_MESSAGE_LENGTH})."

    for pattern in _COMPILED:
        if pattern.search(message):
            return False, "Message contains disallowed content."

    return True, ""
