"""
StackOverflow retriever utilities for AnswerForge.
Uses Stack Exchange API (no auth required for small volumes).

Key features:
 - Smart caching for repeated queries
 - Graceful timeouts and retries
 - Prioritizes accepted & high-voted answers
 - Extracts clean, useful code snippets
"""

import time
import requests
from typing import List, Dict
from bs4 import BeautifulSoup

STACK_API_BASE = "https://api.stackexchange.com/2.3"

# ----------------------------------------------------------
# Simple in-memory cache (with expiration)
# ----------------------------------------------------------
CACHE_TTL = 600  # seconds (10 minutes)
_cache = {}       # key -> (timestamp, data)


def _get_from_cache(key: str):
    entry = _cache.get(key)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts > CACHE_TTL:
        _cache.pop(key, None)
        return None
    return data


def _save_to_cache(key: str, data):
    _cache[key] = (time.time(), data)


# ----------------------------------------------------------
# Safe GET with retry, timeout, and backoff
# ----------------------------------------------------------
def _safe_get(url: str, params: dict, retries: int = 3, timeout: int = 10, backoff: float = 0.75) -> dict:
    """
    Perform a GET request with retry, timeout, and backoff handling.
    Automatically caches successful responses.
    """
    cache_key = f"{url}:{str(sorted(params.items()))}"
    cached = _get_from_cache(cache_key)
    if cached:
        print(f"[CACHE] Using cached response for {url}")
        return cached

    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            _save_to_cache(cache_key, data)
            return data
        except requests.exceptions.Timeout:
            print(f"[WARN] Timeout (attempt {attempt+1}/{retries}) for URL: {url}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request failed ({url}): {e}")
        time.sleep(backoff * (attempt + 1))

    print(f"[FAIL] All retries failed for URL: {url}")
    return {}


# ----------------------------------------------------------
# Search StackOverflow questions
# ----------------------------------------------------------
def search_stackoverflow(query: str, max_questions: int = 10) -> List[Dict]:
    """
    Search StackOverflow for relevant questions.
    Strategy:
      1) Try advanced search with accepted answers.
      2) Fallback to general relevance/votes search.
    """
    questions = []
    page_size = min(max_questions, 50)
    url = f"{STACK_API_BASE}/search/advanced"

    # Pass 1: accepted answers preferred
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "accepted": "True",
        "site": "stackoverflow",
        "pagesize": page_size,
    }
    data = _safe_get(url, params)
    for item in data.get("items", []):
        questions.append({
            "question_id": item.get("question_id"),
            "title": item.get("title"),
            "link": item.get("link"),
        })

    # Pass 2: fallback to most-voted if needed
    if len(questions) < max_questions:
        needed = max_questions - len(questions)
        params = {
            "order": "desc",
            "sort": "votes",
            "q": query,
            "site": "stackoverflow",
            "pagesize": min(needed, 50),
        }
        data = _safe_get(url, params)
        for item in data.get("items", []):
            questions.append({
                "question_id": item.get("question_id"),
                "title": item.get("title"),
                "link": item.get("link"),
            })

    # Deduplicate questions
    seen = set()
    result = []
    for q in questions:
        qid = q.get("question_id")
        if qid and qid not in seen:
            seen.add(qid)
            result.append(q)
        if len(result) >= max_questions:
            break

    print(f"[INFO] Found {len(result)} questions for query '{query}'")
    return result


# ----------------------------------------------------------
# Fetch answers for a given question
# ----------------------------------------------------------
def fetch_answers(question_id: int, max_answers: int = 10) -> List[Dict]:
    """
    Fetch answers for a StackOverflow question_id.
    Returns list of dicts:
      { 'answer_id', 'body' (HTML), 'is_accepted', 'score' }
    """
    url = f"{STACK_API_BASE}/questions/{question_id}/answers"
    params = {
        "order": "desc",
        "sort": "votes",
        "site": "stackoverflow",
        "filter": "withbody",
        "pagesize": min(max_answers, 100),
    }

    data = _safe_get(url, params, retries=3, timeout=10)
    items = data.get("items", [])
    answers = []

    for it in items:
        answers.append({
            "answer_id": it.get("answer_id"),
            "body": it.get("body", ""),
            "is_accepted": it.get("is_accepted", False),
            "score": it.get("score", 0),
        })

    # Sort: accepted first, then by score
    answers.sort(key=lambda a: (not a["is_accepted"], -a["score"]))
    print(f"[INFO] Retrieved {len(answers)} answers for question {question_id}")
    return answers


# ----------------------------------------------------------
# Extract code snippets from HTML
# ----------------------------------------------------------
def extract_code_blocks(html: str) -> List[str]:
    """
    Extract code snippets from answer HTML.
    Returns list of cleaned code strings.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    code_blocks = []

    # Multi-line <pre><code>
    for pre in soup.find_all("pre"):
        code_tag = pre.find("code")
        code = code_tag.get_text() if code_tag else pre.get_text()
        if code and code.strip():
            code_blocks.append(code.strip())

    # Inline <code> (fallback)
    if not code_blocks:
        for code in soup.find_all("code"):
            txt = code.get_text().strip()
            if txt:
                code_blocks.append(txt)

    # Clean fragments
    cleaned = []
    for c in code_blocks:
        c_clean = c.strip()
        if len(c_clean) < 3:
            continue
        cleaned.append(c_clean)

    return cleaned
