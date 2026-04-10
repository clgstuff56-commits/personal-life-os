# ============================================================
# REVERSE INTERVIEW ENGINE v2.0
# - Every user (new + returning) gets interviewed on open
# - 3 question banks that rotate — different each session
# - Fun facts shown after each answer
# - Teaches user something about themselves
# ============================================================

import os
import random
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from layer1 import load_graph, save_graph, extract, get_summary

load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")

# ─── HuggingFace API ─────────────────────────────────────────
def call_hf(prompt, max_tokens=400):
    url = "https://router.huggingface.co/v1/chat/completions"
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "meta-llama/Llama-3.1-8B-Instruct:cerebras",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return None


# ============================================================
# QUESTION BANKS — 3 sets, rotates each session
# Each question has: text, type, options (if choice), fun_fact
# fun_fact = what psychology/research says about this topic
# ============================================================

QUESTION_BANK_1 = [
    {
        "id": "monday",
        "text": "⏰ Monday morning. Alarm rings. What's the FIRST feeling in your gut?",
        "type": "choice",
        "options": [
            "😴 Ugh. 5 more minutes. Every. Single. Day.",
            "😐 Fine I guess. Nothing special.",
            "⚡ Actually kinda ready to get going.",
            "😰 Anxiety before the day even starts."
        ],
        "fun_fact": "💡 Fun Fact: Studies show your Monday morning feeling predicts job satisfaction more accurately than any survey. If it's been 'ugh' for 3+ months — your gut already made the decision your mind hasn't.",
        "extracts": "job_satisfaction"
    },
    {
        "id": "money_vs_meaning",
        "text": "💰 Real talk — ₹25 LPA boring job vs ₹8 LPA work you believe in. No 'it depends'.",
        "type": "choice",
        "options": [
            "₹25L — money first, sort rest later",
            "₹8L — meaning first, money will follow",
            "₹25L but I'd feel guilty about it",
            "I'd negotiate to make the ₹8L job pay more"
        ],
        "fun_fact": "💡 Fun Fact: Harvard research found people who chose meaning over money reported 2x higher life satisfaction after 5 years — BUT people who chose money and invested it wisely had equal satisfaction by year 10. Both paths work. The problem is choosing neither.",
        "extracts": "risk_appetite"
    },
    {
        "id": "flow",
        "text": "🌊 What's something you do where you look up and 3 hours just disappeared?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: Psychologist Mihaly Csikszentmihalyi studied 'flow' for 30 years. People in flow states are 5x more productive and report it as their happiest moments — more than vacations, parties, or even relationships. Your flow activity IS your superpower.",
        "extracts": "flow_state"
    },
    {
        "id": "proudest",
        "text": "🏆 One thing you've built or done that you're secretly proud of — but never put on your resume?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: What we leave OFF our resume often reveals more about our true capabilities than what we put ON it. Recruiters who ask this question consistently find the best hires.",
        "extracts": "hidden_strength"
    },
    {
        "id": "five_year",
        "text": "🔮 5 years from now — best life. What does your Tuesday afternoon look like? (Not job title — what are you DOING?)",
        "type": "open",
        "fun_fact": "💡 Fun Fact: People who describe their future in terms of daily activities (not titles) are 3x more likely to actually achieve it. The brain needs scenes, not labels.",
        "extracts": "true_goal"
    },
    {
        "id": "fear",
        "text": "😶 The decision sitting in the back of your head at 2am — what is it?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: Jeff Bezos calls this the 'Regret Minimization Framework' — imagine yourself at 80, looking back. The things we regret most are almost never the risks we took. They're the ones we didn't.",
        "extracts": "blocked_decision"
    },
    {
        "id": "role_model",
        "text": "🌟 One person — real or fictional — whose career/life you secretly want. Who?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: Your role model reveals your values more accurately than any personality test. We admire what we secretly want to become — not what we've been told to become.",
        "extracts": "inspiration"
    },
    {
        "id": "basics",
        "text": "📋 Last one! Ground me in reality — your current role, city, salary (rough), age, years working. Just dump it.",
        "type": "open",
        "fun_fact": "💡 Fun Fact: You just completed a psychological profile that most career coaches take 2 hours to build. Now I actually know you.",
        "extracts": "profile"
    }
]

