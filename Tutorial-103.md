# 🚀 Complete Tutorial: Build an "Ask-the-Web" Agent like Perplexity

## Full Beginner-to-Advanced Guide | Part 1 of 2

---

> **What we are building:** An AI agent that can search the web, read results, think about them, and give you a smart answer with sources — just like Perplexity.ai does.

---

# 📚 TABLE OF CONTENTS — PART 1

```
PART 1 (This Document)
│
├── 1. What is Perplexity? What are we building?
├── 2. Agents Overview
│   ├── What is an Agent?
│   ├── LLMs vs Agents vs Agentic Systems
│   └── Agency Levels
├── 3. Workflows
│   ├── Prompt Chaining
│   ├── Routing
│   ├── Parallelization (Sectioning + Voting)
│   ├── Reflection
│   └── Orchestrator-Worker
├── 4. Tools
│   ├── What is Tool Calling?
│   ├── Tool Formatting
│   ├── Tool Execution
│   └── MCP (Model Context Protocol)
```

---

# 🌟 CHAPTER 1: What Are We Building?

---

## 1.1 What is Perplexity.ai?

Let me explain this with a simple story.

### 🔴 The Old Way (Before Perplexity):

Imagine you want to know:
**"What is the best programming language to learn in 2025?"**

**Step 1:** You open Google
**Step 2:** You see 10 blue links
**Step 3:** You click link 1... read it... too long
**Step 4:** You click link 2... different opinion...
**Step 5:** You click link 3... another opinion...
**Step 6:** After 20 minutes, you are confused

**The problem:** Google gives you **links**, not **answers**. You do the hard work.

---

### 🟢 The Perplexity Way:

**Step 1:** You ask: *"What is the best programming language to learn in 2025?"*
**Step 2:** Perplexity:
- Searches the web automatically
- Reads multiple pages
- Thinks about what it read
- Writes you a clear summary
- Shows you the sources

**Step 3:** You get a smart answer in 5 seconds with citations

**The magic:** An AI agent does all the searching, reading, and thinking **FOR YOU**.

---

## 1.2 What We Will Build (Simple Version)

```
USER ASKS A QUESTION
        ↓
Our Agent THINKS: "What do I need to search?"
        ↓
Agent SEARCHES the web using a tool
        ↓
Agent READS the search results
        ↓
Agent THINKS: "Is this enough information?"
        ↓
Agent WRITES a clear answer with sources
        ↓
USER GETS ANSWER ✅
```

---

## 1.3 Technologies We Will Use

| Component | Technology |
|-----------|------------|
| The Brain (LLM) | GPT-4o / Claude / Gemini |
| Web Search Tool | Tavily API / SerpAPI |
| Agent Framework | LangChain / custom code |
| Web Interface | Streamlit / Gradio |
| Language | Python |

---

# 🧠 CHAPTER 2: Agents Overview

---

## 2.1 What is an AI Agent?

### 🔮 Prediction First:

**What do most beginners think?**
> "An agent is just a chatbot that answers questions."

**The real answer:**
> An agent is an AI system that can **perceive, think, decide, act, and observe results** — in a loop — to complete a goal.

---

### 🏠 Real-World Analogy:

Think about a **human assistant** at work:

**Regular Employee (LLM):**
- You give them a document
- They read it
- They answer your question
- That's it. Done. They stop.

**Agent Employee:**
- You give them a goal: *"Find me the best hotel in Paris under $200"*
- They DECIDE: "I need to search Google"
- They SEARCH Google
- They SEE the results
- They DECIDE: "Let me check reviews too"
- They CHECK Tripadvisor
- They COMPARE options
- They REPORT back to you with a recommendation

**The key difference:** The agent keeps working, making decisions, using tools, until the goal is achieved.

---

### 🔑 The 5 Core Properties of an Agent:

```
1. PERCEPTION    → Can receive input (text, images, data)
2. THINKING      → Can reason about what to do
3. DECISION      → Can choose an action
4. ACTION        → Can DO something (call a tool, search web)
5. OBSERVATION   → Can see the result and continue
```

This **loop** is what makes an agent powerful.

---

## 2.2 LLMs vs Agents vs Agentic Systems

### 🟡 Very Important — Understand the Difference

Most beginners mix these three up. Let me explain each clearly.

---

### 📦 Level 1: LLM (Large Language Model)

**What it is:**
A very smart text prediction machine. It takes text in, produces text out.

**Real-world analogy:**
A **calculator** — you give input, it gives output. It doesn't remember. It doesn't decide what to calculate next. It just responds.

**Example:**
```
YOU: "What is the capital of France?"
LLM: "Paris"
[DONE — it stops here]
```

**Key limitation:**
- No memory between conversations (by default)
- Cannot search the web
- Cannot run code
- Cannot take actions
- Just input → output, one time

---

### 🤖 Level 2: Agent

**What it is:**
An LLM **plus** the ability to use tools, remember things, and loop until a task is done.

**Real-world analogy:**
A **smart assistant with a phone** — they can call people, search the internet, take notes, and keep working until they finish your task.

**Example:**
```
YOU: "What are the top AI news stories today?"
AGENT:
  → THINKS: "I need to search the web"
  → USES TOOL: web_search("top AI news today")
  → SEES RESULTS: [list of articles]
  → THINKS: "Let me read the top 3"
  → READS: article 1, 2, 3
  → WRITES: "Here are today's top AI stories: ..."
[Goal complete ✅]
```

**Key additions over LLM:**
- Tool use (search, code, APIs)
- Memory (short-term and long-term)
- Planning (deciding what steps to take)
- Looping (keep going until done)

---

### 🏗️ Level 3: Agentic System

**What it is:**
Multiple agents working together in a coordinated system, each with different roles, tools, and responsibilities.

**Real-world analogy:**
A **company with departments** — the CEO (orchestrator) gives direction, the Research team searches, the Writing team drafts, the Review team checks quality.

**Example (Our Perplexity Clone):**
```
ORCHESTRATOR AGENT: "User asked about climate change"
       ↓
SEARCH AGENT: Searches web for latest climate data
       ↓
READER AGENT: Reads and extracts key information
       ↓
WRITER AGENT: Writes a clear summary
       ↓
REVIEWER AGENT: Checks accuracy and adds citations
       ↓
USER GETS PERFECT ANSWER ✅
```

---

### 📊 Comparison Table:

| Feature | LLM | Agent | Agentic System |
|---------|-----|-------|----------------|
| Tool use | ❌ | ✅ | ✅ |
| Memory | ❌ | ✅ | ✅ |
| Planning | ❌ | ✅ | ✅ |
| Multiple AIs | ❌ | ❌ | ✅ |
| Can loop | ❌ | ✅ | ✅ |
| Complexity | Low | Medium | High |
| Cost | Low | Medium | High |

---

## 2.3 Agency Levels

### 🎚️ Think of Agency as a Dial (0 to 5)

Not all agents are the same. There is a **spectrum of how much autonomy** (freedom to decide) an agent has.

```
LOW AGENCY ←————————————————→ HIGH AGENCY
    0        1      2      3      4      5
  LLM      Fixed  Routed  Multi   Full   Full
  Only    Chain  Output  Step   Auto   Multi
                         Agent  Agent  Agent
```

Let me explain each level:

---

### 🔴 Level 0: Pure LLM (No Agency)

```
Input → LLM → Output
```

