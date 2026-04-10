# ============================================================
# LAYER 5: Decision Compiler
# Takes filtered results from Layer 4
# Compiles ONE final personalized answer
# Uses HuggingFace API with regex fallback
# ============================================================

import os
import re
import requests
from dotenv import load_dotenv
from layer1 import load_graph, get_context
from layer2 import enrich_question
from layer3 import research
from layer4 import filter_results

load_dotenv()

HF_API_KEY    = os.getenv("HF_API_KEY")
HF_API_URL = "https://router.huggingface.co/hf-inference/models/mistralai/Mixtral-8x7B-Instruct-v0.1"

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
        "max_tokens": 800
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    result = response.json()
    return result["choices"][0]["message"]["content"]

# ─── Compile answer using AI ─────────────────────────────────
def compile_with_ai(user_question, context, filtered_results):
    research_text = ""
    for i, r in enumerate(filtered_results[:6], 1):
        research_text += f"\nSource {i} [{r['score']}/10]: {r['title']}\n"
        research_text += f"{r['content'][:200]}\n"

    # Detect question type so the AI doesn't treat everything as career advice
    q_lower = user_question.lower()
    if any(w in q_lower for w in ["go to", "visit", "travel", "trip", "vacation", "manali", "goa", "trek", "tour"]):
        answer_focus = "This is a TRAVEL question. Give advice about whether/how to make this trip — cost, timing, what to do. Do NOT give career advice."
    elif any(w in q_lower for w in ["invest", "stock", "mutual fund", "crypto", "sip", "fd", "loan", "emi"]):
        answer_focus = "This is a FINANCE question. Give advice about the financial decision based on the user's salary and budget."
    elif any(w in q_lower for w in ["gym", "diet", "workout", "health", "weight", "fitness", "sleep"]):
        answer_focus = "This is a HEALTH/FITNESS question. Give practical health advice."
    else:
        answer_focus = "This is a CAREER/LIFE question. Give career and life advice specific to the user's profile."

    prompt = f"""You are a personal life advisor giving specific, practical advice.

User Profile:
{context}

User Question: {user_question}

{answer_focus}

Research Findings:
{research_text}

Give a specific recommendation for THIS user based on their profile and the research above.
Format your answer exactly like this:

RECOMMENDATION: [Yes/No/Maybe + one line summary]

REASONS:
1. [Reason specific to user's profile]
2. [Reason specific to user's profile]
3. [Reason specific to user's profile]

BEST PATH FOR YOU:
1. [Specific step for this user]
2. [Specific step for this user]
3. [Specific step for this user]

RISKS TO CONSIDER:
- [Risk specific to user's situation]
- [Risk specific to user's situation]

Keep it specific to the user. Use their actual details."""

    try:
        print("🤖 Compiling personalized answer...")
        response = call_hf(prompt)
        if response and len(response) > 100:
            return response
        else:
            return None
    except Exception as e:
        print(f"   ⚠️  AI failed: {e}")
        return None

