# ============================================================
# LAYER 1: Personal Context Engine v4.0
# Neo4j AuraDB + JSON fallback (works even on college WiFi)
# Bug fixes: name extraction, skip words, fallback storage
# ============================================================

import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── Neo4j Connection ────────────────────────────────────────
NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

LOCAL_GRAPH_FILE = "personal_graph.json"
USE_NEO4J = True  # Will auto-disable if connection fails

driver = None

def get_driver():
    global driver, USE_NEO4J
    if not USE_NEO4J:
        return None
    if driver is None:
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
                max_connection_lifetime=200
            )
            # Quick connectivity check
            with driver.session() as session:
                session.run("RETURN 1")
        except Exception as e:
            print(f"⚠️  Neo4j unavailable ({e})")
            print("   → Using local JSON storage instead")
            USE_NEO4J = False
            driver = None
            return None
    return driver

def close_driver():
    global driver
    if driver:
        driver.close()
        driver = None

def test_connection():
    d = get_driver()
    if d:
        print("✅ Neo4j connected!")
        return True
    else:
        print("⚠️  Neo4j not available — using local storage")
        return False

# ─── JSON Fallback Storage ───────────────────────────────────
def save_to_json(graph):
    try:
        graph["meta"]["updated_at"] = datetime.now().isoformat()
        with open(LOCAL_GRAPH_FILE, 'w') as f:
            json.dump(graph, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ JSON save failed: {e}")
        return False

def load_from_json():
    try:
        if os.path.exists(LOCAL_GRAPH_FILE):
            with open(LOCAL_GRAPH_FILE, 'r') as f:
                graph = json.load(f)
            print("📂 Profile loaded from local storage")
            return graph
    except Exception as e:
        print(f"⚠️  JSON load failed: {e}")
    return empty_graph()

# ─── Write to Neo4j ──────────────────────────────────────────
def save_to_neo4j(graph):
    try:
        d = get_driver()
        if not d:
            return save_to_json(graph)

        with d.session() as session:
            name = graph["person"].get("name", "User")

            session.run("""
                MERGE (p:Person {id: 'main_user'})
                SET p.name       = $name,
                    p.age        = $age,
                    p.gender     = $gender,
                    p.updated_at = $updated_at
            """, name=name,
                 age=graph["person"].get("age"),
                 gender=graph["person"].get("gender"),
                 updated_at=datetime.now().isoformat())

            if graph["location"].get("city"):
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    MERGE (c:City {name: $city})
                    MERGE (p)-[:LOCATED_IN]->(c)
                """, city=graph["location"]["city"])

            if graph["work"].get("company"):
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    MERGE (co:Company {name: $company})
                    MERGE (p)-[:WORKS_AT]->(co)
                """, company=graph["work"]["company"])

            if graph["work"].get("role"):
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    SET p.role = $role
                """, role=graph["work"]["role"])

            if graph["work"].get("salary"):
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    SET p.salary = $salary
                """, salary=graph["work"]["salary"])

            if graph["work"].get("experience"):
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    SET p.experience = $experience
                """, experience=graph["work"]["experience"])

            if graph["education"].get("degree"):
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    MERGE (d:Degree {name: $degree})
                    MERGE (p)-[:HAS_DEGREE]->(d)
                """, degree=graph["education"]["degree"])

            for skill in graph["skills"]:
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    MERGE (s:Skill {name: $skill})
                    MERGE (p)-[:HAS_SKILL]->(s)
                """, skill=skill)

            for goal in graph["goals"]:
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    MERGE (g:Goal {text: $goal})
                    MERGE (p)-[:HAS_GOAL]->(g)
                """, goal=goal)

            for constraint in graph["constraints"]:
                session.run("""
                    MERGE (p:Person {id: 'main_user'})
                    MERGE (c:Constraint {text: $constraint})
                    MERGE (p)-[:HAS_CONSTRAINT]->(c)
                """, constraint=constraint)

        # Also save to JSON as backup
        save_to_json(graph)
        return True

    except Exception as e:
        print(f"⚠️  Neo4j save failed: {e}")
        print("   → Saving to local JSON instead")
        return save_to_json(graph)