**Example:** ChatGPT answering a single question
**Human control:** 100%
**AI control:** 0%

---

### 🟠 Level 1: Fixed Workflow (Minimal Agency)

```
Input → Step 1 → Step 2 → Step 3 → Output
```

The steps are **pre-defined by a human**. The AI just fills in each step.

**Example:**
```
User Question 
    → Translate to English 
    → Answer in English 
    → Translate back
```

**Human control:** 90%
**AI control:** 10%

---

### 🟡 Level 2: Routing (Some Agency)

```
Input → LLM DECIDES ROUTE → Path A or Path B or Path C
```

The AI decides **which path** to take based on the input.

**Example:**
```
User Question
    → Is this a math question? → Go to math solver
    → Is this a coding question? → Go to code helper
    → Is this a web question? → Go to web searcher
```

**Human control:** 70%
**AI control:** 30%

---

### 🟢 Level 3: Multi-Step Agent (Good Agency)

```
Input → Plan → Act → Observe → Plan again → Act again → ...→ Output
```

The AI plans its own steps, uses tools, observes results, and decides what to do next.

**Example:** Our Perplexity clone! It decides what to search, reads results, decides if it needs more info, then answers.

**Human control:** 40%
**AI control:** 60%

---

### 🔵 Level 4: Full Autonomous Agent (High Agency)

The agent can:
- Set its own sub-goals
- Decide its own tools
- Work for long periods without human input
- Handle unexpected situations

**Example:** AutoGPT — you give it a big goal, it works for hours breaking it down.

**Human control:** 20%
**AI control:** 80%

---

### 🟣 Level 5: Multi-Agent System (Maximum Agency)

Multiple specialized agents collaborate, check each other, and complete complex tasks.

**Example:** A full research assistant that searches, reads, summarizes, fact-checks, formats, and publishes.

**Human control:** 10%
**AI control:** 90%

---

### ⚠️ Key Engineering Lesson:

> **Higher agency = more power BUT more risk and cost**

As an AI engineer, your job is to choose the **right level of agency** for the task. Not always maximum. Not always minimum. The right level.

```
Simple task (FAQ bot) → Level 0-1
Routing task (customer service) → Level 2
Research task (our project) → Level 3
Complex task (autonomous coding) → Level 4-5
```

---

# 🔄 CHAPTER 3: Workflows

---

## What is a Workflow?

**Simple definition:**
A workflow is a **planned sequence of steps** that an AI system follows to complete a task.

**Analogy:**
Think of a **recipe** in cooking:
1. Boil water
2. Add pasta
3. Cook 10 minutes
4. Drain water
5. Add sauce
6. Serve

The recipe is the workflow. Each step has a clear input and output. Steps happen in order.

In AI, workflows are patterns of how we **connect LLMs, tools, and logic** to solve problems.

---

## 3.1 Prompt Chaining

---

### What is Prompt Chaining?

**Simple explanation:**
Instead of asking one big complex question to an AI, you break the task into **small steps**, and the output of Step 1 becomes the input of Step 2, which becomes the input of Step 3, and so on.

**Like a chain:** 🔗→🔗→🔗→🔗

---

### 🏠 Real-World Analogy:

**Making a hamburger in a factory:**

```
STATION 1: Bake the bun
       ↓ (pass the bun to)
STATION 2: Cook the patty
       ↓ (pass bun + patty to)
STATION 3: Add vegetables
       ↓ (pass everything to)
STATION 4: Add sauce and wrap
       ↓
FINAL PRODUCT: Complete hamburger 🍔
```

Each station does ONE job well. The output passes to the next station.

**This is prompt chaining!**

---

### 📝 Simple Example — Research Paper Summary:

**Without chaining (bad approach):**
```
Prompt: "Read this 50-page paper, find the key ideas, 
         translate them to simple English, then create 
         bullet points, then make an executive summary, 
         then add relevant questions"
```
**Problem:** Too many instructions → AI gets confused → Bad output

---

**With chaining (good approach):**

```
STEP 1 PROMPT:
"Read this paper. Extract ONLY the key findings. 
Output: A list of findings."
        ↓ OUTPUT: [Finding 1, Finding 2, Finding 3...]

STEP 2 PROMPT:
"Here are the findings: [findings from step 1]
Translate each finding into simple English."
        ↓ OUTPUT: [Simple explanation 1, 2, 3...]

STEP 3 PROMPT:
"Here are the simple explanations: [from step 2]
Create 5 bullet points for an executive."
        ↓ OUTPUT: [Bullet 1, Bullet 2...]

STEP 4 PROMPT:
"Based on these bullets: [from step 3]
Write a 3-sentence executive summary."
        ↓ OUTPUT: Final clean summary ✅
```

---

### 💻 Code Example — Prompt Chaining:

```python
import openai

client = openai.OpenAI(api_key="your-api-key")

def call_llm(prompt, content):
    """
    Simple function to call an LLM.
    prompt = instructions for the AI
    content = the actual content to process
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content


def research_chain(user_question, web_results):
    """
    A 3-step prompt chain for our Perplexity agent.
    
    Step 1: Extract relevant facts from web results
    Step 2: Organize facts by importance  
    Step 3: Write final answer with citations
    """
    
    print("🔗 Starting Prompt Chain...")
    print("=" * 50)
    
    # ─── STEP 1: Extract relevant facts ───
    print("\n📌 Step 1: Extracting relevant facts...")
    
    step1_prompt = """
    You are a fact extractor.
    Given a user question and web search results,
    extract ONLY the facts that are relevant to the question.
    Output a numbered list of facts with their source URLs.
    Be precise. Do not add opinions.
    """
    
    step1_input = f"""
    User Question: {user_question}
    
    Web Results:
    {web_results}
    """
    
    facts = call_llm(step1_prompt, step1_input)
    print(f"Facts found:\n{facts}")
    
    # ─── STEP 2: Organize and rank facts ───
    print("\n📌 Step 2: Organizing facts by importance...")
    
    step2_prompt = """
    You are a fact organizer.
    Given a list of facts about a topic,
    organize them from most important to least important.
    Group related facts together.
    Remove any duplicate information.
    """
    
    organized_facts = call_llm(step2_prompt, facts)
    print(f"Organized facts:\n{organized_facts}")
    
    # ─── STEP 3: Write final answer ───
    print("\n📌 Step 3: Writing final answer...")
    
    step3_prompt = """
    You are a helpful research assistant like Perplexity.
    Given organized facts, write a clear, comprehensive answer
    to the user's question.
    - Use simple language
    - Add [Source 1], [Source 2] style citations
    - End with a "Sources:" section
    - Be direct and informative
    """
    
    step3_input = f"""
    Original Question: {user_question}
    
    Organized Facts:
    {organized_facts}
    """
    
    final_answer = call_llm(step3_prompt, step3_input)
    print(f"\n✅ Final Answer:\n{final_answer}")
    
    return final_answer


# ─── Example Usage ───
if __name__ == "__main__":
    question = "What are the latest developments in GPT-5?"
    
    # Simulated web results (in real project, this comes from search API)
    fake_web_results = """
    Result 1 (source: techcrunch.com):
    OpenAI announced GPT-5 with improved reasoning capabilities...
    
    Result 2 (source: openai.com):
    GPT-5 shows significant improvements in mathematics and coding...
    
    Result 3 (source: verge.com):
    Experts say GPT-5 represents a major leap in AI capabilities...
    """
    
    answer = research_chain(question, fake_web_results)
```

