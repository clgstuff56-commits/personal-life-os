# ============================================================
# LAYER 2: Question Enrichment v4.0
# IMPROVED: LLM-first (no keyword matching)
# NEW: Gap detection — asks user for missing info before research
# NEW: Smarter fallback with more categories
# ============================================================

import os
import json
import requests
from dotenv import load_dotenv
from layer1 import load_graph, get_context

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")

# ─── HuggingFace API call ────────────────────────────────────
def call_hf(prompt):
    url = "https://router.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/Llama-3.1-8B-Instruct:cerebras",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    result = response.json()
    return result["choices"][0]["message"]["content"]


# ─── NEW: Gap Detection ─────────────────────────────────────
# Checks if we have enough context to answer well
# Returns list of missing info needed
def detect_gaps(user_question, context):
    """Check what info is missing to answer this question properly"""
    q_lower = user_question.lower()
    ctx_lower = context.lower()
    gaps = []

    # Check basic profile completeness
    if "name:" not in ctx_lower:
        gaps.append("name")
    if "city:" not in ctx_lower:
        gaps.append("city")
    if "current role:" not in ctx_lower:
        gaps.append("current role")

    # Question-specific gaps
    if any(w in q_lower for w in ["mba", "college", "study", "course", "degree"]):
        if "experience:" not in ctx_lower:
            gaps.append("years of experience")
        if "salary:" not in ctx_lower:
            gaps.append("current salary")
        if "budget" not in ctx_lower:
            gaps.append("education budget")

    elif any(w in q_lower for w in ["invest", "stock", "sip", "fd", "save", "mutual"]):
        if "salary:" not in ctx_lower:
            gaps.append("current salary/income")
        if "budget" not in ctx_lower and "save" not in ctx_lower:
            gaps.append("how much you can invest monthly")

    elif any(w in q_lower for w in ["job", "switch", "company", "career", "hire"]):
        if "experience:" not in ctx_lower:
            gaps.append("years of experience")
        if "salary:" not in ctx_lower:
            gaps.append("current salary")
        if "skills:" not in ctx_lower:
            gaps.append("your key skills")

    elif any(w in q_lower for w in ["travel", "trip", "visit", "go to", "vacation"]):
        if "city:" not in ctx_lower:
            gaps.append("which city you are travelling from")

    return gaps


# ─── Generate sub-questions (LLM-first, no keyword matching) ─
def generate_questions(user_question, context):
    prompt = f"""You are a personal advisor that breaks down complex life questions.

User Profile:
{context}

User Question: {user_question}

Your job: Generate exactly 4 specific sub-questions that need web research to answer this question FOR THIS SPECIFIC USER.

Rules:
- Use the user's ACTUAL details (name, city, salary, role, etc.) in sub-questions
- Make sub-questions specific enough to get useful search results
- Don't ask generic questions — make each one targeted
- If it's a travel question, ask about travel. If career, ask about career. Match the topic.
- Include the current year 2026 where relevant

Return ONLY a numbered list:
1. [specific sub-question]
2. [specific sub-question]
3. [specific sub-question]
4. [specific sub-question]"""

    try:
        print("🤖 Generating smart questions...")
        response = call_hf(prompt)

        # Parse numbered list
        questions = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line and line[0].isdigit() and '.' in line:
                question = line.split('.', 1)[1].strip()
                # Clean up common LLM artifacts
                question = question.strip('"').strip("'").strip()
                if question and len(question) > 10:
                    questions.append(question)

        if len(questions) >= 2:
            return questions[:4]
        else:
            print("   ⚠️  LLM returned too few questions, using fallback")
            return fallback_questions(user_question, context)

    except Exception as e:
        print(f"   ⚠️  AI failed: {e}")
        print("   → Using smart fallback questions...")
        return fallback_questions(user_question, context)


