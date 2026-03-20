"""
Security utilities for Bundlescope.

Includes:
- Path traversal protection
- Input sanitization
- File validation
- Rate limiting helpers
"""

from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("bundlescope")

# ─── Path Traversal Protection ───

def safe_resolve_path(root: str, user_path: str) -> Optional[str]:
    """
    Safely resolve a user-provided relative path within a root directory.
    Returns the resolved path if safe, or None if the path escapes the root.
    """
    try:
        root_resolved = Path(root).resolve()
        # Normalize the user path to prevent ../ attacks
        joined = (root_resolved / user_path).resolve()
        # Ensure the resolved path is within the root
        if not str(joined).startswith(str(root_resolved)):
            logger.warning(
                "Path traversal attempt blocked: root=%s, path=%s, resolved=%s",
                root, user_path, joined,
            )
            return None
        return str(joined)
    except (ValueError, OSError) as e:
        logger.warning("Path resolution error: %s", e)
        return None


# ─── Input Sanitization ───

# Control characters (except newline, tab) that have no business in user input
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Common prompt injection markers
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(previous|above|all)\s+instructions"
    r"|you\s+are\s+now\s+in"
    r"|system:\s*override"
    r"|<\|im_start\|>"
    r"|<\|endoftext\|>)",
    re.IGNORECASE,
)


def sanitize_chat_input(message: str, max_length: int = 4000) -> str:
    """
    Sanitize user chat input:
    - Strip control characters
    - Enforce max length
    - Log suspicious patterns (but don't block — log and let LLM handle)
    """
    # Remove control characters
    cleaned = _CONTROL_CHARS.sub("", message)
    # Truncate
    cleaned = cleaned[:max_length].strip()

    if _INJECTION_PATTERNS.search(cleaned):
        logger.warning("Potential prompt injection detected in chat input: %.100s...", cleaned)

    return cleaned


# ─── File Validation ───

ALLOWED_EXTENSIONS = (".tar.gz", ".tgz")
MAX_FILENAME_LENGTH = 255
_SAFE_FILENAME = re.compile(r"^[a-zA-Z0-9._\-]+$")


def validate_upload_filename(filename: Optional[str]) -> Optional[str]:
    """
    Validate an upload filename. Returns sanitized filename or None if invalid.
    """
    if not filename:
        return None

    # Basic length check
    if len(filename) > MAX_FILENAME_LENGTH:
        return None

    # Must have allowed extension
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return None

    # Strip any path components — only the basename matters
    basename = os.path.basename(filename)
    if not basename:
        return None

    # Must be safe characters only
    if not _SAFE_FILENAME.match(basename):
        # Replace unsafe chars
        basename = re.sub(r"[^a-zA-Z0-9._\-]", "_", basename)

    return basename


# ─── UUID Validation ───

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID v4 format."""
    return bool(_UUID_PATTERN.match(value))