---

### ✅ When to Use Prompt Chaining:

| Situation | Use Chaining? |
|-----------|---------------|
| Complex multi-step task | ✅ Yes |
| Simple single question | ❌ No |
| When output quality matters | ✅ Yes |
| When you need to verify intermediate steps | ✅ Yes |
| Fast, simple response needed | ❌ No |

---

### ❌ When Prompt Chaining Fails:

1. **Error propagation** — If Step 1 makes a mistake, Step 2 and 3 will also be wrong (garbage in, garbage out)
2. **Cost** — Each step = one API call = more money
3. **Latency** — More steps = slower response
4. **Over-engineering** — Sometimes one good prompt is better than 5 chained prompts

---

## 3.2 Routing

---

### What is Routing?

**Simple definition:**
Routing means an AI (or logic) looks at the input and decides **which path or specialist** should handle it.

---

### 🏠 Real-World Analogy:

Imagine you call a **hospital's reception desk:**

```
You call: "I have a problem"
         ↓
Receptionist asks: "What kind of problem?"
         ↓
Chest pain? → Route to: Cardiology Department
Broken bone? → Route to: Orthopedics Department
Eye problem? → Route to: Ophthalmology Department
General checkup? → Route to: General Physician
```

The receptionist is the **router**. She doesn't treat you herself. She decides **who** should treat you.

---

### 📝 In Our Perplexity Agent:

```
User asks a question
        ↓
ROUTER analyzes the question
        ↓
Is it a MATH question? → Go to: Math solver tool
Is it a CODE question? → Go to: Code interpreter tool
Is it a CURRENT EVENT? → Go to: Web search tool
Is it GENERAL KNOWLEDGE? → Go to: LLM memory (no search needed)
Is it AMBIGUOUS? → Go to: Clarification handler
```

---

### 💻 Code Example — Routing:

```python
import openai
import json

client = openai.OpenAI(api_key="your-api-key")


def router(user_question):
    """
    The router looks at the question and decides
    which handler should process it.
    
    Returns one of:
    - "web_search"     → needs fresh internet data
    - "calculation"    → needs math computation
    - "code_help"      → needs code assistance
    - "general_knowledge" → LLM can answer from memory
    - "clarification"  → question is too vague
    """
    
    routing_prompt = """
    You are a question router for an AI assistant.
    
    Analyze the user's question and classify it into 
    EXACTLY ONE of these categories:
    
    1. "web_search" - needs current/real-time information
       Examples: news, prices, recent events, weather
       
    2. "calculation" - needs math computation
       Examples: "what is 15% of 340", "calculate compound interest"
       
    3. "code_help" - needs coding assistance
       Examples: "write a Python function", "fix this bug"
       
    4. "general_knowledge" - LLM knows this already
       Examples: "what is photosynthesis", "who wrote Hamlet"
       
    5. "clarification" - question is too vague to answer
       Examples: "tell me about stuff", "help me"
    
    Respond in JSON format ONLY:
    {
        "route": "category_name",
        "reason": "one sentence explanation",
        "confidence": 0.0 to 1.0
    }
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": routing_prompt},
            {"role": "user", "content": user_question}
        ],
        response_format={"type": "json_object"}  # Force JSON output
    )
    
    result = json.loads(response.choices[0].message.content)
    return result


def handle_web_search(question):
    """Handler for web search questions"""
    print(f"🌐 Routing to: Web Search Handler")
    # In real project: call Tavily/SerpAPI here
    return f"[Web search results for: {question}]"


def handle_calculation(question):
    """Handler for math questions"""
    print(f"🔢 Routing to: Calculation Handler")
    # In real project: call a calculator tool
    return f"[Calculation result for: {question}]"


def handle_code(question):
    """Handler for coding questions"""
    print(f"💻 Routing to: Code Helper")
    return f"[Code solution for: {question}]"


def handle_general(question):
    """Handler for general knowledge"""
    print(f"🧠 Routing to: General Knowledge (LLM Memory)")
    return f"[General answer for: {question}]"


def handle_clarification(question):
    """Handler for vague questions"""
    print(f"❓ Routing to: Clarification Handler")
    return "Could you please be more specific about what you want to know?"


def main_router_system(user_question):
    """
    The complete routing system.
    Analyzes question → routes → handles → returns answer.
    """
    
    print(f"\n📩 User Question: {user_question}")
    print("=" * 50)
    
    # Step 1: Analyze and route
    routing_decision = router(user_question)
    print(f"\n🔀 Routing Decision:")
    print(f"   Route: {routing_decision['route']}")
    print(f"   Reason: {routing_decision['reason']}")
    print(f"   Confidence: {routing_decision['confidence']}")
    
    # Step 2: Send to correct handler
    route = routing_decision['route']
    
    if route == "web_search":
        answer = handle_web_search(user_question)
    elif route == "calculation":
        answer = handle_calculation(user_question)
    elif route == "code_help":
        answer = handle_code(user_question)
    elif route == "general_knowledge":
        answer = handle_general(user_question)
    elif route == "clarification":
        answer = handle_clarification(user_question)
    else:
        answer = handle_general(user_question)  # Default fallback
    
    print(f"\n✅ Answer: {answer}")
    return answer


# ─── Test the router ───
if __name__ == "__main__":
    
    test_questions = [
        "What is the latest news about Tesla?",        # → web_search
        "What is 25% of 480?",                         # → calculation
        "Write a Python function to reverse a string", # → code_help
        "What is the speed of light?",                 # → general_knowledge
        "Tell me stuff"                                # → clarification
    ]
    
    for q in test_questions:
        main_router_system(q)
        print("\n" + "="*60 + "\n")
```

---

### ✅ Routing Best Practices:

```
1. Keep routes CLEAR and DISTINCT — no overlap
2. Always have a DEFAULT fallback route
3. Use CONFIDENCE scores — if low, ask for clarification
4. Test edge cases — what about questions that fit 2 routes?
5. Monitor routing decisions in production to catch errors
```

---

## 3.3 Parallelization

---

### What is Parallelization?

**Simple definition:**
Instead of doing tasks one after another (sequential), you do multiple tasks **at the same time** (parallel) and then combine the results.

---

### 🏠 Real-World Analogy:

**Sequential (slow):**
```
One chef in a kitchen:
Cook rice → (wait 20 min) → Cook chicken → (wait 30 min) → Make salad → (wait 10 min)
Total time: 60 minutes 😴
```

**Parallel (fast):**
```
Three chefs in a kitchen at the SAME TIME:
Chef 1: Cook rice (20 min)    ─┐
Chef 2: Cook chicken (30 min)  ├─→ All done in 30 min! 🚀
Chef 3: Make salad (10 min)   ─┘
```

**In AI:** Run multiple LLM calls simultaneously, then combine results.

---

### Two Types of Parallelization:

### Type 1: Sectioning (Divide and Conquer)

**Idea:** Break a big task into pieces. Process each piece at the same time. Combine results.

**Example for our Perplexity agent:**

```
User asks: "Compare iPhone 15, Samsung S24, and Pixel 8"

SEQUENTIAL (slow):
Research iPhone 15 → (3 sec)
Research Samsung S24 → (3 sec)  
Research Pixel 8 → (3 sec)
Total: 9 seconds 😴

PARALLEL with Sectioning (fast):
Research iPhone 15  ─┐
Research Samsung S24 ├─→ All done in 3 seconds! 🚀
Research Pixel 8    ─┘
Combine results → Write comparison
```

