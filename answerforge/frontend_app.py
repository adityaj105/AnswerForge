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

# --- Small CSS for a minimalistic dark look (applies to Streamlit components) ---
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

# --- Sidebar (API status + quick info) ---
with st.sidebar:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("## ⚙️ System")
    st.markdown("**AnswerForge — Dev UI**")
    st.markdown("A simple demo frontend for verifying and explaining code.")
    st.markdown("---")

    # API status area
    st.markdown("### 🔗 Backend status")
    status_placeholder = st.empty()
    refresh = st.button("🔄 Refresh status")

    st.markdown("---")
    st.markdown("### ⚡ Quick actions")
    st.markdown("- Use **Verify** to retrieve from StackOverflow + Gemini")
    st.markdown("- Use **Verify Local** to run the verifier on a local snippet")
    st.markdown("---")
    st.caption("Built with Streamlit • Docker sandbox + Gemini backend")
    st.markdown("</div>", unsafe_allow_html=True)


def check_health() -> Dict[str, Any]:
    """Return dict with 'ok' boolean and text message (safe)."""
    try:
        r = requests.get(HEALTH_ENDPOINT, timeout=2.5)
        if r.status_code == 200:
            return {"ok": True, "msg": "Backend reachable", "detail": r.json()}
        return {"ok": False, "msg": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "msg": f"Error: {e}"}


# initial status (or on refresh)
if refresh:
    health = check_health()
else:
    # on load try once
    health = check_health()

# render status in sidebar placeholder
if health["ok"]:
    status_placeholder.markdown(
        f"""<div class='small'><span class='status-dot' style='background: #22c55e'></span>
        <strong class='accent'>Online</strong> — <span class='muted small'>{health.get('msg')}</span></div>""",
        unsafe_allow_html=True,
    )
else:
    status_placeholder.markdown(
        f"""<div class='small'><span class='status-dot' style='background: #ef4444'></span>
        <strong>Offline</strong> — <span class='muted small'>{health.get('msg')}</span></div>""",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Try reconnect"):
        time.sleep(0.2)
        health = check_health()
        st.experimental_rerun()

# --- Main UI layout ---
st.title("⚡ AnswerForge")
st.markdown("Ask a coding question — fetch verified code and a concise explanation.")

col_input, col_meta = st.columns([3, 1])

with col_input:
    question = st.text_input("Ask your coding question", value="", placeholder="e.g., reverse a string in python")
    submitted = st.button("🔎 Verify (StackOverflow + Gemini)")
    submitted_local = st.button("🧪 Verify Local (run in sandbox)")
    # small examples
    st.markdown("**Examples:**")
    st.markdown(
        "- `reverse a string in python`  \n"
        "- `efficient merge two sorted arrays in c++`  \n"
        "- `how to remove duplicates from list in python`"
    )

with col_meta:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Session")
    st.markdown(f"**API Base:** `{API_BASE}`")
    st.markdown("**Mode:** dev")
    st.markdown("</div>", unsafe_allow_html=True)


# placeholder for result area
result_placeholder = st.empty()

def call_verify(payload: dict, endpoint: str):
    try:
        resp = requests.post(endpoint, json=payload, timeout=15)
        # be defensive: return JSON or structured error
        try:
            return {"ok": True, "data": resp.json()}
        except Exception:
            return {"ok": False, "error": "Non-JSON response from backend", "status": resp.status_code, "text": resp.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# handle actions
if submitted or submitted_local:
    if not question and submitted:
        st.warning("Please enter a question for the Verify flow.")
    else:
        with st.spinner("Contacting backend and retrieving verified snippet..."):
            payload = {"question": question or "", "max_candidates": 10}
            endpoint = VERIFY_LOCAL_ENDPOINT if submitted_local else VERIFY_ENDPOINT
            res = call_verify(payload, endpoint)

        if not res["ok"]:
            result_placeholder.error(f"Failed to call backend: {res.get('error')}")
        else:
            data = res["data"]
            # Show verification badge
            verified = data.get("verified", False)
            verify_reason = None
            verify_details = None
            if isinstance(verified, dict):
                # If backend returns verify structure inside 'verified' (older shape)
                verify_details = verified
                verified = verified.get("verified", False)
            # attempt to fetch common fields
            code = data.get("code") or data.get("extracted_code") or data.get("snippet") or ""
            explanation = data.get("explanation") or data.get("explain") or data.get("explanation_text") or ""

            # Render results in two-column layout
            left, right = st.columns([2, 1])

            with left:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                # Top row: Title + badge
                if verified:
                    st.markdown("### ✅ Verified snippet")
                    st.success("Docker test passed — code executed successfully")
                else:
                    st.markdown("### ⚠️ Snippet (unverified)")
                    st.warning("Snippet is not verified (or verification failed)")

                # Code block (if present)
                if code:
                    st.code(code, language="python")
                else:
                    st.info("No code snippet returned by the backend.")

                st.markdown("---")
                st.markdown("#### Explanation")
                if explanation:
                    st.markdown(explanation)
                else:
                    st.markdown("<span class='muted'>No explanation returned.</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with right:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### 🔍 Details")
                # show verify_details or raw data keys
                st.write("**Verified:**", verified)
                if verify_details:
                    st.write("**Verify details:**", verify_details)
                else:
                    # attempt show nested verify_details
                    st.write("Raw response keys:", list(data.keys()))
                st.markdown("</div>", unsafe_allow_html=True)

            # show raw debug if dev user wants
            with st.expander("Show raw response (debug)"):
                st.json(data)

# show connection hint when idle
else:
    with result_placeholder.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 👋 Ready")
        st.markdown("Enter a question and press **Verify** to fetch a verified snippet + explanation.")
        if not health["ok"]:
            st.warning("Backend appears offline. Start your backend server (uvicorn) and click Refresh in the sidebar.")
        else:
            st.info("Backend online — you can query it.")
        st.markdown("</div>", unsafe_allow_html=True)
