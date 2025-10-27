# answerforge/api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Project imports (adjust names/paths if your modules are different)
from answerforge.retriever.stackoverflow import search_stackoverflow, fetch_answers, extract_code_blocks
from answerforge.verifier.verifier import verify_python
from answerforge.llm.gemini_client import explain_code_with_gemini

app = FastAPI(title="AnswerForge MVP")

class Query(BaseModel):
    question: Optional[str] = None
    max_candidates: Optional[int] = 5

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/verify")
def verify_endpoint(q: Query):
    """
    Full flow:
      1) Search StackOverflow for the query
      2) For each question, fetch answers and extract first code block
      3) Run verify_python (static checks + sandbox run)
      4) On first verified snippet, call Gemini for an explanation and return combined JSON
    """
    if not q.question:
        raise HTTPException(status_code=400, detail="`question` is required in request body")

    # 1) Search
    try:
        questions = search_stackoverflow(q.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"search_stackoverflow failure: {e}")

    questions = questions[: q.max_candidates or 5]

    # 2) Iterate through questions and answers
    for qn in questions:
        try:
            answers = fetch_answers(qn["question_id"])
        except Exception:
            answers = []

        for ans in answers:
            blocks = extract_code_blocks(ans.get("body", ""))
            if not blocks:
                continue

            code = blocks[0]  # take the first code block
            # 3) Verify the code (static checks + run in sandbox)
            try:
                v = verify_python(code)
            except Exception as e:
                # if the verifier crashes, include the error and continue searching
                v = {"verified": False, "error": str(e)}

            if v.get("verified"):
                # 4) Explain the verified code using Gemini
                try:
                    explanation = explain_code_with_gemini(code, q.question)
                except Exception as e:
                    explanation = f"⚠️ Gemini call failed: {e}"

                return {
                    "question_title": qn.get("title"),
                    "question_id": qn.get("question_id"),
                    "answer_id": ans.get("answer_id"),
                    "code": code,
                    "verified": True,
                    "explanation": explanation,
                    "verify_details": v
                }

    # nothing found
    return {"verified": False, "message": "No verified snippet found for the query."}


@app.post("/verify_local")
def verify_local(q: Query):
    """
    Debug helper: runs verifier + Gemini on a local snippet (no StackOverflow).
    Use this to validate the pipeline end-to-end quickly.
    """
    # default test snippet if none provided
    snippet = "s = 'hello'\nprint(s[::-1])"

    question = q.question or "Reverse a string in python"

    try:
        v = verify_python(snippet)
    except Exception as e:
        return {"verified": False, "error": f"verifier error: {e}"}

    explanation = explain_code_with_gemini(snippet, question)
    return {
        "code": snippet,
        "verified": v,
        "explanation": explanation
    }
