# frontend_app.py
import streamlit as st
import requests
import time
from typing import Any, Dict

# --- Configuration ---
API_BASE = "http://127.0.0.1:8000"
VERIFY_ENDPOINT = f"{API_BASE}/verify"
VERIFY_LOCAL_ENDPOINT = f"{API_BASE}/verify_local"
HEALTH_ENDPOINT = f"{API_BASE}/health"

st.set_page_config(
    page_title="AnswerForge",
    page_icon="⚡",
    layout="wide",
)

# --- CSS (modern minimal dark theme) ---
st.markdown(
    """
    <style>
    :root {
      --card-bg: #0b1220;
      --panel-bg: #071024;
      --muted: #94a3b8;
      --accent: #f97316; /* warm orange accent */
      --card-border: rgba(255,255,255,0.04);
    }
    .stApp {
      background: linear-gradient(180deg, #04060a 0%, #061024 100%);
      color: #e6eef8;
    }
    .card {
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 16px;
      border-radius: 12px;
      box-shadow: 0 6px 18px rgba(2,6,23,0.6);
    }
    .muted { color: var(--muted); }
    .accent { color: var(--accent); font-weight: 600; }
    .small { font-size: 0.9rem; }
    .status-dot { height:10px; width:10px; border-radius:50%; display:inline-block; margin-right:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar (System status + quick info) ---
with st.sidebar:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("## ⚙️ System")
    st.markdown("**AnswerForge — Dev UI**")
    st.markdown("A simple demo frontend for verifying and explaining code.")
    st.markdown("---")

    # Backend Status
    st.markdown("### 🔗 Backend status")
    status_placeholder = st.empty()
    refresh = st.button("🔄 Refresh status")

    st.markdown("---")
    st.markdown("### ⚡ Quick actions")
    st.markdown("- Use **Verify** for StackOverflow + Gemini verification")
    st.markdown("- Use **Verify Local** to run the verifier locally")
    st.caption("Built with Streamlit • Gemini + Docker backend")
    st.markdown("</div>", unsafe_allow_html=True)


def check_health() -> Dict[str, Any]:
    """Check backend health safely."""
    try:
        r = requests.get(HEALTH_ENDPOINT, timeout=3)
        if r.status_code == 200:
            return {"ok": True, "msg": "Backend reachable", "detail": r.json()}
        return {"ok": False, "msg": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "msg": f"{type(e).__name__}: {e}"}


# Initialize or refresh health
health = check_health() if refresh else check_health()

# Sidebar status indicator
if health["ok"]:
    status_placeholder.markdown(
        f"""<div class='small'>
        <span class='status-dot' style='background: #22c55e'></span>
        <strong class='accent'>Online</strong> — <span class='muted'>{health['msg']}</span></div>""",
        unsafe_allow_html=True,
    )
else:
    status_placeholder.markdown(
        f"""<div class='small'>
        <span class='status-dot' style='background: #ef4444'></span>
        <strong>Offline</strong> — <span class='muted'>{health['msg']}</span></div>""",
        unsafe_allow_html=True,
    )

# --- Main Layout ---
st.title("⚡ AnswerForge")
st.markdown("Ask a coding question — fetch verified code and concise explanation.")

col_input, col_meta = st.columns([3, 1])

with col_input:
    question = st.text_input("Ask your coding question", placeholder="e.g., reverse a string in python")
    submitted = st.button("🔎 Verify (StackOverflow + Gemini)")
    submitted_local = st.button("🧪 Verify Local (sandbox)")
    st.markdown("**Examples:**")
    st.markdown(
        "- `reverse a string in python`\n"
        "- `efficient merge two sorted arrays in c++`\n"
        "- `how to remove duplicates from list in python`"
    )

with col_meta:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Session")
    st.markdown(f"**API Base:** `{API_BASE}`")
    st.markdown("**Mode:** dev")
    st.markdown("</div>", unsafe_allow_html=True)


def call_verify(payload: dict, endpoint: str):
    """Call backend verify endpoints safely with longer timeout and clear errors."""
    try:
        resp = requests.post(endpoint, json=payload, timeout=60)
        resp.raise_for_status()
        try:
            return {"ok": True, "data": resp.json()}
        except Exception:
            return {"ok": False, "error": "Invalid JSON response from backend."}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "Request timed out after 60s. Backend may be busy."}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Cannot connect to backend. Is Uvicorn running?"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Handle user actions ---
result_placeholder = st.empty()

if submitted or submitted_local:
    if not question.strip():
        st.warning("Please enter a question first.")
    else:
        with st.spinner("🔄 Fetching verified code snippet and explanation..."):
            payload = {"question": question.strip(), "max_candidates": 10}
            endpoint = VERIFY_LOCAL_ENDPOINT if submitted_local else VERIFY_ENDPOINT
            res = call_verify(payload, endpoint)

        if not res["ok"]:
            result_placeholder.error(f"❌ Failed to call backend: {res['error']}")
        else:
            data = res["data"]
            verified = data.get("verified", False)
            code = data.get("code", "")
            explanation = data.get("explanation", "")

            left, right = st.columns([2, 1])
            with left:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                if verified:
                    st.success("✅ Verified Code Snippet")
                else:
                    st.warning("⚠️ Snippet verification failed or unverified.")

                st.code(code or "# No snippet found", language="python")
                st.markdown("#### 🧠 Explanation")
                st.markdown(explanation or "_No explanation provided._")
                st.markdown("</div>", unsafe_allow_html=True)

            with right:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### Debug Info")
                st.write("Verified:", verified)
                st.write("Response keys:", list(data.keys()))
                st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("Raw API Response"):
                st.json(data)

else:
    with result_placeholder.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 👋 Ready")
        st.markdown("Enter a coding question and click **Verify** to get a verified code snippet + explanation.")
        if not health["ok"]:
            st.warning("Backend offline. Run: `uvicorn answerforge.api.main:app --reload`")
        else:
            st.info("Backend is online and ready.")
        st.markdown("</div>", unsafe_allow_html=True)