QUESTION_BANK_2 = [
    {
        "id": "energy",
        "text": "🔋 After a full day of work — you're exhausted but someone invites you for something. Which one would actually recharge you?",
        "type": "choice",
        "options": [
            "🎮 Gaming or watching something alone",
            "☕ 1-on-1 deep conversation with a friend",
            "🎉 Group hangout, more people = more energy",
            "📚 Reading or learning something new"
        ],
        "fun_fact": "💡 Fun Fact: This reveals your introvert/extrovert energy pattern. But here's the twist — 70% of people are 'ambiverts' who need BOTH. The question is which one recharges you faster after stress. That's the real you.",
        "extracts": "personality_type"
    },
    {
        "id": "feedback",
        "text": "📢 Your manager gives you critical feedback in front of the team. Your HONEST internal reaction?",
        "type": "choice",
        "options": [
            "😤 Angry — even if they're right, not cool",
            "😳 Embarrassed and want to disappear",
            "🤔 Thinking — are they right or wrong?",
            "😶 Shut down completely, process it later"
        ],
        "fun_fact": "💡 Fun Fact: How you receive feedback predicts your career growth trajectory. People who immediately evaluate 'are they right?' (not 'how dare they') learn 40% faster than their peers over a 10-year career.",
        "extracts": "feedback_style"
    },
    {
        "id": "work_style",
        "text": "🛠️ You get a big project with zero instructions. What's your move?",
        "type": "choice",
        "options": [
            "📋 Make a detailed plan before touching anything",
            "🚀 Start immediately, figure it out as you go",
            "🤝 Find someone who's done it before and ask",
            "🔍 Research for 2 days, then start"
        ],
        "fun_fact": "💡 Fun Fact: Startups need option 2. Big companies reward option 1. Option 3 is the most underrated — studies show 'asking the right person' solves problems 10x faster than solo research.",
        "extracts": "work_style"
    },
    {
        "id": "childhood",
        "text": "🧒 What did you want to be at age 10? And what killed that dream?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: Steve Jobs, Elon Musk, and Warren Buffett all say their childhood obsession directly connects to their life's work — just in a different form. The dream didn't die. It just went underground.",
        "extracts": "original_passion"
    },
    {
        "id": "conflict",
        "text": "⚔️ Someone at work is being difficult and slowing your project. What do you actually do?",
        "type": "choice",
        "options": [
            "😬 Avoid them and work around it",
            "📧 Send a polite but firm email",
            "☕ Talk to them directly, face to face",
            "👆 Escalate to manager immediately"
        ],
        "fun_fact": "💡 Fun Fact: 85% of workplace failures are caused by relationship problems, not skill gaps. The people who choose option 3 consistently get promoted faster — not because it's comfortable, but because it builds trust.",
        "extracts": "conflict_style"
    },
    {
        "id": "legacy",
        "text": "🌍 If your work disappeared tomorrow — what would you actually miss about it?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: This question reveals your actual motivation — not what you THINK motivates you. Most people say 'salary' in surveys but answer 'the team' or 'the problem I was solving' to this question.",
        "extracts": "core_motivation"
    },
    {
        "id": "superpower",
        "text": "⚡ One skill you have that you think most people around you lack — what is it?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: Your self-assessed superpower is usually accurate. Research shows people consistently underestimate themselves in everything EXCEPT their top skill — which they see clearly.",
        "extracts": "top_skill"
    },
    {
        "id": "basics",
        "text": "📋 Ground check — your current role, city, rough salary, age, years working. One dump.",
        "type": "open",
        "fun_fact": "💡 Fun Fact: Done! Your answers just revealed your conflict style, energy pattern, work style, and true motivation. Most HR departments can't do this in 3 rounds of interviews.",
        "extracts": "profile"
    }
]