---

### Type 2: Voting (Multiple Perspectives)

**Idea:** Run the same task through multiple LLMs or prompts. Take the majority answer or best answer.

**Why?** One LLM might make a mistake. Multiple LLMs voting is more reliable.

**Example:**

```
Question: "Is this news article factually accurate?"

LLM 1 analysis: "Contains 2 inaccuracies → UNRELIABLE" 
LLM 2 analysis: "Mostly accurate → RELIABLE"
LLM 3 analysis: "Contains 1 inaccuracy → UNRELIABLE"

Voting result: 2 vs 1 → UNRELIABLE (majority wins)
```

This is like a **jury system** — multiple judges reduce the chance of one bad decision.

---

### 💻 Code Example — Parallelization:

```python
import asyncio
import openai
from typing import List

client = openai.AsyncOpenAI(api_key="your-api-key")  # Async client!


# ═══════════════════════════════════════
# TYPE 1: SECTIONING
# ═══════════════════════════════════════

async def research_one_topic(topic: str, question: str) -> dict:
    """
    Research ONE specific topic asynchronously.
    Returns a dict with topic and findings.
    """
    prompt = f"""
    Research the following aspect: {topic}
    In context of the question: {question}
    Provide 3-5 key facts. Be concise.
    """
    
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return {
        "topic": topic,
        "findings": response.choices[0].message.content
    }


async def parallel_research(question: str, topics: List[str]) -> str:
    """
    Research multiple topics AT THE SAME TIME (parallel).
    Then combine all findings into one answer.
    """
    
    print(f"\n🔀 Starting Parallel Research for: {question}")
    print(f"📚 Topics to research simultaneously: {topics}")
    print("=" * 50)
    
    # Create all research tasks at the same time
    tasks = [research_one_topic(topic, question) for topic in topics]
    
    # Run ALL tasks simultaneously using asyncio.gather
    print("\n⚡ Running all research tasks in parallel...")
    results = await asyncio.gather(*tasks)
    
    print(f"\n✅ All {len(topics)} topics researched!")
    
    # Combine all findings
    combined = "\n\n".join([
        f"**{r['topic']}:**\n{r['findings']}" 
        for r in results
    ])
    
    # Final synthesis
    synthesis_response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Synthesize the research findings into one coherent answer."
            },
            {
                "role": "user", 
                "content": f"Question: {question}\n\nResearch Findings:\n{combined}"
            }
        ]
    )
    
    return synthesis_response.choices[0].message.content


# ═══════════════════════════════════════
# TYPE 2: VOTING
# ═══════════════════════════════════════

async def single_vote(question: str, perspective: str) -> str:
    """
    Get one 'vote' from one perspective.
    """
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"You are analyzing from this perspective: {perspective}. Be honest and critical."
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )
    return response.choices[0].message.content


async def voting_system(question: str) -> str:
    """
    Run the same question through multiple perspectives simultaneously.
    Then have a judge decide the best combined answer.
    """
    
    perspectives = [
        "a skeptical scientist who questions everything",
        "an optimistic tech enthusiast",
        "a practical engineer focused on real-world use"
    ]
    
    print(f"\n🗳️  Voting System Starting...")
    print(f"Question: {question}")
    print(f"Running {len(perspectives)} perspectives simultaneously...")
    
    # All votes happen at the same time
    tasks = [single_vote(question, p) for p in perspectives]
    votes = await asyncio.gather(*tasks)
    
    # Show all votes
    for i, (perspective, vote) in enumerate(zip(perspectives, votes)):
        print(f"\n📊 Vote {i+1} ({perspective}):\n{vote[:200]}...")
    
    # Judge synthesizes all votes
    all_votes_text = "\n\n".join([
        f"Perspective {i+1} ({p}):\n{v}" 
        for i, (p, v) in enumerate(zip(perspectives, votes))
    ])
    
    judge_response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """
                You are a neutral judge.
                Read all perspectives and create a balanced, 
                comprehensive answer that captures the best insights
                from all viewpoints.
                """
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nAll Perspectives:\n{all_votes_text}"
            }
        ]
    )
    
    return judge_response.choices[0].message.content


# ─── Run examples ───
async def main():
    
    # Example 1: Sectioning
    question = "Compare iPhone 15, Samsung S24, and Google Pixel 8"
    topics = [
        "iPhone 15 specifications and unique features",
        "Samsung S24 specifications and unique features", 
        "Google Pixel 8 specifications and unique features"
    ]
    
    result1 = await parallel_research(question, topics)
    print(f"\n✅ SECTIONING RESULT:\n{result1}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Voting
    question2 = "Is AI going to replace software engineers in 5 years?"
    result2 = await voting_system(question2)
    print(f"\n✅ VOTING RESULT:\n{result2}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3.4 Reflection

---

### What is Reflection?

**Simple definition:**
The agent generates an answer, then **looks at its own answer critically**, finds problems with it, and **improves it** — like a human checking their own work before submitting.

---

### 🏠 Real-World Analogy:

**A student writing an essay:**

```
STEP 1: Write first draft
STEP 2: Read it again → "This paragraph is unclear"
STEP 3: Improve that paragraph
STEP 4: Read again → "Missing a conclusion"
STEP 5: Add conclusion
STEP 6: Read again → "Looks good now"
STEP 7: Submit ✅
```

This **self-checking loop** is reflection!

---

### 📊 Reflection Flow Diagram:

```
User Question
     ↓
Generate Initial Answer
     ↓
REFLECT: "Is this answer good?"
     ↓
Is it good? ──YES──→ Return Answer ✅
     │
    NO
     ↓
What's wrong? (critique)
     ↓
Improve the answer
     ↓
REFLECT again... (loop)
     ↓
[After max iterations] → Return best answer
```

---

### 💻 Code Example — Reflection:

```python
import openai

client = openai.OpenAI(api_key="your-api-key")


def generate_answer(question: str, context: str = "") -> str:
    """Generate an initial answer to the question."""
    
    prompt = f"""
    Answer the following question clearly and accurately.
    {f'Context: {context}' if context else ''}
    
    Question: {question}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def reflect_on_answer(question: str, answer: str) -> dict:
    """
    Critically evaluate the answer.
    Returns a dict with:
    - is_good: True/False
    - score: 1-10
    - problems: list of issues
    - suggestions: list of improvements
    """
    
    reflection_prompt = """
    You are a critical quality checker for AI-generated answers.
    
    Evaluate the given answer for the given question.
    
    Check for:
    1. Accuracy - Is information correct?
    2. Completeness - Does it fully answer the question?
    3. Clarity - Is it easy to understand?
    4. Sources - Does it cite evidence when needed?
    5. Conciseness - Is it too long or too short?
    
    Respond in this exact format:
    SCORE: [1-10]
    IS_GOOD: [YES/NO] (YES if score >= 7)
    PROBLEMS:
    - [problem 1]
    - [problem 2]
    SUGGESTIONS:
    - [suggestion 1]
    - [suggestion 2]
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": reflection_prompt},
            {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer}"}
        ]
    )
    
    content = response.choices[0].message.content
    
    # Parse the response
    lines = content.strip().split('\n')
    score = 5
    is_good = False
    problems = []
    suggestions = []
    
    current_section = None
    for line in lines:
        if line.startswith("SCORE:"):
            try:
                score = int(line.split(":")[1].strip())
            except:
                score = 5
        elif line.startswith("IS_GOOD:"):
            is_good = "YES" in line
        elif line.startswith("PROBLEMS:"):
            current_section = "problems"
        elif line.startswith("SUGGESTIONS:"):
            current_section = "suggestions"
        elif line.startswith("- "):
            if current_section == "problems":
                problems.append(line[2:])
            elif current_section == "suggestions":
                suggestions.append(line[2:])
    
    return {
        "score": score,
        "is_good": is_good,
        "problems": problems,
        "suggestions": suggestions,
        "raw_feedback": content
    }


