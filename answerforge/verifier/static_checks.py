# answerforge/verifier/static_checks.py
import re
from typing import Tuple, List

# Simple blacklist regexes for common dangerous patterns
BLACKLIST = [
    r"\bos\.system\s*\(",      # os.system(...)
    r"\bsubprocess\.",        # subprocess.* (Popen, run, etc.)
    r"\beval\s*\(",           # eval(...)
    r"\bexec\s*\(",           # exec(...)
    r"\bopen\s*\(.+['\"]w['\"]",  # open(..., 'w') write to file
    r"\brequests\.",          # outbound HTTP via requests
    r"\burllib\.",            # urllib usage
    r"\bsocket\.",            # raw sockets
]

def looks_safe_python(code: str) -> Tuple[bool, List[str]]:
    """
    Returns (is_safe, matched_patterns).
    If matched_patterns non-empty => unsafe.
    """
    matches = []
    for p in BLACKLIST:
        if re.search(p, code):
            matches.append(p)
    return (len(matches) == 0, matches)