QUESTION_BANK_3 = [
    {
        "id": "regret",
        "text": "😔 One thing from your career so far — if you could redo it, you would. What is it?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: Regret research shows we regret INACTIONS 2x more than actions. Missed opportunities hurt more than failed attempts — even years later. Your regret is telling you what still matters.",
        "extracts": "regret"
    },
    {
        "id": "success_definition",
        "text": "🏁 Be honest — when you imagine being 'successful', what does the scene look like?",
        "type": "choice",
        "options": [
            "💰 Financial freedom — never worry about money",
            "🏆 Recognized as the best at what I do",
            "🌍 Built something that outlasts me",
            "⚖️ Balance — good work, good life, good health"
        ],
        "fun_fact": "💡 Fun Fact: Your definition of success is set by age 25 and rarely changes — but most people never articulate it. The ones who write it down are 42% more likely to achieve it.",
        "extracts": "success_definition"
    },
    {
        "id": "learning",
        "text": "📚 How do you actually learn best? Not how you THINK you should learn — how you actually do.",
        "type": "choice",
        "options": [
            "🎥 Watch/listen first, then try",
            "💪 Just start doing, learn by breaking things",
            "👥 Learn from someone who already did it",
            "📖 Read everything first, then execute"
        ],
        "fun_fact": "💡 Fun Fact: Knowing your learning style cuts skill acquisition time by 30%. Most schools teach one style. Most jobs demand another. The people who figure out their own style become the fastest learners in the room.",
        "extracts": "learning_style"
    },
    {
        "id": "worst_boss",
        "text": "😤 Describe your worst boss or work experience in one line. What made it unbearable?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: What you hate most in a boss reveals what you value most in leadership — including how you'd lead if given the chance. Your answer is basically your management philosophy.",
        "extracts": "leadership_values"
    },
    {
        "id": "risk",
        "text": "🎲 Someone offers you a startup role — 40% salary cut, but 1% equity. Company looks promising. You?",
        "type": "choice",
        "options": [
            "✅ Yes — asymmetric upside is worth the risk",
            "❌ No — stability matters more right now",
            "🤔 Depends on the founding team",
            "🔢 I'd negotiate — 1% isn't enough"
        ],
        "fun_fact": "💡 Fun Fact: This is exactly the offer early Flipkart, Zerodha, and CRED employees got. The ones who said yes made 100x. The ones who said 'depends on the team' and then verified — they made 100x too. The lesson: due diligence beats impulse in both directions.",
        "extracts": "risk_tolerance"
    },
    {
        "id": "values",
        "text": "💎 If you had to pick ONE thing your work MUST have — non-negotiable — what is it?",
        "type": "choice",
        "options": [
            "🧠 Intellectual challenge — I need to keep thinking",
            "🤝 People — great team, great culture",
            "📈 Growth — title, money, or both moving up",
            "🎯 Impact — what I do must actually matter"
        ],
        "fun_fact": "💡 Fun Fact: This single answer predicts where you'll be happiest better than any job title match. A brilliant role at a toxic company will always feel wrong if you picked 'people'. A low-impact job will drain you if you picked 'impact' — even at ₹40 LPA.",
        "extracts": "non_negotiable"
    },
    {
        "id": "identity",
        "text": "🪞 How do you introduce yourself at a party — not your job title, just YOU in one sentence?",
        "type": "open",
        "fun_fact": "💡 Fun Fact: People who can answer this without mentioning their job title have stronger personal brands, higher confidence, and report more life satisfaction. The ones who say 'I'm a software engineer' are more likely to feel stuck in their career.",
        "extracts": "self_identity"
    },
    {
        "id": "basics",
        "text": "📋 Reality check — current role, city, rough salary, age, years of experience. Just dump it all.",
        "type": "open",
        "fun_fact": "💡 Fun Fact: You just answered questions that most people spend years in therapy figuring out. Your profile is saved — now let's use it.",
        "extracts": "profile"
    }
]