def improve_answer(question: str, answer: str, critique: dict) -> str:
    """
    Improve the answer based on the critique.
    """
    
    problems_text = "\n".join([f"- {p}" for p in critique["problems"]])
    suggestions_text = "\n".join([f"- {s}" for s in critique["suggestions"]])
    
    improvement_prompt = f"""
    You are improving an answer based on feedback.
    
    Original Question: {question}
    
    Previous Answer:
    {answer}
    
    Problems found:
    {problems_text}
    
    Suggested improvements:
    {suggestions_text}
    
    Please write an improved version that fixes all these problems.
    Keep what was good, fix what was bad.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": improvement_prompt}]
    )
    return response.choices[0].message.content


def reflection_loop(question: str, max_iterations: int = 3) -> str:
    """
    The full reflection loop:
    Generate → Reflect → Improve → Reflect → Improve → ...
    
    Stops when:
    - Answer is good enough (score >= 7)
    - OR max iterations reached
    """
    
    print(f"\n🤔 Reflection Loop Starting")
    print(f"Question: {question}")
    print(f"Max iterations: {max_iterations}")
    print("=" * 50)
    
    # Step 1: Generate initial answer
    print("\n📝 Iteration 1: Generating initial answer...")
    current_answer = generate_answer(question)
    print(f"Initial answer:\n{current_answer[:300]}...")
    
    # Reflection loop
    for iteration in range(max_iterations):
        
        print(f"\n🔍 Reflecting on answer (iteration {iteration + 1})...")
        
        # Reflect
        critique = reflect_on_answer(question, current_answer)
        
        print(f"📊 Score: {critique['score']}/10")
        print(f"✅ Good enough: {critique['is_good']}")
        print(f"⚠️  Problems found: {len(critique['problems'])}")
        
        # Check if good enough
        if critique['is_good']:
            print(f"\n🎉 Answer is good enough! (Score: {critique['score']}/10)")
            print("Stopping reflection loop.")
            break
        
        # If not good enough and we have more iterations
        if iteration < max_iterations - 1:
            print(f"\n✏️  Improving answer based on feedback...")
            current_answer = improve_answer(question, current_answer, critique)
            print(f"Improved answer:\n{current_answer[:300]}...")
        else:
            print(f"\n⏰ Max iterations reached. Returning best answer.")
    
    print(f"\n✅ FINAL ANSWER:\n{current_answer}")
    return current_answer


# ─── Test reflection ───
if __name__ == "__main__":
    question = "Explain how neural networks learn, for a complete beginner."
    final = reflection_loop(question, max_iterations=3)
```

---

## 3.5 Orchestrator-Worker Pattern

---

### What is the Orchestrator-Worker Pattern?

**Simple definition:**
One **Orchestrator** (manager) receives the big task, breaks it into subtasks, assigns them to **Workers** (specialists), collects their results, and produces the final output.

---

### 🏠 Real-World Analogy:

**A news magazine production:**

```
EDITOR-IN-CHIEF (Orchestrator):
"We're writing an article about climate change"
         ↓
Assigns tasks to specialists:
         ↓
         ├── Reporter 1 (Worker): Research latest climate data
         ├── Reporter 2 (Worker): Interview scientists
         ├── Photographer (Worker): Find relevant images
         ├── Fact-checker (Worker): Verify all claims
         └── Designer (Worker): Create infographics
         ↓
All workers submit their work
         ↓
EDITOR-IN-CHIEF: Combines everything into final article
         ↓
Final article published ✅
```

---

### 📊 In Our Perplexity Agent:

```
USER: "Write a comprehensive report on AI trends in 2025"

ORCHESTRATOR AGENT:
"This is a big task. I'll break it into parts."
         ↓
Creates plan:
  Task 1: Search for AI hardware trends
  Task 2: Search for AI software/model trends  
  Task 3: Search for AI business adoption trends
  Task 4: Search for AI regulation trends
         ↓
Sends to Workers (in parallel):
  Worker 1: [Searches hardware] → Returns findings
  Worker 2: [Searches software] → Returns findings
  Worker 3: [Searches business] → Returns findings
  Worker 4: [Searches regulation] → Returns findings
         ↓
ORCHESTRATOR: 
  Receives all 4 results
  Combines into structured report
  Adds citations
         ↓
Final comprehensive report ✅
```

---

### 💻 Code Example — Orchestrator-Worker:

```python
import asyncio
import openai
from typing import List, Dict

client = openai.AsyncOpenAI(api_key="your-api-key")


class Worker:
    """
    A Worker agent that handles one specific subtask.
    Each worker is a specialist.
    """
    
    def __init__(self, worker_id: str, specialty: str):
        self.worker_id = worker_id
        self.specialty = specialty
    
    async def execute(self, subtask: str) -> Dict:
        """
        Execute the given subtask.
        In real project: this would call search APIs, code tools, etc.
        """
        print(f"  🔧 Worker {self.worker_id} ({self.specialty}): Starting task...")
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a specialist in {self.specialty}. Be thorough and accurate."
                },
                {
                    "role": "user",
                    "content": subtask
                }
            ]
        )
        
        result = response.choices[0].message.content
        print(f"  ✅ Worker {self.worker_id}: Task complete!")
        
        return {
            "worker_id": self.worker_id,
            "specialty": self.specialty,
            "subtask": subtask,
            "result": result
        }


class Orchestrator:
    """
    The Orchestrator agent that manages the whole process:
    1. Receives the big task
    2. Creates a plan (breaks into subtasks)
    3. Assigns subtasks to workers
    4. Collects results
    5. Synthesizes final output
    """
    
    def __init__(self):
        self.workers = [
            Worker("W1", "web research and fact-finding"),
            Worker("W2", "data analysis and statistics"),
            Worker("W3", "expert opinion and quotes"),
            Worker("W4", "recent news and current events")
        ]
    
    async def create_plan(self, main_task: str) -> List[str]:
        """
        The orchestrator thinks about the task and
        breaks it into subtasks for workers.
        """
        
        planning_prompt = f"""
        You are a task planner. 
        Break this main task into exactly 4 specific subtasks.
        Each subtask should be independent and assignable to a specialist.
        
        Main Task: {main_task}
        
        Output exactly 4 subtasks, one per line, numbered 1-4.
        Make each subtask specific and actionable.
        """
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": planning_prompt}]
        )
        
        plan_text = response.choices[0].message.content
        
        # Parse into list
        lines = plan_text.strip().split('\n')
        subtasks = []
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering
                cleaned = line.lstrip('0123456789.-) ').strip()
                if cleaned:
                    subtasks.append(cleaned)
        
        return subtasks[:4]  # Max 4 subtasks
    
    async def synthesize(self, main_task: str, worker_results: List[Dict]) -> str:
        """
        Combine all worker results into a final comprehensive answer.
        """
        
        all_results = "\n\n".join([
            f"**{r['specialty'].upper()}:**\n{r['result']}"
            for r in worker_results
        ])
        
        synthesis_prompt = f"""
        You are a senior research synthesizer.
        
        Main Task: {main_task}
        
        Worker Research Results:
        {all_results}
        
        Create a comprehensive, well-structured final report that:
        1. Integrates all worker findings coherently
        2. Uses clear headings and sections
        3. Highlights the most important insights
        4. Is written for a general audience
        5. Ends with a brief conclusion
        """
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        
        return response.choices[0].message.content
    
    async def run(self, main_task: str) -> str:
        """
        The main orchestration flow.
        """
        
        print(f"\n🎯 ORCHESTRATOR: Received task")
        print(f"Task: {main_task}")
        print("=" * 60)
        
        # Step 1: Create plan
        print("\n📋 Step 1: Creating execution plan...")
        subtasks = await self.create_plan(main_task)
        
        print(f"Plan created with {len(subtasks)} subtasks:")
        for i, task in enumerate(subtasks, 1):
            print(f"  {i}. {task}")
        
        # Step 2: Assign to workers and run in parallel
        print(f"\n⚡ Step 2: Assigning tasks to {len(self.workers)} workers (parallel)...")
        
        # Match subtasks to workers
        worker_tasks = []
        for i, (worker, subtask) in enumerate(zip(self.workers, subtasks)):
            worker_tasks.append(worker.execute(subtask))
        
        # Run all workers simultaneously
        worker_results = await asyncio.gather(*worker_tasks)
        
        print(f"\n✅ All {len(worker_results)} workers completed!")
        
        # Step 3: Synthesize
        print("\n🔗 Step 3: Synthesizing all results...")
        final_report = await self.synthesize(main_task, list(worker_results))
        
        print(f"\n🎉 ORCHESTRATOR: Final report ready!")
        print("=" * 60)
        print(final_report)
        
        return final_report


# ─── Run the orchestrator-worker system ───
async def main():
    orchestrator = Orchestrator()
    
    task = "Create a comprehensive overview of artificial intelligence trends in 2025"
    
    report = await orchestrator.run(task)
    return report


if __name__ == "__main__":
    asyncio.run(main())
```

---

# 🔧 CHAPTER 4: Tools

---

## 4.1 What is Tool Calling?

---

### The Problem Without Tools:

Imagine an LLM as an extremely smart person who is **locked in a room with no internet, no phone, no calculator, no calendar.**

They can answer questions from memory, but they cannot:
- Search the web (don't know today's news)
- Do complex math (might make errors)
- Check today's date (no calendar)
- Read files (can't access your computer)
- Send emails (no phone)

**This is the limitation of a raw LLM.**

---

### The Solution — Tools:

Now imagine you **pass notes under the door to that person:**
- A printed web search result
- A calculator output
- Today's newspaper
- The content of a file

They can now use that information to give much better answers!

**Tools are these "notes under the door"** — they extend what the LLM can do.

---

### 🏠 Real-World Analogy:

**A doctor WITHOUT tools:**
- Can diagnose from symptoms alone
- Limited by what they remember
- Cannot see inside the body

**A doctor WITH tools:**
- X-ray machine → sees bones
- Blood test → sees chemistry
- MRI scanner → sees soft tissue
- Computer → looks up research

**Tools transform a capable person into a super-capable person.**

Same with LLMs!

---

### What Kinds of Tools Can an LLM Use?

```
INFORMATION TOOLS:
├── Web search (Google, Bing, Tavily)
├── Wikipedia lookup
├── News API
└── Database query

COMPUTATION TOOLS:
├── Calculator / Math engine
├── Code interpreter (run Python)
├── Unit converter
└── Currency converter

FILE TOOLS:
├── Read PDF / Word / CSV
├── Write to file
├── Image analysis
└── Audio transcription

COMMUNICATION TOOLS:
├── Send email
├── Send Slack message
├── Post to Twitter
└── Make API call

MEMORY TOOLS:
├── Save to memory database
├── Retrieve from memory
├── Update notes
└── Search past conversations
```

---

### How Does Tool Calling Actually Work?

This is the **most important mechanism** to understand. Let me show you step by step.

```
STEP 1: You give the LLM a question AND a list of available tools

STEP 2: The LLM DECIDES if it needs a tool or can answer directly

STEP 3: If it needs a tool, it outputs a "tool call" 
        (not the answer — just the instruction to call the tool)

STEP 4: YOUR CODE receives the tool call instruction

STEP 5: YOUR CODE actually runs the tool (searches web, etc.)

STEP 6: YOUR CODE sends the tool result back to the LLM

STEP 7: The LLM reads the result and writes the final answer
```

**Key insight:** The LLM does NOT run the tools itself. It just tells you WHICH tool to call and WITH WHAT ARGUMENTS. **You** (your Python code) actually execute the tool and return the result.

---

## 4.2 Tool Formatting

---

### How Do We Tell the LLM About Available Tools?

We use a **structured format** (usually JSON) to describe each tool.

Think of it like a **job posting** for a worker:
- What is the tool's name?
- What does it do? (description)
- What information does it need? (parameters)
- What type is each parameter? (string, number, etc.)
- Which parameters are required?

---

### 📝 Tool Definition Format (OpenAI Style):

```python
# This is how you define a tool for the LLM to use

web_search_tool = {
    "type": "function",           # It's a function/tool
    "function": {
        "name": "search_web",     # The name of the function
        
        "description": """
            Search the internet for current information.
            Use this when you need:
            - Current news or events
            - Real-time data (prices, weather, scores)
            - Information that might have changed recently
            - Specific facts you're not sure about
            DO NOT use for simple general knowledge questions.
        """,
        
        "parameters": {
            "type": "object",
            "properties": {
                
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific and clear. Example: 'OpenAI GPT-5 release date 2025'"
                },
                
                "num_results": {
                    "type": "integer",
                    "description": "Number of search results to return. Default 5. Max 10.",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                },
                
                "search_type": {
                    "type": "string",
                    "enum": ["general", "news", "academic"],
                    "description": "Type of search: 'general' for normal search, 'news' for recent news, 'academic' for research papers",
                    "default": "general"
                }
            },
            
            "required": ["query"]  # Only query is required
        }
    }
}


# Another tool: Calculator
calculator_tool = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": """
            Perform mathematical calculations.
            Use this for ANY math: arithmetic, percentages, 
            statistics, unit conversions.
            Always use this instead of calculating in your head.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate. Example: '(150 * 0.15) + 45'"
                }
            },
            "required": ["expression"]
        }
    }
}


