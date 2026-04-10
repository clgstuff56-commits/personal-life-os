# ============================================================
# LAYER 4: Personal Filter
# Takes research results from Layer 3
# Filters and scores based on user's profile
# Returns only relevant results for Layer 5
# ============================================================

import os
import re
from dotenv import load_dotenv
from layer1 import load_graph, get_context
from layer2 import enrich_question
from layer3 import research

load_dotenv()

# ─── Score a single result ───────────────────────────────────
def score_result(result, context):
    score = 5  # default score
    content = (result["title"] + " " + result["content"]).lower()

    # Parse context
    ctx = {}
    for line in context.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            ctx[key.strip().lower()] = value.strip().lower()

    city       = ctx.get('city', '')
    salary     = ctx.get('salary', '').replace('lpa', '').strip()
    experience = ctx.get('experience', '').replace('years', '').strip()
    constraints = ctx.get('constraints', '')
    goal       = ctx.get('goals', '')
    role       = ctx.get('current role', '')

    # ── Boost score ──────────────────────────────────────────

    # City match
    if city and city.lower() in content:
        score += 2

    # India specific
    if 'india' in content or 'indian' in content:
        score += 1

    # 2024 or 2025 content
    if '2024' in content or '2025' in content:
        score += 1

    # Goal match
    if goal:
        goal_words = goal.lower().split()
        for word in goal_words:
            if len(word) > 4 and word in content:
                score += 1
                break

    # Role match
    if role and role.lower() in content:
        score += 1

    # ── Reduce score ─────────────────────────────────────────

    # Budget check — remove expensive options
    budget_match = re.search(r'budget[:\s]+(\d+)', constraints)
    if budget_match:
        budget = int(budget_match.group(1))

        # Find prices mentioned in content
        price_matches = re.findall(r'(\d+)\s*lakh', content)
        for price in price_matches:
            price = int(price)
            if price > budget * 2:
                score -= 3
                break

    # Old content penalty
    if '2020' in content or '2019' in content or '2018' in content:
        score -= 1

    # Generic content penalty
    generic_words = ["generally", "typically", "usually",
                     "in most cases", "it depends"]
    for word in generic_words:
        if word in content:
            score -= 1
            break

    return max(0, min(10, score))  # keep between 0-10

# ─── Filter and rank results ─────────────────────────────────
def filter_results(all_results, context):
    print("\n" + "=" * 55)
    print("       🎯 LAYER 4: PERSONAL FILTER")
    print("=" * 55)

    scored_results = []

    for question, results in all_results.items():
        print(f"\n📊 Filtering: {question[:50]}...")

        for result in results:
            score = score_result(result, context)
            scored_results.append({
                "question": question,
                "title":    result["title"],
                "url":      result["url"],
                "content":  result["content"],
                "score":    score
            })
            print(f"   [{score}/10] {result['title'][:50]}")

    # Sort by score
    scored_results.sort(key=lambda x: x["score"], reverse=True)

    # Keep top results only (score >= 4)
    filtered = [r for r in scored_results if r["score"] >= 4]

    print(f"\n{'=' * 55}")
    print(f"✅ Filtered: {len(scored_results)} → {len(filtered)} relevant results")
    print(f"{'=' * 55}")

    return filtered

# ─── Show filtered results ───────────────────────────────────
def show_filtered(filtered_results):
    print("\n" + "=" * 55)
    print("     ✅ TOP RELEVANT RESULTS FOR YOU")
    print("=" * 55)

    for i, r in enumerate(filtered_results[:6], 1):
        print(f"\n{i}. [{r['score']}/10] {r['title']}")
        print(f"   Q: {r['question'][:60]}...")
        print(f"   {r['content'][:200]}...")
        print(f"   🔗 {r['url']}")

    print("\n" + "=" * 55)

# ─── Main function ───────────────────────────────────────────
def personal_filter(user_question):
    # Load profile
    graph   = load_graph()
    context = get_context(graph)

    if not context.strip():
        print("❌ No profile found! Run Layer 1 first.")
        return []

    # Get research from Layer 3
    questions   = enrich_question(user_question)
    all_results = research(questions)

    # Filter results
    filtered = filter_results(all_results, context)

    # Show top results
    show_filtered(filtered)

    return filtered

# ─── Run standalone ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("    🚀 PERSONAL LIFE OS — LAYER 4")
    print("=" * 55)

    question = input("\nEnter your question: ").strip()

    if question:
        filtered = personal_filter(question)
        print(f"\n✅ Layer 4 complete!")
        print(f"   Relevant results kept: {len(filtered)}")
        print(f"\n→ Ready for Layer 5 decision!")
    else:
        print("No question entered!")