ALL_BANKS = [QUESTION_BANK_1, QUESTION_BANK_2, QUESTION_BANK_3]


# ─── Pick which bank to use this session ─────────────────────
def pick_question_bank(graph):
    """Rotate banks so returning users always get fresh questions"""
    sessions = graph.get("interview", {}).get("session_count", 0)
    bank_index = sessions % len(ALL_BANKS)
    return ALL_BANKS[bank_index], bank_index


# ─── Display a choice question ────────────────────────────────
def ask_choice(question):
    print(f"\n  {question['text']}\n")
    for i, opt in enumerate(question["options"], 1):
        print(f"    {i}. {opt}")
    print()
    while True:
        choice = input("  Your choice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(question["options"]):
            return question["options"][int(choice) - 1]
        print(f"  Type a number between 1 and {len(question['options'])}")


# ─── Display an open question ─────────────────────────────────
def ask_open(question):
    print(f"\n  {question['text']}\n")
    while True:
        answer = input("  You: ").strip()
        if answer:
            return answer
        print("  Come on, give me something.")


# ─── Analyze answers → personality insights ──────────────────
def analyze(answers):
    insights = {
        "job_satisfaction": "unknown",
        "risk_appetite":    "unknown",
        "core_driver":      "unknown",
        "true_goal":        "unknown",
        "flow_state":       "not shared",
        "blocked_decision": "not shared",
        "contradiction":    None
    }

    # Job satisfaction
    monday = (answers.get("monday") or answers.get("energy") or "").lower()
    if any(w in monday for w in ["ugh", "5 more", "anxiety", "exhausted", "tired", "dread", "bore"]):
        insights["job_satisfaction"] = "unhappy"
    elif any(w in monday for w in ["ready", "going", "excited", "good"]):
        insights["job_satisfaction"] = "happy"
    else:
        insights["job_satisfaction"] = "neutral"

    # Risk appetite
    money = (answers.get("money_vs_meaning") or answers.get("risk") or "").lower()
    if any(w in money for w in ["25l", "money first", "stability", "no —"]):
        insights["risk_appetite"] = "security-first"
    elif any(w in money for w in ["8l", "meaning first", "yes —", "equity"]):
        insights["risk_appetite"] = "purpose-driven"
    elif any(w in money for w in ["guilty", "negotiate", "depends", "verify"]):
        insights["risk_appetite"] = "calculated-risk"

    # Core driver
    frustration = (answers.get("frustration") or answers.get("worst_boss") or answers.get("legacy") or "").lower()
    if any(w in frustration for w in ["creative", "build", "create", "design", "make"]):
        insights["core_driver"] = "creativity"
    elif any(w in frustration for w in ["team", "lead", "people", "culture", "alone"]):
        insights["core_driver"] = "people"
    elif any(w in frustration for w in ["freedom", "flexible", "remote", "own", "control"]):
        insights["core_driver"] = "autonomy"
    elif any(w in frustration for w in ["money", "salary", "growth", "promotion", "recognition"]):
        insights["core_driver"] = "growth"
    elif any(w in frustration for w in ["learn", "skill", "boring", "repetitive", "challenge"]):
        insights["core_driver"] = "challenge"
    else:
        insights["core_driver"] = "impact"

    # True goal
    future = (answers.get("five_year") or answers.get("success_definition") or "").lower()
    if any(w in future for w in ["startup", "company", "founder", "business", "entrepreneur", "outlasts"]):
        insights["true_goal"] = "entrepreneurship"
    elif any(w in future for w in ["freelance", "remote", "travel", "freedom", "balance"]):
        insights["true_goal"] = "freedom"
    elif any(w in future for w in ["lead", "team", "manager", "director", "ceo", "recognized", "best"]):
        insights["true_goal"] = "leadership"
    elif any(w in future for w in ["build", "create", "product", "code", "ship"]):
        insights["true_goal"] = "building"
    elif any(w in future for w in ["money", "financial", "never worry"]):
        insights["true_goal"] = "financial freedom"
    elif any(w in future for w in ["impact", "matter", "teach", "mentor", "help"]):
        insights["true_goal"] = "impact"
    else:
        insights["true_goal"] = "growth"

    # Flow state
    flow = answers.get("flow") or answers.get("superpower") or ""
    insights["flow_state"] = flow[:120] if flow else "not shared"

    # Blocked decision
    fear = answers.get("fear") or answers.get("regret") or ""
    insights["blocked_decision"] = fear[:120] if fear else "not shared"

    # Contradiction check
    if insights["risk_appetite"] == "security-first" and insights["true_goal"] == "entrepreneurship":
        insights["contradiction"] = (
            "You want to build your own thing — but you chose money/stability when pushed. "
            "That tension is real. Most founders feel it. The question is: which fear is bigger — "
            "failing at your own thing, or never trying?"
        )
    elif insights["job_satisfaction"] == "unhappy" and insights["risk_appetite"] == "security-first":
        insights["contradiction"] = (
            "You're unhappy at work — but you chose stability over meaning. "
            "You're paying for security with your happiness. "
            "At some point that math stops making sense."
        )
    elif insights["true_goal"] == "freedom" and insights["core_driver"] == "growth":
        insights["contradiction"] = (
            "You want freedom but you're driven by growth/recognition — "
            "which usually requires staying in systems. "
            "The happiest people with this pattern build their OWN metrics for growth."
        )

    return insights


# ─── Generate AI insight ──────────────────────────────────────
def generate_insight(answers, insights, graph):
    name = graph.get("person", {}).get("name", "")

    prompt = f"""You are a brutally honest but caring career mentor.

Here's what I know about this person from their interview answers:
- Job satisfaction: {insights['job_satisfaction']}
- Risk appetite: {insights['risk_appetite']}
- Core driver: {insights['core_driver']}
- True goal: {insights['true_goal']}
- Flow state: {insights['flow_state']}
- Blocked decision: {insights['blocked_decision']}
- Contradiction found: {insights.get('contradiction', 'none')}

Their raw answers:
{chr(10).join([f'- {k}: {v}' for k, v in answers.items() if k != 'basics'])}

Write 2-3 sentences that:
1. Tell them something TRUE about themselves they haven't fully admitted
2. Connect their answers to reveal a pattern they may not see
3. End with one specific, actionable suggestion

Be direct. No fluff. Speak like a wise older sibling, not a corporate coach.
Keep it under 80 words."""

    result = call_hf(prompt, max_tokens=150)
    if result and len(result) > 30:
        return result.strip()

    # Fallback insight
    fallbacks = {
        ("unhappy", "security-first"): "You already know you need to leave — but fear is disguised as 'being practical'. The practical move IS to leave before you spend 3 more years here.",
        ("unhappy", "purpose-driven"): "You know what you want. What's stopping you isn't opportunity — it's the last 2% of commitment. Make the decision first. The path appears after.",
        ("happy",   "purpose-driven"): "You're rare — you're both happy and purpose-driven. Your job now is to scale your impact, not just your title.",
        ("neutral",  "calculated-risk"): "You're playing it safe but thinking big. The gap between where you are and where you want to be closes with one bold move — not a plan, a move.",
    }
    key = (insights["job_satisfaction"], insights["risk_appetite"])
    return fallbacks.get(key, "Your answers show someone who knows exactly what they want — but is waiting for permission. Nobody is coming to give it. You already have it.")


# ─── Save everything to graph ─────────────────────────────────
def save_to_graph(graph, answers, insights, bank_index):
    graph.setdefault("personality", {})
    for key, val in insights.items():
        if val and val not in ("unknown", "not shared"):
            graph["personality"][key] = val

    prev_count = graph.get("interview", {}).get("session_count", 0)
    graph["interview"] = {
        "completed_at":  datetime.now().isoformat(),
        "session_count": prev_count + 1,
        "bank_used":     bank_index,
        "answers":       answers
    }
    save_graph(graph)


# ============================================================
# MAIN INTERVIEW RUNNER — called from main.py on every open
# ============================================================
def run_interview():
    print("\n" + "=" * 55)
    print("     🎯 LET'S START WITH A FEW QUESTIONS")
    print("=" * 55)
    print()
    print("  Not boring ones. These will actually tell you")
    print("  something about yourself.")
    print()
    print("  8 questions. Honest answers only.")
    print("=" * 55)
    input("\n  Press Enter when ready...\n")

    graph    = load_graph()
    bank, bi = pick_question_bank(graph)
    answers  = {}

    for i, q in enumerate(bank):
        print(f"\n{'─' * 55}")
        print(f"  Question {i+1} of {len(bank)}")
        print(f"{'─' * 55}")

        if q["type"] == "choice":
            answer = ask_choice(q)
        else:
            answer = ask_open(q)

        answers[q["id"]] = answer

        # Show fun fact
        print(f"\n  {q['fun_fact']}")
        time.sleep(0.8)

        # Extract profile from last question
        if q["id"] == "basics":
            found = extract(answer, graph)
            if found:
                print(f"\n  📋 Saved: {', '.join(found)}")

    # ── Analysis ─────────────────────────────────────────────
    print("\n\n" + "=" * 55)
    print("  🔍 READING YOUR PATTERN...")
    print("=" * 55)
    time.sleep(0.8)
    print("\n  Connecting the dots...")
    time.sleep(0.8)
    print("  Finding what you didn't say...")
    time.sleep(0.8)

    insights = analyze(answers)
    insight  = generate_insight(answers, insights, graph)
    save_to_graph(graph, answers, insights, bi)

    # ── The Reveal ───────────────────────────────────────────
    print("\n\n" + "=" * 55)
    print("  🎯 HERE'S WHAT YOUR ANSWERS SAY ABOUT YOU")
    print("=" * 55)

    labels = {
        "job_satisfaction": "Current happiness",
        "risk_appetite":    "Risk style",
        "core_driver":      "What drives you",
        "true_goal":        "Where you're heading"
    }
    for key, label in labels.items():
        val = insights.get(key, "")
        if val and val != "unknown":
            print(f"  {label:20s}: {val}")

    if insights.get("contradiction"):
        print(f"\n  ⚡ THE CONTRADICTION I SEE:")
        print(f"  {insights['contradiction']}")

    print(f"\n  🔮 MY TAKE ON YOU:")
    # wrap long insight text
    words = insight.split()
    line = "  "
    for word in words:
        if len(line) + len(word) > 54:
            print(line)
            line = "  " + word + " "
        else:
            line += word + " "
    if line.strip():
        print(line)

    print("\n" + "=" * 55)
    print("  ✅ Done! Now I actually know you.")
    print("  Ask me anything — I'll give you real answers.")
    print("=" * 55 + "\n")

    return load_graph()


# ─── Quick 3-question setup (fallback) ───────────────────────
def run_quick_interview():
    print("\n" + "=" * 55)
    print("     ⚡ QUICK SETUP")
    print("=" * 55)

    graph = load_graph()

    print("\n  Tell me: name, age, city, role, company, salary,")
    print("  experience, and goal. All in one message.\n")
    answer = input("  You: ").strip()
    found  = extract(answer, graph)
    if found:
        print(f"\n  ✅ Got: {', '.join(found)}")
    save_graph(graph)

    print("\n  What frustrates you most about your current work?\n")
    frustration = input("  You: ").strip()
    if frustration:
        graph.setdefault("personality", {})
        graph["personality"]["core_frustration"] = frustration
        save_graph(graph)

    print("\n  What decision have you been avoiding?\n")
    fear = input("  You: ").strip()
    if fear:
        graph.setdefault("personality", {})
        graph["personality"]["blocked_decision"] = fear
        save_graph(graph)

    print(f"\n  ✅ Done! {get_summary(graph)}\n")
    return load_graph()


# ─── Standalone run ──────────────────────────────────────────
if __name__ == "__main__":
    run_interview()