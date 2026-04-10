# ============================================================
# LAYER 3: Deep Research
# Takes sub-questions from Layer 2
# Searches web using Tavily API
# Returns research results for Layer 4
# ============================================================

import os
from dotenv import load_dotenv
from tavily import TavilyClient
from layer1 import load_graph, get_context
from layer2 import enrich_question

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# ─── Initialize Tavily ───────────────────────────────────────
client = TavilyClient(api_key=TAVILY_API_KEY)

# ─── Search single question ──────────────────────────────────
def search_question(question):
    try:
        result = client.search(
            query=question,
            search_depth="basic",
            max_results=3
        )
        results = []
        for r in result.get("results", []):
            results.append({
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "content": r.get("content", "")[:300]
            })
        return results
    except Exception as e:
        print(f"   ⚠️  Search failed: {e}")
        return []

# ─── Research all questions ──────────────────────────────────
def research(questions):
    print("\n" + "=" * 55)
    print("       🔍 LAYER 3: DEEP RESEARCH")
    print("=" * 55)

    all_results = {}

    for i, question in enumerate(questions, 1):
        print(f"\n🔎 Searching {i}/{len(questions)}: {question[:50]}...")
        results = search_question(question)
        all_results[question] = results

        if results:
            print(f"   ✅ Found {len(results)} results")
            for r in results:
                print(f"      → {r['title'][:60]}")
        else:
            print(f"   ❌ No results found")

    print("\n" + "=" * 55)
    print(f"✅ Research complete — {len(all_results)} questions researched")
    print("=" * 55)

    return all_results

# ─── Format results for display ──────────────────────────────
def show_results(all_results):
    print("\n" + "=" * 55)
    print("          📚 RESEARCH RESULTS")
    print("=" * 55)

    for question, results in all_results.items():
        print(f"\n❓ {question}")
        print("-" * 40)
        if results:
            for i, r in enumerate(results, 1):
                print(f"\n  {i}. {r['title']}")
                print(f"     {r['content'][:200]}...")
                print(f"     🔗 {r['url']}")
        else:
            print("  No results found")

    print("\n" + "=" * 55)

# ─── Main function ───────────────────────────────────────────
def deep_research(user_question):
    # Get sub-questions from Layer 2
    questions = enrich_question(user_question)

    if not questions:
        print("❌ No questions generated!")
        return {}

    # Research each question
    results = research(questions)

    # Show results
    show_results(results)

    return results

# ─── Run standalone ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("    🚀 PERSONAL LIFE OS — LAYER 3")
    print("=" * 55)

    question = input("\nEnter your question: ").strip()

    if question:
        results = deep_research(question)
        print(f"\n✅ Layer 3 complete!")
        print(f"   Total questions researched: {len(results)}")
        total_results = sum(len(v) for v in results.values())
        print(f"   Total results found: {total_results}")
        print(f"\n→ Ready for Layer 4 filtering!")
    else:
        print("No question entered!")