# Another tool: Get current date/time
datetime_tool = {
    "type": "function",
    "function": {
        "name": "get_current_datetime",
        "description": "Get the current date and time. Use this when the user asks about today's date or current time.",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Timezone like 'UTC', 'US/Eastern', 'Asia/Dhaka'. Default: 'UTC'",
                    "default": "UTC"
                }
            },
            "required": []  # No required parameters!
        }
    }
}

# List of all tools to give to the LLM
ALL_TOOLS = [web_search_tool, calculator_tool, datetime_tool]
```

---

### 🔑 Key Rules for Good Tool Descriptions:

```
1. Name should be clear and descriptive
   ✅ "search_web"    ❌ "tool1"
   ✅ "calculate"     ❌ "math"

2. Description should tell WHEN to use it
   ✅ "Use when you need current news"
   ❌ "Searches the web"

3. Parameter descriptions should include examples
   ✅ "Example: 'Tesla stock price today'"
   ❌ "The query"

4. Mark required vs optional parameters clearly

5. Use enums for parameters with fixed options
   ✅ "enum": ["news", "general", "academic"]
```

---

## 4.3 Tool Execution

---

### The Complete Tool Execution Flow:

```python
import openai
import json
import math
from datetime import datetime
import pytz

client = openai.OpenAI(api_key="your-api-key")


