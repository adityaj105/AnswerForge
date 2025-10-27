# answerforge/verifier/verifier.py
from typing import Dict, Optional, List, Any, Tuple
from .static_checks import looks_safe_python
from .docker_sandbox import run_in_docker
import textwrap

# -------------------------
# Helpers
# -------------------------
def make_executable_snippet(code: str) -> str:
    """
    Light-weight wrapper to make short snippets executable.
    - If it's a single-line expression (no newline), try printing it.
    - Ensure trailing newline for safety.
    """
    code = code.rstrip() + "\n"
    if "\n" not in code.strip():
        # single-line expression -> print it so we capture output
        return f"print({code.strip()})\n"
    return code

# Internal: runs static checks then executes code in docker
def _verify_single(code: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Run static checks + Docker execution on one snippet.
    Returns a dict: { "verified": bool, "reason": str, "details": {...} }
    """
    safe, matches = looks_safe_python(code)
    if not safe:
        return {"verified": False, "reason": "static_blacklist_match", "matches": matches}

    # wrap small fragments to be runnable
    payload = make_executable_snippet(code)

    res = run_in_docker(payload, timeout=timeout)
    if res.get("ok"):
        return {"verified": True, "reason": "docker_passed", "details": res}
    else:
        return {"verified": False, "reason": "docker_failed", "details": res}

# -------------------------
# Public verifier API
# -------------------------
def verify_python(code: Any, timeout: int = 5) -> Dict[str, Any]:
    """
    Verify Python code. Accepts:
      - a single code string -> verifies it and returns result
      - a list of code strings -> tries each block in order and returns the first verified one
    Return structure:
      {
        "verified": bool,
        "reason": str,
        "details": { ... }   # if single: direct details; if list: contains "tried_blocks": [...]
      }
    """
    # If a single string, run directly
    if isinstance(code, str):
        return _verify_single(code, timeout=timeout)

    # If a list/iterable, try each block until one verifies
    tried: List[Dict[str, Any]] = []
    blocks = list(code)
    for idx, blk in enumerate(blocks):
        entry: Dict[str, Any] = {"index": idx, "skipped": False, "verified": False, "reason": None, "details": None}
        if not blk or len(blk.strip()) < 6:
            entry.update({"skipped": True, "reason": "too_short"})
            tried.append(entry)
            continue

        try:
            res = _verify_single(blk, timeout=timeout)
        except Exception as e:
            entry.update({"verified": False, "reason": "exception_in_verifier", "details": {"error": str(e)}})
            tried.append(entry)
            continue

        entry.update({
            "verified": bool(res.get("verified", False)),
            "reason": res.get("reason"),
            "details": res.get("details"),
        })
        tried.append(entry)

        if res.get("verified"):
            # success: return with tried list + success details
            return {
                "verified": True,
                "reason": res.get("reason"),
                "details": {
                    "tried_blocks": tried,
                    **(res.get("details", {}) or {})
                }
            }

    # none verified
    return {"verified": False, "reason": "no_block_verified", "details": {"tried_blocks": tried}}
