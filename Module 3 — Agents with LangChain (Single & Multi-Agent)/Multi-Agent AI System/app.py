"""Multi-Agent Research Assistant: Streamlit UI for the search -> reader -> writer -> critic pipeline.

Run from the project root:
    uv run streamlit run app.py
"""

import html
import os
import time

import streamlit as st

from src.pipelines.pipeline import critic_step, reader_step, search_step, writer_step

# ==========================================
# CONFIG
# ==========================================

st.set_page_config(
    page_title="Multi-Agent Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

REQUIRED_KEYS = ["GROQ_API_KEY", "TAVILY_API_KEY"]

# (key, number, title, description, spinner text)
STEPS = [
    ("search", "01", "Search Agent", "Gathers recent web information",   "🔍 Search Agent is working…"),
    ("reader", "02", "Reader Agent", "Scrapes & extracts deep content",  "📄 Reader Agent is scraping top resources…"),
    ("writer", "03", "Writer Chain", "Drafts the full research report",  "✍️ Writer is drafting the report…"),
    ("critic", "04", "Critic Chain", "Reviews & scores the report",      "🧐 Critic is reviewing the report…"),
]

EXAMPLES = [
    "Future of LLM in Tech Industry",
    "All Latest AI Agents in 2026",
    "Roadmap for AGI development in next 5 years",
]


# ==========================================
# STYLE
# ==========================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

/* ── Base ── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: #edf3ff; }
.stApp {
    background: #07111f;
    background-image:
        radial-gradient(circle at top left, rgba(0,191,255,0.14), transparent 32%),
        radial-gradient(circle at bottom right, rgba(124,58,237,0.12), transparent 30%),
        linear-gradient(180deg, #07111f 0%, #0a1729 100%);
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1200px; }

/* ── Hero ── */
.hero { text-align: center; padding: 3.5rem 0 2.5rem; }
.hero-eyebrow {
    font-family: 'DM Mono', monospace; font-size: 0.7rem; font-weight: 500;
    letter-spacing: 0.25em; text-transform: uppercase; color: #38bdf8; margin-bottom: 1rem;
}
.hero h1 {
    font-family: 'Syne', sans-serif; font-size: clamp(2.8rem, 6vw, 5rem); font-weight: 800;
    line-height: 1.0; letter-spacing: -0.03em; color: #f8fbff; margin: 0 0 1rem;
}
.hero h1 span {
    background: linear-gradient(135deg, #38bdf8, #8b5cf6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-sub { font-size: 1.05rem; font-weight: 300; color: #b5c3d9; max-width: 520px; margin: 0 auto; line-height: 1.65; }
.divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(56,189,248,0.35), transparent); margin: 2rem 0; }

/* ── Input ── */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.06) !important; border: 1px solid rgba(56,189,248,0.25) !important;
    border-radius: 12px !important; color: #f8fbff !important; font-size: 1rem !important;
    padding: 0.8rem 1rem !important;
}
.stTextInput > div > div > input:focus { border-color: #38bdf8 !important; box-shadow: 0 0 0 4px rgba(56,189,248,0.14) !important; }
.stTextInput > label {
    font-family: 'DM Mono', monospace !important; font-size: 0.72rem !important; letter-spacing: 0.15em !important;
    text-transform: uppercase !important; color: #38bdf8 !important;
}

/* ── Button ── */
.stButton > button {
    background: linear-gradient(135deg, #38bdf8 0%, #8b5cf6 100%) !important; color: white !important;
    font-family: 'Syne', sans-serif !important; font-weight: 700 !important; letter-spacing: 0.04em !important;
    border: none !important; border-radius: 12px !important; padding: 0.8rem 2.2rem !important;
    box-shadow: 0 8px 30px rgba(56,189,248,0.22) !important; transition: all 0.18s ease !important;
}
.stButton > button:hover { transform: translateY(-2px) scale(1.01) !important; }

/* ── Example chips ── */
.chips { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin: 1rem 0 1.5rem; }
.chips-label { font-family: 'DM Mono', monospace; font-size: 0.68rem; color: #7f93ad; letter-spacing: 0.1em; }
.chip {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
    padding: 0.35rem 0.8rem; font-size: 0.75rem; color: #d8e2f0;
}

/* ── Pipeline step cards ── */
.step-card {
    background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.08); border-radius: 18px;
    padding: 1.5rem 1.8rem; margin-bottom: 1.2rem; position: relative; overflow: hidden;
}
.step-card.active { border-color: rgba(56,189,248,0.45); background: rgba(56,189,248,0.06); }
.step-card.done   { border-color: rgba(34,197,94,0.28);  background: rgba(34,197,94,0.05); }
.step-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: rgba(255,255,255,0.06); }
.step-card.active::before { background: #38bdf8; }
.step-card.done::before   { background: #22c55e; }
.step-header { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.3rem; }
.step-num    { font-family: 'DM Mono', monospace; font-size: 0.68rem; letter-spacing: 0.15em; color: #38bdf8; }
.step-title  { font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: #f8fbff; }
.step-status { margin-left: auto; font-family: 'DM Mono', monospace; font-size: 0.68rem; letter-spacing: 0.1em; }
.step-desc   { font-size: 0.82rem; color: #94a3b8; margin-top: 0.3rem; }
.status-waiting { color: #64748b; }
.status-running { color: #38bdf8; }
.status-done    { color: #22c55e; }

/* ── Result panels ── */
.result-content { font-size: 0.92rem; line-height: 1.8; color: #d8e2f0; white-space: pre-wrap; }
.panel-label {
    font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.2em; text-transform: uppercase;
    margin-bottom: 1.2rem; padding-bottom: 0.7rem;
}
.panel-label.blue  { color: #38bdf8; border-bottom: 1px solid rgba(56,189,248,0.15); }
.panel-label.green { color: #22c55e; border-bottom: 1px solid rgba(34,197,94,0.15); }

.section-heading { font-family: 'Syne', sans-serif; font-size: 1.35rem; font-weight: 700; color: #f8fbff; margin: 2rem 0 1rem; }
.notice { font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #7f93ad; text-align: center; margin-top: 3rem; letter-spacing: 0.08em; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# HELPERS
# ==========================================

def step_card_html(num: str, title: str, desc: str, state: str) -> str:
    label, cls = {
        "waiting": ("WAITING", "status-waiting"),
        "running": ("● RUNNING", "status-running"),
        "done":    ("✓ DONE", "status-done"),
    }[state]
    card_cls = {"running": "active", "done": "done"}.get(state, "")
    return f"""
    <div class="step-card {card_cls}">
        <div class="step-header">
            <span class="step-num">{num}</span>
            <span class="step-title">{title}</span>
            <span class="step-status {cls}">{label}</span>
        </div>
        <div class="step-desc">{desc}</div>
    </div>"""


def render_pipeline(slots: dict, results: dict, running: str | None = None):
    """Redraw every step card: done if it has a result, running if it's the current one."""
    for key, num, title, desc, _ in STEPS:
        state = "done" if key in results else "running" if key == running else "waiting"
        slots[key].markdown(step_card_html(num, title, desc, state), unsafe_allow_html=True)


# ==========================================
# STATE
# ==========================================

if "results" not in st.session_state:
    st.session_state.results = {}  # {"search": str, "reader": str, "writer": str, "critic": str}


# ==========================================
# UI: HERO
# ==========================================

st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">Multi-Agent AI System</div>
    <h1>Researcher<span>Agent</span></h1>
    <p class="hero-sub">
        Four specialized AI agents collaborate — searching, scraping, writing,
        and critiquing — to deliver a polished research report on any topic.
    </p>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)

missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]  # .env is loaded by src/tools/tools.py
if missing:
    st.error(f"Missing keys in .env: {', '.join(missing)}")
    st.stop()


# ==========================================
# UI: INPUT (left) + PIPELINE (right)
# ==========================================

col_input, _, col_pipeline = st.columns([5, 0.5, 4])

with col_input:
    with st.container(border=True):
        topic = st.text_input(
            "Research Topic",
            placeholder="e.g. Roadmap for AGI development in next 5 years",
        )
        run_btn = st.button("⚡ Run Research Pipeline", width="stretch")

    chips = "".join(f'<span class="chip">{ex}</span>' for ex in EXAMPLES)
    st.markdown(f'<div class="chips"><span class="chips-label">TRY →</span>{chips}</div>', unsafe_allow_html=True)

with col_pipeline:
    st.markdown('<div class="section-heading">Pipeline</div>', unsafe_allow_html=True)
    slots = {key: st.empty() for key, *_ in STEPS}  # placeholders we can redraw while running
    render_pipeline(slots, st.session_state.results)


# ==========================================
# RUN PIPELINE
# ==========================================

if run_btn:
    if not topic.strip():
        st.warning("Please enter a research topic first.")
    else:
        r = {}
        st.session_state.results = r
        runners = {
            "search": lambda: search_step(topic),
            "reader": lambda: reader_step(topic, r["search"]),
            "writer": lambda: writer_step(topic, r["search"], r["reader"]),
            "critic": lambda: critic_step(r["writer"]),
        }
        try:
            for key, *_, spinner_text in STEPS:
                render_pipeline(slots, r, running=key)
                with st.spinner(spinner_text):
                    r[key] = runners[key]()
            render_pipeline(slots, r)
        except Exception as e:  # rate limit, recursion limit, network...
            render_pipeline(slots, r)
            st.error(f"Pipeline stopped: {e}")


# ==========================================
# UI: RESULTS
# ==========================================

r = st.session_state.results

if r:
    st.markdown('<div class="divider"></div><div class="section-heading">Results</div>', unsafe_allow_html=True)

    for key, title in [("search", "🔍 Search Results (raw)"), ("reader", "📄 Scraped Content (raw)")]:
        if key in r:
            with st.expander(title):
                # escape: raw agent text must not be interpreted as HTML
                st.markdown(f'<div class="result-content">{html.escape(r[key])}</div>', unsafe_allow_html=True)

    if "writer" in r:
        with st.container(border=True):
            st.markdown('<div class="panel-label blue">📝 Final Research Report</div>', unsafe_allow_html=True)
            st.markdown(r["writer"])
        st.download_button(
            label="⬇ Download Report (.md)",
            data=r["writer"],
            file_name=f"research_report_{int(time.time())}.md",
            mime="text/markdown",
        )

    if "critic" in r:
        with st.container(border=True):
            st.markdown('<div class="panel-label green">🧐 Critic Feedback</div>', unsafe_allow_html=True)
            st.markdown(r["critic"])


# ==========================================
# UI: FOOTER
# ==========================================

st.markdown("""
<div class="notice">
    ResearchAgent · Powered by LangChain multi-agent pipeline · Built with Streamlit
</div>
""", unsafe_allow_html=True)
