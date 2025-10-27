# answerforge/llm/gemini_client.py  (replace the old explain_code_with_gemini function)
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read API key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY not found in .env file")

# Configure Gemini
genai.configure(api_key=API_KEY)


def extract_text(response) -> str:
    """
    Safely extract text output from Gemini responses (works across SDK versions).
    """
    # 1) Try the standard response.text
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    # 2) Try candidates (some SDK versions use this structure)
    candidates = getattr(response, "candidates", None)
    if candidates and len(candidates) > 0:
        try:
            cand = candidates[0]
            if hasattr(cand, "content"):
                content = cand.content
                # content.parts might be a list of text objects
                if hasattr(content, "parts") and isinstance(content.parts, list):
                    return " ".join(
                        part.text for part in content.parts if hasattr(part, "text")
                    ).strip()
            # Dict fallback (in case of dict-style structure)
            elif isinstance(cand, dict) and "content" in cand:
                content = cand["content"]
                if isinstance(content, list):
                    parts = [p.get("text", "") for p in content if isinstance(p, dict)]
                    return " ".join(parts).strip()
        except Exception:
            pass

    # 3) Try chunks (streamed responses)
    chunks = getattr(response, "_chunks", None)
    if chunks:
        parts = []
        for c in chunks:
            if hasattr(c, "text") and c.text:
                parts.append(c.text)
        if parts:
            return " ".join(parts).strip()

    # 4) Fallback — return repr of object
    return f"⚠️ Gemini returned an unexpected response: {repr(response)[:500]}"


def explain_code_with_gemini(code: str, question: str, max_output_tokens: int = 512) -> str:
    """
    Robust explanation caller with model fallbacks and safe debug preview.
    Tries pro model first, then falls back to smaller models if necessary.
    Returns either a clean explanation string or a short diagnostic message.
    """

    prompt = f"""
You are a helpful senior software engineer.
Question: {question}

Here is a verified Python snippet:

Provide:
1) A 2–4 line plain-English explanation of what the code does.
2) A one-line list of required imports (if any).
3) One caveat or edge-case to watch.

Be concise.
"""

    # model candidates (order = try best -> fallback)
    model_candidates = ["gemini-2.5-pro", "gemini-2.5", "gemini-1.5-flash"]

    def safe_extract(resp):
        try:
            txt = getattr(resp, "text", None)
            if isinstance(txt, str) and txt.strip():
                return txt.strip()
        except Exception:
            pass

        try:
            res = getattr(resp, "_result", None) or getattr(resp, "_response", None)
            if res:
                cand = None
                if hasattr(res, "candidates"):
                    cand_list = getattr(res, "candidates")
                    if cand_list:
                        cand = cand_list[0]
                elif isinstance(res, dict) and "candidates" in res:
                    cand_list = res["candidates"]
                    if cand_list:
                        cand = cand_list[0]
                if cand:
                    if hasattr(cand, "content"):
                        content = getattr(cand, "content")
                        if hasattr(content, "parts"):
                            parts = [getattr(p, "text", "") for p in content.parts if getattr(p, "text", None)]
                            joined = " ".join([p for p in parts if p]).strip()
                            if joined:
                                return joined
                    if isinstance(cand, dict):
                        cont = cand.get("content", cand.get("text", None))
                        if isinstance(cont, str) and cont.strip():
                            return cont.strip()
                        if isinstance(cont, list):
                            parts = []
                            for p in cont:
                                if isinstance(p, dict):
                                    parts.append(p.get("text") or p.get("content") or "")
                                else:
                                    parts.append(str(p))
                            joined = " ".join([p for p in parts if p]).strip()
                            if joined:
                                return joined
        except Exception:
            pass

        try:
            chunks = getattr(resp, "_chunks", None) or []
            if chunks:
                pieces = []
                for ch in chunks:
                    if hasattr(ch, "delta"):
                        d = getattr(ch, "delta")
                        if isinstance(d, str) and d.strip():
                            pieces.append(d.strip())
                        elif hasattr(d, "text"):
                            pieces.append(getattr(d, "text", "").strip())
                    if hasattr(ch, "text") and getattr(ch, "text"):
                        pieces.append(getattr(ch, "text").strip())
                    if hasattr(ch, "content") and getattr(ch, "content"):
                        pieces.append(str(getattr(ch, "content"))[:400])
                if pieces:
                    joined = " ".join(pieces).strip()
                    if joined:
                        return joined[:2000]
        except Exception:
            pass

        try:
            raw_preview = getattr(resp, "_result", None) or getattr(resp, "_response", None) or getattr(resp, "body", None)
            preview_str = repr(raw_preview)
            if len(preview_str) > 1000:
                preview_str = preview_str[:1000] + "...(truncated)"
            return f"⚠️ No clean text returned. Raw preview: {preview_str}"
        except Exception as e:
            return f"⚠️ No text and preview failed: {e}"

    # Try models in order
    last_exc = None
    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(model_name)

            # ✅ Retry logic: try with 1024 first, then 2048 if needed
            for tokens in (1024, 2048):
                try:
                    resp = model.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": tokens,
                            "temperature": 0.2
                        }
                    )
                    extracted = safe_extract(resp)
                    if extracted and not extracted.startswith("⚠️"):
                        return extracted
                except Exception:
                    continue

        except Exception as e:
            last_exc = e
            print(f"[gemini_client] model {model_name} failed: {e}")
            continue

    # All models failed or returned no usable text
    if last_exc:
        return f"⚠️ Gemini API error (all models attempted). Last error: {last_exc}"
    return "⚠️ Gemini returned no usable text from any model."