# ─── Read from Neo4j ─────────────────────────────────────────
def load_from_neo4j():
    graph = empty_graph()
    try:
        d = get_driver()
        if not d:
            return load_from_json()

        with d.session() as session:
            result = session.run("""
                MATCH (p:Person {id: 'main_user'})
                RETURN p LIMIT 1
            """)
            record = result.single()
            if not record:
                # Try JSON fallback — maybe data was saved locally
                json_graph = load_from_json()
                if json_graph["person"]:
                    return json_graph
                print("🆕 New profile — let's get started!")
                return graph

            p = record["p"]
            if p.get("name"):       graph["person"]["name"]       = p["name"]
            if p.get("age"):        graph["person"]["age"]        = p["age"]
            if p.get("gender"):     graph["person"]["gender"]     = p["gender"]
            if p.get("role"):       graph["work"]["role"]         = p["role"]
            if p.get("salary"):     graph["work"]["salary"]       = p["salary"]
            if p.get("experience"): graph["work"]["experience"]   = p["experience"]

            result = session.run("""
                MATCH (p:Person {id: 'main_user'})-[:LOCATED_IN]->(c:City)
                RETURN c.name AS city LIMIT 1
            """)
            r = result.single()
            if r: graph["location"]["city"] = r["city"]

            result = session.run("""
                MATCH (p:Person {id: 'main_user'})-[:WORKS_AT]->(co:Company)
                RETURN co.name AS company LIMIT 1
            """)
            r = result.single()
            if r: graph["work"]["company"] = r["company"]

            result = session.run("""
                MATCH (p:Person {id: 'main_user'})-[:HAS_DEGREE]->(d:Degree)
                RETURN d.name AS degree LIMIT 1
            """)
            r = result.single()
            if r: graph["education"]["degree"] = r["degree"]

            result = session.run("""
                MATCH (p:Person {id: 'main_user'})-[:HAS_SKILL]->(s:Skill)
                RETURN s.name AS skill
            """)
            graph["skills"] = [r["skill"] for r in result]

            result = session.run("""
                MATCH (p:Person {id: 'main_user'})-[:HAS_GOAL]->(g:Goal)
                RETURN g.text AS goal
            """)
            graph["goals"] = [r["goal"] for r in result]

            result = session.run("""
                MATCH (p:Person {id: 'main_user'})-[:HAS_CONSTRAINT]->(c:Constraint)
                RETURN c.text AS constraint
            """)
            graph["constraints"] = [r["constraint"] for r in result]

        # Save JSON backup
        save_to_json(graph)
        print("📂 Profile loaded from Neo4j!")
        return graph

    except Exception as e:
        print(f"⚠️  Neo4j load failed: {e}")
        print("   → Loading from local storage...")
        return load_from_json()

