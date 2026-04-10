# ============================================================
# APP.PY — Personal Life OS (Streamlit Web Version)
# Same 5 layers, but now runs in browser instead of terminal
# Run with: streamlit run app.py
# ============================================================

import streamlit as st
import time
from layer1 import (
    load_graph, get_context, extract, save_graph,
    get_summary, empty_graph, test_connection
)
from layer2 import enrich_question
from layer3 import research
from layer4 import filter_results
from layer5 import compile_decision

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Personal Life OS",
    page_icon="🚀",
    layout="wide"
)

# ─── Custom CSS ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="st-"] {
    font-family: 'DM Sans', sans-serif;
}

.main-title {
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}

.sub-title {
    font-size: 1rem;
    color: #888;
    margin-top: -8px;
    margin-bottom: 24px;
}

.profile-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
}

.score-high { color: #10b981; font-weight: 700; }
.score-mid  { color: #f59e0b; font-weight: 700; }
.score-low  { color: #ef4444; font-weight: 700; }

.layer-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    margin: 2px 4px;
}

.result-card {
    border-left: 4px solid #667eea;
    padding: 12px 16px;
    margin: 8px 0;
    border-radius: 0 8px 8px 0;
    background: rgba(102, 126, 234, 0.05);
}

div[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}

div[data-testid="stSidebar"] .stMarkdown {
    color: #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ──────────────────────────────────────
if "graph" not in st.session_state:
    st.session_state.graph = load_graph()
if "profile_complete" not in st.session_state:
    st.session_state.profile_complete = False
if "answer" not in st.session_state:
    st.session_state.answer = None
if "pipeline_log" not in st.session_state:
    st.session_state.pipeline_log = []

# ─── Helper: Check profile completeness ─────────────────────
def check_profile(graph):
    required = {
        "name": graph["person"].get("name"),
        "age": graph["person"].get("age"),
        "city": graph["location"].get("city"),
        "role": graph["work"].get("role"),
        "experience": graph["work"].get("experience"),
        "salary": graph["work"].get("salary"),
        "goals": graph["goals"],
    }
    missing = [k for k, v in required.items() if not v]
    return missing

# ─── Sidebar: Profile ───────────────────────────────────────
with st.sidebar:
    st.markdown("## 👤 Your profile")
    graph = st.session_state.graph

    if graph["person"].get("name"):
        st.markdown(f"**{graph['person'].get('name', '')}**")

        if graph["person"].get("age"):
            st.markdown(f"🎂 {graph['person']['age']} years old")
        if graph["location"].get("city"):
            st.markdown(f"📍 {graph['location']['city']}")
        if graph["work"].get("role"):
            st.markdown(f"💼 {graph['work']['role']}")
        if graph["work"].get("company"):
            st.markdown(f"🏢 {graph['work']['company']}")
        if graph["work"].get("salary"):
            st.markdown(f"💰 {graph['work']['salary']}")
        if graph["work"].get("experience"):
            st.markdown(f"📅 {graph['work']['experience']}")
        if graph["education"].get("degree"):
            st.markdown(f"🎓 {graph['education']['degree']}")
        if graph["skills"]:
            st.markdown(f"🛠️ {', '.join(graph['skills'])}")
        if graph["goals"]:
            st.markdown(f"🎯 {graph['goals'][0][:60]}...")

        st.divider()
        if st.button("🗑️ Clear profile", use_container_width=True):
            st.session_state.graph = empty_graph()
            save_graph(st.session_state.graph)
            st.session_state.answer = None
            st.session_state.pipeline_log = []
            st.rerun()
    else:
        st.markdown("*No profile yet — set up below*")

# ─── Main Area ───────────────────────────────────────────────
st.markdown('<p class="main-title">🚀 Personal Life OS</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Your AI advisor — powered by real web research + your personal context</p>', unsafe_allow_html=True)

# ─── Tab Layout ──────────────────────────────────────────────
tab1, tab2 = st.tabs(["💬 Ask a question", "📝 Setup profile"])

# ─── TAB 2: Profile Setup ───────────────────────────────────
with tab2:
    st.markdown("### Tell me about yourself")
    st.markdown("Type naturally — I'll extract your details automatically.")

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Your name", placeholder="e.g. Kunal Acharya")
        age = st.number_input("Your age", min_value=15, max_value=80, value=22)
        city = st.text_input("Your city", placeholder="e.g. Jaipur, Mumbai, Delhi")
        degree = st.text_input("Your degree (optional)", placeholder="e.g. B.Tech, MBA, BCA")

    with col2:
        role = st.text_input("Your current role", placeholder="e.g. Software Developer, Data Analyst")
        company = st.text_input("Your company (optional)", placeholder="e.g. TCS, Infosys, Google")
        salary = st.text_input("Your salary (LPA)", placeholder="e.g. 5, 8.5, 12")
        experience = st.text_input("Years of experience", placeholder="e.g. 0, 2, 5")

    skills = st.text_input("Your skills (comma separated)", placeholder="e.g. Python, React, SQL, Machine Learning")
    goal = st.text_input("Your career goal", placeholder="e.g. Become a Product Manager, Switch to Data Science")

    if st.button("💾 Save profile", type="primary", use_container_width=True):
        graph = st.session_state.graph

        # Direct assignment — no need for extract() regex matching
        if name.strip():
            graph["person"]["name"] = name.strip().title()
        if age:
            graph["person"]["age"] = age
        if city.strip():
            graph["location"]["city"] = city.strip().title()
        if role.strip():
            graph["work"]["role"] = role.strip().title()
        if company.strip():
            graph["work"]["company"] = company.strip().upper()
        if salary.strip():
            num = salary.replace("lpa", "").replace("LPA", "").strip()
            try:
                float(num)
                graph["work"]["salary"] = f"{num} LPA"
            except ValueError:
                st.warning("Enter salary as a number like 5 or 8.5")
        if experience.strip():
            num = experience.replace("years", "").strip()
            if num.isdigit():
                graph["work"]["experience"] = f"{num} years"
        if degree.strip():
            graph["education"]["degree"] = degree.strip()
        if skills.strip():
            for s in skills.split(","):
                s = s.strip().title()
                if s and s not in graph["skills"]:
                    graph["skills"].append(s)
        if goal.strip():
            if not graph["goals"] or goal.strip() not in graph["goals"]:
                graph["goals"].append(goal.strip())

        save_graph(graph)
        st.session_state.graph = load_graph()
        st.success("✅ Profile saved to Neo4j!")
        st.rerun()

    # Also support natural language input
    st.divider()
    st.markdown("**Or type naturally:**")
    natural_input = st.text_area("", placeholder="My name is Kunal, I am 22 years old, I work at TCS as software developer in Jaipur, I know Python and React, my goal is to become product manager", height=100)

    if st.button("🔍 Extract from text", use_container_width=True):
        if natural_input.strip():
            graph = st.session_state.graph
            found = extract(natural_input, graph)
            if found:
                save_graph(graph)
                st.session_state.graph = load_graph()
                st.success(f"✅ Extracted: {', '.join(found)}")
                st.rerun()
            else:
                st.warning("Couldn't extract anything. Try being more specific.")

# ─── TAB 1: Ask Question ────────────────────────────────────
with tab1:
    graph = st.session_state.graph
    missing = check_profile(graph)

    if missing:
        st.warning(f"⚠️ Complete your profile first! Missing: **{', '.join(missing)}**. Go to 'Setup profile' tab.")
    else:
        st.markdown(f"👤 **{get_summary(graph)}**")

    question = st.text_input(
        "Ask me anything about your career, life, finance, travel...",
        placeholder="e.g. Should I do MBA? / Should I switch jobs? / Best investment for 5 LPA salary?",
        key="main_question"
    )

    if st.button("🚀 Get personalized answer", type="primary", use_container_width=True, disabled=bool(missing)):
        if question.strip():
            context = get_context(graph)
            pipeline_log = []

            # ── Layer 2: Enrich ──
            with st.status("🧠 Layer 2: Breaking down your question...", expanded=True) as status:
                start = time.time()
                questions = enrich_question(question)
                elapsed = round(time.time() - start, 1)
                pipeline_log.append(f"Layer 2: Generated {len(questions)} sub-questions ({elapsed}s)")

                for i, q in enumerate(questions, 1):
                    st.write(f"{i}. {q}")
                status.update(label=f"✅ Layer 2: {len(questions)} sub-questions ({elapsed}s)", state="complete")

            # ── Layer 3: Research ──
            with st.status("🔍 Layer 3: Searching the web...", expanded=True) as status:
                start = time.time()
                all_results = research(questions)
                total = sum(len(v) for v in all_results.values())
                elapsed = round(time.time() - start, 1)
                pipeline_log.append(f"Layer 3: Found {total} web results ({elapsed}s)")

                for q, results in all_results.items():
                    st.write(f"**{q[:60]}...** → {len(results)} results")
                status.update(label=f"✅ Layer 3: {total} web results found ({elapsed}s)", state="complete")

            # ── Layer 4: Filter ──
            with st.status("🎯 Layer 4: Scoring results for you...", expanded=True) as status:
                start = time.time()
                filtered = filter_results(all_results, context)
                elapsed = round(time.time() - start, 1)
                pipeline_log.append(f"Layer 4: {total} → {len(filtered)} relevant results ({elapsed}s)")

                for r in filtered[:5]:
                    score = r["score"]
                    css = "score-high" if score >= 7 else "score-mid" if score >= 5 else "score-low"
                    st.markdown(f'<span class="{css}">[{score}/10]</span> {r["title"][:70]}', unsafe_allow_html=True)
                status.update(label=f"✅ Layer 4: {len(filtered)} relevant results ({elapsed}s)", state="complete")

            # ── Layer 5: Compile ──
            with st.status("⚡ Layer 5: Writing your personalized answer...", expanded=False) as status:
                start = time.time()
                answer = compile_decision(question, filtered, context)
                elapsed = round(time.time() - start, 1)
                pipeline_log.append(f"Layer 5: Answer compiled ({elapsed}s)")
                status.update(label=f"✅ Layer 5: Answer ready ({elapsed}s)", state="complete")

            st.session_state.answer = answer
            st.session_state.pipeline_log = pipeline_log

    # ── Display Answer ──
    if st.session_state.answer:
        st.divider()
        st.markdown("### 🎯 Your personalized answer")
        st.markdown(st.session_state.answer)

        # Pipeline summary
        with st.expander("📊 Pipeline summary"):
            for log in st.session_state.pipeline_log:
                st.write(f"✅ {log}")

# ─── Footer ──────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.85rem;'>"
    "Personal Life OS v3.0 — Powered by Neo4j + Llama AI + Tavily"
    "</div>",
    unsafe_allow_html=True
)