# ─── Fallback questions (improved, more categories) ──────────
def fallback_questions(user_question, context):
    ctx = {}
    for line in context.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            ctx[key.strip().lower()] = value.strip()

    q = user_question.lower()
    role   = ctx.get('current role', 'professional')
    salary = ctx.get('salary', '')
    city   = ctx.get('city', 'India')
    exp    = ctx.get('experience', '')
    skills = ctx.get('skills', '')
    goal   = ctx.get('goals', '')
    budget = ctx.get('constraints', '').replace('Budget:', '').strip()

    # ── Travel ───────────────────────────────────────────────
    travel_places = [
        "manali", "goa", "shimla", "leh", "ladakh", "kerala",
        "rajasthan", "ooty", "darjeeling", "rishikesh", "jaipur",
        "mumbai", "bangalore", "delhi", "kolkata", "varanasi",
        "andaman", "spiti", "coorg", "munnar", "kodaikanal",
        "udaipur", "agra", "kashmir", "meghalaya", "sikkim",
        "thailand", "bali", "dubai", "singapore", "maldives",
        "europe", "japan", "vietnam", "sri lanka", "nepal"
    ]
    destination = next((d for d in travel_places if d in q), None)

    if destination or any(w in q for w in ["go to", "visit", "travel", "trip", "vacation", "holiday", "tour", "trek"]):
        dest = destination or "the destination"
        return [
            f"Best time to visit {dest} in 2026 — weather and crowds",
            f"Total trip cost to {dest} from {city} for 3-5 days including travel and stay",
            f"Top things to do and must-visit places in {dest}",
            f"Is {dest} safe and accessible right now? Any travel advisories?"
        ]

    # ── MBA / Education ──────────────────────────────────────
    if any(w in q for w in ['mba', 'college', 'university', 'study abroad', 'masters']):
        return [
            f"Is MBA worth it for a {role} with {exp} experience earning {salary} in 2026?",
            f"Best MBA programs {'under ' + budget if budget else 'in India'} with good placement for {goal or 'career growth'}",
            f"MBA vs direct job switch — which gives better ROI for {role} in India?",
            f"What are alternatives to MBA for achieving {goal or 'career growth'} in 2026?"
        ]

    # ── Job Switch ───────────────────────────────────────────
    if any(w in q for w in ['job', 'switch', 'company', 'career change', 'resign']):
        return [
            f"Average salary for {role} with {exp} experience and skills in {skills} in 2026",
            f"Best companies hiring {role} in {city} right now in 2026",
            f"What skills should a {role} learn to get 50%+ salary hike?",
            f"How to switch from {role} to {goal or 'a better role'} — step by step"
        ]

    # ── Salary ───────────────────────────────────────────────
    if any(w in q for w in ['salary', 'hike', 'raise', 'pay', 'compensation', 'ctc']):
        return [
            f"Market salary for {role} with {exp} experience in {city} in 2026",
            f"How much salary hike to expect when switching jobs as a {role}?",
            f"Top paying companies for {role} in India in 2026",
            f"How to negotiate salary — best techniques for {role}"
        ]

    # ── Investment / Finance ─────────────────────────────────
    if any(w in q for w in ['invest', 'stock', 'mutual fund', 'crypto', 'sip', 'fd', 'save', 'insurance', 'loan', 'emi']):
        return [
            f"Best investment options for someone earning {salary} in India 2026",
            f"SIP vs FD vs stocks — which is better for {salary} salary in 2026?",
            f"How much should a {role} earning {salary} save and invest monthly?",
            f"Tax saving investment options for salaried {role} in India 2026"
        ]

    # ── Skills / Learning ────────────────────────────────────
    if any(w in q for w in ['learn', 'skill', 'course', 'certification', 'upskill']):
        return [
            f"Most in-demand skills for {role} in 2026",
            f"Best online courses to transition from {role} to {goal or 'next level'}",
            f"Which certifications boost salary most for {role} in India?",
            f"How long to learn skills needed for {goal or 'career growth'}?"
        ]

    # ── Health / Fitness ─────────────────────────────────────
    if any(w in q for w in ['gym', 'diet', 'workout', 'health', 'weight', 'fitness', 'sleep', 'stress']):
        return [
            f"Best workout routine for a busy {role} working long hours",
            f"Healthy diet plan for Indian {role} on a budget in {city}",
            f"How to manage stress and sleep better as a {role}",
            f"Best gyms or fitness apps for working professionals in {city} 2026"
        ]

    # ── Startup / Business ───────────────────────────────────
    if any(w in q for w in ['startup', 'business', 'founder', 'entrepreneur', 'side hustle']):
        return [
            f"Best startup ideas for a {role} with skills in {skills} in 2026",
            f"How to start a side business while working as a {role}?",
            f"Startup funding options in India for first-time founders in 2026",
            f"Common mistakes to avoid when starting a business in {city}"
        ]

    # ── Generic ──────────────────────────────────────────────
    return [
        f"What are the key considerations for: {user_question}",
        f"Best approach for a {role} in {city}: {user_question}",
        f"What are the pros and cons of: {user_question} for someone earning {salary}",
        f"Step by step guide: {user_question} in India 2026"
    ]


# ─── Main function ───────────────────────────────────────────
def enrich_question(user_question):
    print("\n" + "=" * 55)
    print("       🧠 LAYER 2: QUESTION ENRICHMENT")
    print("=" * 55)

    # Load profile from Layer 1
    graph   = load_graph()
    context = get_context(graph)

    if not context.strip():
        print("⚠️  No profile found! Run Layer 1 first.")
        return []

    print(f"\n📋 User Question: {user_question}")
    print(f"\n👤 Using profile:")
    print("-" * 40)
    print(context)
    print("-" * 40)

    # NEW: Check for gaps in context
    gaps = detect_gaps(user_question, context)
    if gaps:
        print(f"\n⚠️  Missing context: {', '.join(gaps)}")
        print("   (Answer quality may be limited without this info)")

    # Generate sub-questions
    questions = generate_questions(user_question, context)

    print(f"\n✅ Generated {len(questions)} sub-questions:")
    print("-" * 40)
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")
    print("-" * 40)

    return questions


# ─── Run standalone ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("    🚀 PERSONAL LIFE OS — LAYER 2 v4.0")
    print("=" * 55)

    question = input("\nEnter your question: ").strip()

    if question:
        questions = enrich_question(question)
        print(f"\n✅ Layer 2 complete — {len(questions)} questions ready for Layer 3!")
    else:
        print("No question entered!")