# ═══════════════════════════════════════════════════
# STEP 1: Define the ACTUAL tool functions
# (These are real Python functions that do real work)
# ═══════════════════════════════════════════════════

def search_web(query: str, num_results: int = 5, search_type: str = "general") -> str:
    """
    ACTUAL web search function.
    In production: uses Tavily API or SerpAPI.
    Here: we simulate it for teaching.
    """
    # In production, you'd use:
    # from tavily import TavilyClient
    # tavily = TavilyClient(api_key="...")
    # results = tavily.search(query=query, max_results=num_results)
    
    print(f"  🌐 [TOOL EXECUTING] search_web('{query}', num_results={num_results})")
    
    # Simulated results for teaching
    simulated_results = f"""
    Search results for: "{query}"
    
    Result 1: [techcrunch.com] Latest developments in {query}...
    Key findings: Important updates found regarding {query}
    
    Result 2: [reuters.com] Breaking news about {query}...
    Key findings: Multiple sources confirm {query} details
    
    Result 3: [wikipedia.org] Background information on {query}...
    Key findings: Historical context and basic facts
    """
    
    return simulated_results


def calculate(expression: str) -> str:
    """
    ACTUAL calculator function.
    Safely evaluates mathematical expressions.
    """
    print(f"  🔢 [TOOL EXECUTING] calculate('{expression}')")
    
    try:
        # Safe evaluation — only allow math operations
        allowed_names = {
            k: v for k, v in math.__dict__.items() 
            if not k.startswith("__")
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"


def get_current_datetime(timezone: str = "UTC") -> str:
    """
    ACTUAL datetime function.
    Returns current date and time in specified timezone.
    """
    print(f"  🕐 [TOOL EXECUTING] get_current_datetime(timezone='{timezone}')")
    
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return f"Current time in {timezone}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    except Exception as e:
        now = datetime.utcnow()
        return f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}"


# ═══════════════════════════════════════════════════
# STEP 2: Tool Registry — Maps tool names to functions
# ═══════════════════════════════════════════════════

TOOL_REGISTRY = {
    "search_web": search_web,
    "calculate": calculate,
    "get_current_datetime": get_current_datetime
}


# ═══════════════════════════════════════════════════
# STEP 3: Tool definitions for the LLM
# ═══════════════════════════════════════════════════

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the internet for current information. Use for news, recent events, real-time data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "default": 5},
                    "search_type": {
                        "type": "string",
                        "enum": ["general", "news", "academic"],
                        "default": "general"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform mathematical calculations. Always use for any math.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Get current date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "default": "UTC"}
                },
                "required": []
            }
        }
    }
]


# ═══════════════════════════════════════════════════
# STEP 4: The Tool Executor — handles the loop
# ═══════════════════════════════════════════════════

def execute_tool_call(tool_call) -> str:
    """
    When the LLM says "call this tool with these arguments",
    this function actually executes it.
    
    Returns the result as a string to send back to the LLM.
    """
    
    # Get the tool name and arguments from the LLM's request
    tool_name = tool_call.function.name
    
    # Parse the JSON arguments string
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return "Error: Could not parse tool arguments"
    
    print(f"\n🔧 LLM requested tool: '{tool_name}'")
    print(f"   Arguments: {arguments}")
    
    # Look up the actual function in registry
    if tool_name not in TOOL_REGISTRY:
        return f"Error: Unknown tool '{tool_name}'"
    
    tool_function = TOOL_REGISTRY[tool_name]
    
    # Call the function with the arguments
    try:
        result = tool_function(**arguments)
        print(f"   Result: {result[:100]}...")  # Show first 100 chars
        return result
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


# ═══════════════════════════════════════════════════
# STEP 5: The Main Agent Loop
# ═══════════════════════════════════════════════════

def agent_with_tools(user_question: str) -> str:
    """
    The complete agent with tool calling.
    
    Loop:
    1. Send question to LLM with available tools
    2. If LLM wants a tool → execute it → send result back
    3. If LLM gives final answer → return it
    4. Repeat until done
    """
    
    print(f"\n{'='*60}")
    print(f"🤖 AGENT STARTING")
    print(f"Question: {user_question}")
    print(f"{'='*60}")
    
    # Conversation history — starts with user question
    messages = [
        {
            "role": "system",
            "content": """
            You are a helpful AI assistant like Perplexity.
            Use your tools whenever you need current information or calculations.
            Always cite sources when using web search results.
            Be clear, accurate, and helpful.
            """
        },
        {
            "role": "user",
            "content": user_question
        }
    ]
    
    iteration = 0
    max_iterations = 10  # Safety limit to prevent infinite loops
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 Agent Iteration {iteration}")
        
        # Call the LLM
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"  # LLM decides whether to use tools
        )
        
        # Get the LLM's response
        response_message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        
        print(f"   LLM finish reason: {finish_reason}")
        
        # Add LLM's response to message history
        messages.append(response_message)
        
        # Check if LLM wants to use tools
        if finish_reason == "tool_calls" and response_message.tool_calls:
            
            print(f"   LLM wants to use {len(response_message.tool_calls)} tool(s)")
            
            # Execute each requested tool
            for tool_call in response_message.tool_calls:
                
                # Execute the tool
                tool_result = execute_tool_call(tool_call)
                
                # Add tool result to message history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
            
            # Continue the loop — LLM will now process tool results
            continue
        
        # If LLM gave a final answer (not a tool call)
        elif finish_reason == "stop":
            
            final_answer = response_message.content
            print(f"\n✅ FINAL ANSWER:")
            print("="*60)
            print(final_answer)
            print("="*60)
            
            return final_answer
        
        else:
            print(f"Unexpected finish reason: {finish_reason}")
            break
    
    return "Max iterations reached without final answer."


# ─── Test the agent ───
if __name__ == "__main__":
    
    # Test 1: Web search question
    agent_with_tools("What are the latest AI developments in 2025?")
    
    # Test 2: Math question
    agent_with_tools("What is 15% tip on a $87.50 restaurant bill?")
    
    # Test 3: Date question
    agent_with_tools("What time is it right now in Dhaka, Bangladesh?")
    
    # Test 4: Mixed — needs both search AND calculation
    agent_with_tools("What is the current price of Bitcoin, and what would $500 worth be?")
```

---

## 4.4 MCP — Model Context Protocol

---

### What is MCP?

**Simple definition:**
MCP (Model Context Protocol) is a **standard way** for AI models to connect to tools and data sources — like a universal plug standard.

---

### 🏠 Real-World Analogy:

**Before USB (no standard):**
- Every device had a DIFFERENT plug
- Your printer plug didn't fit your camera
- Your phone charger didn't fit your laptop
- You needed 10 different cables

**After USB (universal standard):**
- One standard plug
- Works with EVERYTHING
- Plug any device into any port

**MCP is the "USB standard" for AI tools.**

---

### The Problem MCP Solves:

**Without MCP:**
```
Developer A builds a web search tool → Works only with OpenAI
Developer B builds a calculator → Works only with Claude
Developer C builds a file reader → Works only with Gemini