# ─── Keep old function names ─────────────────────────────────
def empty_graph():
    return {
        "meta":        {"created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()},
        "person":      {},
        "work":        {},
        "location":    {},
        "education":   {},
        "goals":       [],
        "skills":      [],
        "constraints": [],
        "decisions":   [],   # NEW: track past decisions
        "interactions": []   # NEW: track conversation topics
    }

def load_graph():
    return load_from_neo4j()

def save_graph(graph):
    save_to_neo4j(graph)

# ─── Extract info from message ───────────────────────────────
def extract(message, graph):
    message = re.sub(r'^\s*you\s*:\s*', '', message.strip(), flags=re.IGNORECASE)
    text  = message.lower()
    found = []

    # ══════════════════════════════════════════════════════════
    # BUG FIX: Expanded skip_words to prevent false name matches
    # "i am ai engineer" was catching "Ai" as name
    # "i am ok" was catching "Ok" as name
    # ══════════════════════════════════════════════════════════
    name_patterns = [
        r'my name is ([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
        r'call me ([a-zA-Z]+)',
        r"i am ([a-zA-Z]+)",
        r"i'm ([a-zA-Z]+)",
        r"this is ([a-zA-Z]+)",
    ]
    skip_words = {
        # Common words after "I am"
        "a", "an", "the", "from", "working", "looking", "trying",
        "planning", "going", "not", "now", "also", "just", "very",
        "currently", "recently", "based", "located", "living",
        "staying", "residing", "here", "there", "doing", "trying",
        "hoping", "aiming", "earning", "seeking", "happy", "excited",
        # Feelings / states
        "ok", "okay", "fine", "good", "great", "bad", "tired",
        "sick", "busy", "free", "confused", "interested", "bored",
        "ready", "sure", "done", "glad", "new", "old", "young",
        "well", "better", "worse", "nervous", "anxious", "calm",
        # Gender / identity
        "male", "female", "fresher", "student",
        # ══════ BUG FIX: Job titles that "i am X" catches ══════
        "developer", "engineer", "analyst", "manager", "intern",
        "trainer", "consultant", "designer", "tester", "architect",
        "lead", "senior", "junior", "associate", "director",
        "founder", "ceo", "cto", "freelancer", "researcher",
        # ══════ BUG FIX: Tech words that "i am X" catches ══════
        "ai", "ml", "ui", "ux", "qa", "hr", "pm", "ba", "sa",
        "devops", "backend", "frontend", "fullstack",
        # ══════ BUG FIX: Action words ══════
        "thinking", "considering", "wondering", "exploring",
        "learning", "studying", "building", "creating",
        # Digits (stops "I am 22" from catching as name)
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"
    }

    # ══════ BUG FIX: Check role patterns BEFORE name patterns ══════
    # This prevents "i am ai engineer" from catching "ai" as name
    role_found = False
    roles = [
        "ai engineer", "ml engineer", "ai ml engineer",
        "software developer", "software engineer",
        "senior software engineer", "product manager",
        "product owner", "data scientist", "data analyst",
        "data engineer", "business analyst",
        "frontend developer", "backend developer",
        "full stack developer", "fullstack developer",
        "devops engineer", "ui ux designer", "ux designer",
        "scrum master", "tech lead", "solution architect",
        "developer", "engineer", "analyst", "designer",
        "consultant", "architect", "manager", "tester",
        "intern", "fresher", "trainee", "researcher"
    ]
    for role in roles:
        if role in text:
            graph["work"]["role"] = role.title()
            found.append(f"Role: {role.title()}")
            role_found = True
            break

    # Now check name — but skip if the matched word is part of a role
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip().title()
            first_word = name.split()[0].lower()

            # Skip if it's in skip_words
            if first_word in skip_words:
                continue

            # Skip if it's part of a role we already found
            if role_found and first_word in text and any(first_word in r for r in roles):
                continue

            # Skip single character names
            if len(first_word) < 2:
                continue

            graph["person"]["name"] = name
            found.append(f"Name: {name}")
            break

    # ── Age ──────────────────────────────────────────────────
    age_patterns = [
        r'i am (\d+) years old',
        r"i'm (\d+) years old",
        r'(\d+) years old',
        r'age[: ]+(\d+)',
        r'aged (\d+)',
        r'i am (\d{2})\b',   # catches "i am 22" (only 2 digits)
    ]
    for pattern in age_patterns:
        match = re.search(pattern, text)
        if match:
            age = int(match.group(1))
            if 15 <= age <= 80:
                graph["person"]["age"] = age
                found.append(f"Age: {age}")
                break

    # ── Gender ───────────────────────────────────────────────
    if any(w in text for w in ["i am male", "i'm male", "i am a male"]):
        graph["person"]["gender"] = "Male"
        found.append("Gender: Male")
    elif any(w in text for w in ["i am female", "i'm female", "i am a female"]):
        graph["person"]["gender"] = "Female"
        found.append("Gender: Female")

    # ── City ─────────────────────────────────────────────────
    cities = [
        "mumbai", "pune", "bangalore", "bengaluru", "delhi",
        "new delhi", "hyderabad", "chennai", "kolkata", "jaipur",
        "ahmedabad", "noida", "gurgaon", "gurugram", "surat",
        "indore", "bhopal", "nagpur", "lucknow", "kochi",
        "chandigarh", "coimbatore", "bhubaneswar", "patna",
        "visakhapatnam", "thiruvananthapuram", "mysore", "mangalore",
        "udaipur", "jodhpur", "varanasi", "agra", "kanpur",
        "ranchi", "guwahati", "dehradun", "shimla", "pondicherry"
    ]
    for city in cities:
        if city in text:
            graph["location"]["city"] = city.title()
            found.append(f"City: {city.title()}")
            break

    # ── Salary ───────────────────────────────────────────────
    salary_patterns = [
        r'(\d+(?:\.\d+)?)\s*lpa',
        r'(\d+(?:\.\d+)?)\s*lakh\s*per\s*annum',
        r'salary[: ]+(\d+(?:\.\d+)?)\s*lakh',
        r'earning[s]?\s*(\d+(?:\.\d+)?)\s*lakh',
        r'ctc[: ]+(\d+(?:\.\d+)?)',
        r'salary[: ]+(\d+(?:\.\d+)?)\s*lpa',
        r'(\d+(?:\.\d+)?)\s*lakhs?\s*(?:per\s*year|annually)',
    ]
    for pattern in salary_patterns:
        match = re.search(pattern, text)
        if match:
            salary = match.group(1)
            graph["work"]["salary"] = f"{salary} LPA"
            found.append(f"Salary: {salary} LPA")
            break

    # ── Company ──────────────────────────────────────────────
    companies = [
        "tcs", "infosys", "wipro", "accenture", "cognizant",
        "amazon", "google", "microsoft", "flipkart", "zomato",
        "swiggy", "paytm", "phonepe", "ola", "uber", "hcl",
        "tech mahindra", "ibm", "capgemini", "deloitte",
        "pwc", "kpmg", "razorpay", "freshworks", "zepto",
        "meesho", "nykaa", "groww", "cred", "byjus",
        "zerodha", "dream11", "lenskart", "dunzo", "ather",
        "oyo", "bharatpe", "unacademy", "vedantu", "scaler",
        "tata", "reliance", "bajaj", "mahindra", "airtel",
        "jio", "hdfc", "icici", "sbi", "axis"
    ]
    for company in companies:
        if company in text:
            graph["work"]["company"] = company.upper()
            found.append(f"Company: {company.upper()}")
            break

    # ── Experience ───────────────────────────────────────────
    exp_patterns = [
        r'(\d+)\s*years?\s*(?:of\s*)?experience',
        r'(\d+)\s*years?\s*(?:of\s*)?work',
        r'working\s*(?:for\s*)?(\d+)\s*years?',
        r'(\d+)\s*yrs?\s*exp',
        r'experience[: ]+(\d+)',
        r'fresher',  # special case
    ]
    for pattern in exp_patterns:
        if pattern == 'fresher':
            if 'fresher' in text:
                graph["work"]["experience"] = "0 years"
                found.append("Experience: 0 years (fresher)")
                break
        else:
            match = re.search(pattern, text)
            if match:
                exp = int(match.group(1))
                if 0 <= exp <= 45:
                    graph["work"]["experience"] = f"{exp} years"
                    found.append(f"Experience: {exp} years")
                    break

    # ── Education ────────────────────────────────────────────
    degrees = [
        ("btech", "B.Tech"), ("b.tech", "B.Tech"), ("b tech", "B.Tech"),
        ("mtech", "M.Tech"), ("m.tech", "M.Tech"), ("m tech", "M.Tech"),
        ("mba", "MBA"),      ("mca", "MCA"),       ("bca", "BCA"),
        ("bsc", "B.Sc"),     ("msc", "M.Sc"),      ("phd", "PhD"),
        ("be", "B.E"),       ("bba", "BBA"),        ("bcom", "B.Com"),
        ("mcom", "M.Com"),   ("ba", "B.A"),         ("ma", "M.A"),
        ("bachelor", "Bachelor"), ("master", "Master"),
        ("12th", "12th Pass"), ("diploma", "Diploma"),
    ]
    for degree_key, degree_name in degrees:
        # Avoid matching "be" as a standalone word in sentences
        if degree_key == "be":
            if re.search(r'\bb\.?e\b', text):
                graph["education"]["degree"] = degree_name
                found.append(f"Degree: {degree_name}")
                break
        elif degree_key in text:
            graph["education"]["degree"] = degree_name
            found.append(f"Degree: {degree_name}")
            break

    # ── Skills ───────────────────────────────────────────────
    skills_db = [
        "python", "java", "javascript", "typescript",
        "react", "angular", "vue", "node", "express",
        "sql", "mysql", "postgresql", "mongodb", "redis",
        "machine learning", "deep learning", "data science",
        "nlp", "natural language processing",
        "computer vision", "tensorflow", "pytorch",
        "aws", "azure", "gcp", "cloud", "docker",
        "kubernetes", "git", "linux", "django", "flask",
        "spring boot", "excel", "power bi", "tableau",
        "c++", "c#", "golang", "rust", "kotlin", "swift",
        "html", "css", "php", "ruby", "scala",
        "langchain", "langgraph", "streamlit", "fastapi",
        "next.js", "tailwind", "figma", "photoshop",
    ]
    for skill in skills_db:
        if skill in text:
            skill_name = skill.title()
            if skill_name not in graph["skills"]:
                graph["skills"].append(skill_name)
                found.append(f"Skill: {skill_name}")

    # ── Goals ────────────────────────────────────────────────
    goal_triggers = [
        "want to become", "goal is to", "aim is to",
        "planning to become", "dream is to",
        "want to be", "looking to become",
        "aspire to", "trying to become",
        "wish to become", "hope to become",
        "my goal is", "my aim is",
        "i want to", "i plan to",
    ]
    for trigger in goal_triggers:
        if trigger in text:
            for sentence in message.split('.'):
                sentence = re.sub(r'^\s*you\s*:\s*', '', sentence.strip(), flags=re.IGNORECASE)
                if trigger in sentence.lower():
                    goal = sentence.strip()
                    already_saved = any(
                        goal.lower().replace(" ", "") in g.lower().replace(" ", "")
                        or g.lower().replace(" ", "") in goal.lower().replace(" ", "")
                        for g in graph["goals"]
                    )
                    if goal and not already_saved:
                        graph["goals"].append(goal)
                        found.append(f"Goal: {goal}")

    # ── Budget ───────────────────────────────────────────────
    budget_patterns = [
        r'budget\s*(?:is\s*)?(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l)',
        r'(\d+(?:\.\d+)?)\s*lakh\s*budget',
        r'can\s*spend\s*(\d+(?:\.\d+)?)\s*lakh',
        r'afford\s*(\d+(?:\.\d+)?)\s*lakh'
    ]
    for pattern in budget_patterns:
        match = re.search(pattern, text)
        if match:
            budget = match.group(1)
            constraint = f"Budget: {budget} lakh"
            if constraint not in graph["constraints"]:
                graph["constraints"].append(constraint)
                found.append(f"Budget: {budget} lakh")
            break

    # ── No relocation ────────────────────────────────────────
    if any(w in text for w in [
        "cannot relocate", "can't relocate",
        "no relocation", "don't want to move",
        "don't want to relocate"
    ]):
        constraint = "No relocation"
        if constraint not in graph["constraints"]:
            graph["constraints"].append(constraint)
            found.append("Constraint: No relocation")

    # ── Track interaction topic (NEW) ────────────────────────
    topic = None
    if any(w in text for w in ["mba", "college", "university", "study"]):
        topic = "education"
    elif any(w in text for w in ["job", "switch", "career", "hire"]):
        topic = "career"
    elif any(w in text for w in ["invest", "stock", "save", "money"]):
        topic = "finance"
    elif any(w in text for w in ["travel", "trip", "visit", "go to"]):
        topic = "travel"

    if topic:
        interaction = {
            "topic": topic,
            "message": message[:100],
            "timestamp": datetime.now().isoformat()
        }
        if "interactions" not in graph:
            graph["interactions"] = []
        graph["interactions"].append(interaction)

    return found

# ─── Display profile ─────────────────────────────────────────
def show_graph(graph):
    print("\n" + "=" * 55)
    print("          📊 YOUR PERSONAL PROFILE")
    print("=" * 55)

    if graph["person"]:
        print("\n👤 Personal:")
        for k, v in graph["person"].items():
            print(f"   {k.title()}: {v}")

    if graph["location"]:
        print("\n📍 Location:")
        for k, v in graph["location"].items():
            print(f"   {k.title()}: {v}")

    if graph["work"]:
        print("\n💼 Work:")
        for k, v in graph["work"].items():
            print(f"   {k.title()}: {v}")

    if graph["education"]:
        print("\n🎓 Education:")
        for k, v in graph["education"].items():
            print(f"   {k.title()}: {v}")

    if graph["skills"]:
        print("\n🛠️  Skills:", ", ".join(graph["skills"]))

    if graph["goals"]:
        print("\n🎯 Goals:")
        for g in graph["goals"]:
            print(f"   • {g}")

    if graph["constraints"]:
        print("\n⚠️  Constraints:")
        for c in graph["constraints"]:
            print(f"   • {c}")

    # NEW: Show interaction history
    interactions = graph.get("interactions", [])
    if interactions:
        topics = {}
        for i in interactions:
            t = i.get("topic", "other")
            topics[t] = topics.get(t, 0) + 1
        print("\n📊 Your interests:")
        for t, count in sorted(topics.items(), key=lambda x: -x[1]):
            print(f"   {t}: {count} conversations")

    print("\n" + "=" * 55)

def get_summary(graph):
    parts = []
    if graph["person"].get("name"):     parts.append(graph["person"]["name"])
    if graph["person"].get("age"):      parts.append(f"{graph['person']['age']} years old")
    if graph["location"].get("city"):   parts.append(f"based in {graph['location']['city']}")
    if graph["work"].get("role"):       parts.append(f"works as {graph['work']['role']}")
    if graph["work"].get("company"):    parts.append(f"at {graph['work']['company']}")
    if graph["work"].get("salary"):     parts.append(f"earning {graph['work']['salary']}")
    if graph["goals"]:                  parts.append(f"goal: {graph['goals'][0]}")
    return " | ".join(parts) if parts else "No profile yet"

def get_context(graph):
    """Returns profile as a string — used by Layer 2, 3, 4, 5"""
    context = []
    p = graph["person"]
    w = graph["work"]
    l = graph["location"]
    e = graph["education"]

    if p.get("name"):        context.append(f"Name: {p['name']}")
    if p.get("age"):         context.append(f"Age: {p['age']}")
    if p.get("gender"):      context.append(f"Gender: {p['gender']}")
    if l.get("city"):        context.append(f"City: {l['city']}")
    if w.get("company"):     context.append(f"Company: {w['company']}")
    if w.get("role"):        context.append(f"Current Role: {w['role']}")
    if w.get("salary"):      context.append(f"Salary: {w['salary']}")
    if w.get("experience"):  context.append(f"Experience: {w['experience']}")
    if e.get("degree"):      context.append(f"Degree: {e['degree']}")
    if graph["skills"]:      context.append(f"Skills: {', '.join(graph['skills'])}")
    if graph["goals"]:       context.append(f"Goals: {'; '.join(graph['goals'])}")
    if graph["constraints"]: context.append(f"Constraints: {'; '.join(graph['constraints'])}")

    return "\n".join(context)

# ─── Standalone run ──────────────────────────────────────────
def main():
    print("\n" + "=" * 55)
    print("    🚀 PERSONAL LIFE OS — LAYER 1 v4.0")
    print("    Neo4j + JSON fallback (college WiFi safe)")
    print("=" * 55)

    test_connection()

    print("\nJust talk naturally about yourself!")
    print("\nCommands:")
    print("  'show'    → view full profile")
    print("  'summary' → one line summary")
    print("  'context' → see what Layer 2 receives")
    print("  'clear'   → delete all data")
    print("  'quit'    → exit")
    print("=" * 55 + "\n")

    graph = load_graph()

    while True:
        try:
            user_input = input("You: ").strip()
        except KeyboardInterrupt:
            print("\n✅ Goodbye!")
            break

        if not user_input:
            continue
        elif user_input.lower() == "quit":
            print("✅ Goodbye!")
            break
        elif user_input.lower() == "show":
            show_graph(graph)
        elif user_input.lower() == "summary":
            print(f"\n💡 {get_summary(graph)}\n")
        elif user_input.lower() == "context":
            print("\n📤 Context for Layer 2:")
            print("-" * 40)
            print(get_context(graph))
            print("-" * 40 + "\n")
        elif user_input.lower() == "clear":
            confirm = input("Are you sure? (yes/no): ")
            if confirm.lower() == "yes":
                try:
                    d = get_driver()
                    if d:
                        with d.session() as session:
                            session.run("MATCH (n) DETACH DELETE n")
                except:
                    pass
                graph = empty_graph()
                save_to_json(graph)
                print("🗑️  Profile cleared!")
        else:
            found = extract(user_input, graph)
            if found:
                print(f"✅ Extracted: {', '.join(found)}")
                save_graph(graph)
            else:
                print("💬 Noted! Nothing specific extracted.")

    close_driver()

if __name__ == "__main__":
    main()