# ─── Fallback compiler without AI ────────────────────────────
def compile_fallback(user_question, context, filtered_results):
    # Parse context
    ctx = {}
    for line in context.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            ctx[key.strip().lower()] = value.strip()

    name        = ctx.get('name', 'You')
    role        = ctx.get('current role', 'professional')
    salary      = ctx.get('salary', '')
    city        = ctx.get('city', '')
    experience  = ctx.get('experience', '')
    goal        = ctx.get('goals', '')
    constraints = ctx.get('constraints', '')
    skills      = ctx.get('skills', '')

    question_lower = user_question.lower()

    # Build answer based on question type
    if 'mba' in question_lower:
        budget_match = re.search(r'(\d+)', constraints)
        budget = budget_match.group(1) if budget_match else "5"

        answer = f"""
RECOMMENDATION: Maybe — depends on your specific goal

REASONS:
1. Your current salary of {salary} at TCS with {experience} is good 
   but MBA can accelerate your transition to Product Manager role
2. With a budget of {budget} lakh, there are MBA options in {city} 
   that fit — ISMS Pune, SPPU programs start under 3 lakh
3. However, many PMs in India got the role WITHOUT an MBA — 
   skills and portfolio matter more at startups

BEST PATH FOR YOU:
1. First try getting PM role internally at TCS — 
   use your {experience} and technical background as advantage
2. If TCS doesn't work, apply to Series A/B startups 
   as Associate PM — they value tech skills over MBA
3. Only do MBA if you want to join a top consulting firm 
   or FAANG as PM — then FMS Delhi or TISS under {budget}L is best

RISKS TO CONSIDER:
- MBA from unknown college gives no advantage — 
  only top 20 MBA programs have good PM placements
- 2 years out of work + {budget} lakh cost = high risk 
  if PM role not guaranteed after graduation
- Your tech skills (Python, React, SQL) are actually 
  a HUGE advantage for Technical PM roles — don't waste them

SOURCES USED:
"""
        for i, r in enumerate(filtered_results[:3], 1):
            answer += f"  {i}. {r['title']} [{r['score']}/10]\n"
            answer += f"     {r['url']}\n"

    elif any(w in question_lower for w in ['job', 'switch', 'company']):
        answer = f"""
RECOMMENDATION: Yes — good time to switch with {experience}

REASONS:
1. {experience} at TCS gives you solid foundation 
   — market values TCS experience highly
2. Your skills ({skills}) are in high demand in 2025
3. Typical salary jump when switching = 30-50% hike from {salary}

BEST PATH FOR YOU:
1. Update LinkedIn with your TCS projects 
   and {skills} skills highlighted
2. Apply to product-focused companies in {city} first
   — Pune has strong tech market
3. Target companies where your PM goal aligns 
   with the role you are applying for

RISKS TO CONSIDER:
- Don't switch just for salary — 
  align with your PM goal
- Avoid switching to companies with no PM track 
  if your goal is {goal}

SOURCES USED:
"""
        for i, r in enumerate(filtered_results[:3], 1):
            answer += f"  {i}. {r['title']} [{r['score']}/10]\n"
            answer += f"     {r['url']}\n"

    elif any(w in question_lower for w in ['salary', 'hike', 'raise']):
        answer = f"""
RECOMMENDATION: Yes — you can negotiate a significant hike

REASONS:
1. Market rate for {role} with {experience} in India 
   is 12-18 LPA in 2025
2. Your current {salary} has room for 30-50% hike 
   when switching companies
3. Your skills ({skills}) command premium in current market

BEST PATH FOR YOU:
1. Research market rates on LinkedIn Salary, 
   Glassdoor for {role} in {city}
2. Get competing offers — best way to negotiate
3. Highlight your TCS experience + {skills} 
   in every interview

RISKS TO CONSIDER:
- Counter offer from TCS may not match market rate
- Don't reveal current salary in interviews — 
  give expected CTC instead

SOURCES USED:
"""
        for i, r in enumerate(filtered_results[:3], 1):
            answer += f"  {i}. {r['title']} [{r['score']}/10]\n"
            answer += f"     {r['url']}\n"

    else:
        answer = f"""
RECOMMENDATION: Here is what I found for {name}

BASED ON YOUR PROFILE:
- Current: {role} at TCS | {salary} | {city}
- Experience: {experience}
- Skills: {skills}
- Goal: {goal}
- Budget: {constraints}

TOP FINDINGS:
"""
        for i, r in enumerate(filtered_results[:5], 1):
            answer += f"\n{i}. {r['title']} [{r['score']}/10]"
            answer += f"\n   {r['content'][:150]}..."
            answer += f"\n   🔗 {r['url']}\n"

        answer += f"""
NEXT STEPS:
1. Review the top sources above
2. Focus on options that match your {city} location
3. Keep your budget of {constraints} as hard limit

SOURCES: {len(filtered_results)} relevant results found
"""

    return answer

# ─── Main compile function ───────────────────────────────────
def compile_decision(user_question, filtered_results, context):
    print("\n" + "=" * 55)
    print("      ⚡ LAYER 5: DECISION COMPILER")
    print("=" * 55)

    # Try AI first
    answer = compile_with_ai(user_question, context, filtered_results)

    # Use fallback if AI fails
    if not answer:
        print("   → Using smart fallback compiler...")
        answer = compile_fallback(user_question, context, filtered_results)

    print("\n" + "=" * 55)
    print("       🎯 YOUR PERSONALIZED ANSWER")
    print("=" * 55)
    print(answer)
    print("=" * 55)

    return answer

# ─── Full pipeline ───────────────────────────────────────────
def run_pipeline(user_question):
    # Layer 1 — load profile
    graph   = load_graph()
    context = get_context(graph)

    if not context.strip():
        print("❌ No profile found! Run Layer 1 first.")
        return

    # Layer 2 — enrich question
    questions = enrich_question(user_question)

    # Layer 3 — research
    all_results = research(questions)

    # Layer 4 — filter
    filtered = filter_results(all_results, context)

    # Layer 5 — compile answer
    answer = compile_decision(user_question, filtered, context)

    return answer

# ─── Run standalone ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("    🚀 PERSONAL LIFE OS — LAYER 5")
    print("=" * 55)

    question = input("\nEnter your question: ").strip()

    if question:
        run_pipeline(question)
        print("\n✅ All 5 layers complete!")
    else:
        print("No question entered!")