Result: Every AI company reinvents the same tools
        Tools don't work across different AI systems
        Huge waste of effort
```

**With MCP:**
```
Developer builds a web search tool → Works with ALL AI models
MCP defines HOW tools communicate
ANY AI model + ANY MCP tool = Works together ✅

Result: Build once, use everywhere
        Standard interface
        Massive tool ecosystem
```

---

### How MCP Works:

```
┌─────────────────────────────────────────┐
│           MCP ARCHITECTURE              │
│                                         │
│  ┌─────────┐    MCP Protocol   ┌──────┐│
│  │   LLM   │ ←─────────────→  │ Tool ││
│  │ (Claude,│                   │Server││
│  │  GPT,   │    Standard       │      ││
│  │ Gemini) │    JSON-RPC       │Web   ││
│  │         │    Messages       │Search││
│  └─────────┘                   │Files ││
│                                │DB    ││
│                                └──────┘│
└─────────────────────────────────────────┘
```

**MCP uses JSON-RPC** (a simple way to call functions over a network) as its communication standard.

---

### MCP Message Flow:

```
1. LLM → MCP Server: "What tools do you have?"
   (tools/list request)

2. MCP Server → LLM: "I have: search_web, read_file, query_db"
   (tools/list response)

3. LLM → MCP Server: "Call search_web with query='AI news'"
   (tools/call request)

4. MCP Server: Executes the actual search
   (server does the work)

5. MCP Server → LLM: "Here are the search results: ..."
   (tools/call response)

6. LLM: Uses results to formulate final answer
```

---

### 💻 Simple MCP Server Example:

```python
# Simple MCP server concept
# In production: use the actual 'mcp' Python library

import json
from typing import Any, Dict

class SimpleMCPServer:
    """
    A simplified MCP server that follows the MCP protocol.
    This shows the CONCEPT — production uses the official MCP SDK.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.tools = {}  # Registry of available tools
    
    def register_tool(self, name: str, description: str, 
                       handler_func, parameters: Dict):
        """Register a tool with this MCP server."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler_func
        }
        print(f"✅ Tool registered: {name}")
    
    def list_tools(self) -> Dict:
        """
        MCP tools/list response.
        Tells the LLM what tools are available.
        """
        return {
            "tools": [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": tool["parameters"]
                }
                for tool in self.tools.values()
            ]
        }
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """
        MCP tools/call response.
        Actually executes the requested tool.
        """
        
        if tool_name not in self.tools:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]
            }
        
        try:
            tool = self.tools[tool_name]
            result = tool["handler"](**arguments)
            
            return {
                "isError": False,
                "content": [{"type": "text", "text": str(result)}]
            }
        except Exception as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: {str(e)}"}]
            }
    
    def handle_request(self, request: Dict) -> Dict:
        """
        Handle incoming MCP requests.
        Routes to correct handler based on method.
        """
        method = request.get("method")
        
        if method == "tools/list":
            return self.list_tools()
        
        elif method == "tools/call":
            params = request.get("params", {})
            return self.call_tool(
                tool_name=params.get("name"),
                arguments=params.get("arguments", {})
            )
        
        else:
            return {"error": f"Unknown method: {method}"}


# ─── Create and populate an MCP server ───

def create_perplexity_mcp_server():
    """Create an MCP server for our Perplexity agent."""
    
    server = SimpleMCPServer("perplexity-tools")
    
    # ── Tool 1: Web Search ──
    def web_search_handler(query: str, max_results: int = 5) -> str:
        # In production: call Tavily API
        return f"Search results for '{query}': [Result 1, Result 2, Result 3]"
    
    server.register_tool(
        name="web_search",
        description="Search the web for current information",
        handler_func=web_search_handler,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    )
    
    # ── Tool 2: Get News ──
    def get_news_handler(topic: str, days_back: int = 7) -> str:
        # In production: call news API
        return f"Recent news about '{topic}' from last {days_back} days: [News 1, News 2]"
    
    server.register_tool(
        name="get_news",
        description="Get recent news articles about a topic",
        handler_func=get_news_handler,
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "days_back": {"type": "integer", "default": 7}
            },
            "required": ["topic"]
        }
    )
    
    return server


# ─── Simulate MCP communication ───

if __name__ == "__main__":
    
    # Create the MCP server
    server = create_perplexity_mcp_server()
    
    print("\n📡 MCP Server Running!")
    print("="*50)
    
    # Simulate: LLM asks "what tools do you have?"
    list_request = {"method": "tools/list"}
    tools_response = server.handle_request(list_request)
    print(f"\n📋 Available Tools:")
    for tool in tools_response["tools"]:
        print(f"  • {tool['name']}: {tool['description']}")
    
    # Simulate: LLM calls web search tool
    call_request = {
        "method": "tools/call",
        "params": {
            "name": "web_search",
            "arguments": {
                "query": "AI trends 2025",
                "max_results": 3
            }
        }
    }
    
    print(f"\n🔧 LLM calling tool: web_search")
    result = server.handle_request(call_request)
    print(f"Result: {result['content'][0]['text']}")
```

---

### 🔑 Key MCP Concepts Summary:

| Concept | What it means |
|---------|---------------|
| **MCP Server** | The tool provider (has the tools) |
| **MCP Client** | The LLM / agent (uses the tools) |
| **tools/list** | Server tells client what tools exist |
| **tools/call** | Client asks server to run a tool |
| **JSON-RPC** | The standard messaging format |
| **Resources** | Data the server can share (files, DBs) |
| **Prompts** | Pre-built prompt templates in the server |

---

### ⚠️ MCP Failure Modes:

```
1. Connection failures → Server goes down, agent crashes
2. Schema mismatches → LLM sends wrong argument types
3. Slow tools → Tool takes too long, agent times out
4. Security issues → Malicious input through tool parameters
5. Over-trust → Agent blindly trusts tool output without validation
```

---

# 📊 CHAPTER SUMMARY — Part 1

Let me summarize everything we learned in Part 1:

---

```
WHAT WE COVERED:

1. ✅ WHAT WE'RE BUILDING
   → Perplexity-like agent: search web, think, answer

2. ✅ AGENTS OVERVIEW
   → LLM = input/output machine
   → Agent = LLM + tools + memory + loop
   → Agentic System = multiple agents working together
   → Agency levels 0-5: from pure LLM to full multi-agent

3. ✅ WORKFLOWS
   → Prompt Chaining: break big task into sequential steps
   → Routing: analyze input → choose right path/specialist
   → Parallelization: 
      - Sectioning: divide task, run in parallel, combine
      - Voting: multiple perspectives, take best result
   → Reflection: generate → critique → improve → loop
   → Orchestrator-Worker: manager assigns tasks to specialists

4. ✅ TOOLS
   → Tool Calling: LLM requests tools, code executes them
   → Tool Formatting: JSON schema defining tools for LLM
   → Tool Execution: the loop of call → execute → return result
   → MCP: standard protocol for LLM ↔ tool communication
```

---



