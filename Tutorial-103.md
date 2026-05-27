# Complete Tutorial: Build an "Ask-the-Web" Agent like Perplexity

## The Most Beginner-Friendly, End-to-End, Deep Tutorial — DEFINITIVE VERSION | Part 1 of 2

---

> **What we are building:** An AI agent that can search the web, read results, think about them, and give you a smart answer with sources — just like Perplexity.ai does.

---

# Full Roadmap of Everything We Will Cover

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
│
├── 5. Multi-Step Agents
│   ├── Planning Autonomy
│   ├── ReACT Framework
│   ├── Reflexion
│   ├── ReWOO
│   └── Tree Search for Agents
│
├── 6. Multi-Agent Systems
│   ├── Challenges
│   ├── Use Cases
│   └── A2A Protocol
│
├── 7. Agent Evaluation
│   ├── Why Evaluation is Hard
│   ├── Evaluation Metrics
│   ├── Evaluation Frameworks
│   └── Code Examples
│
└── 8. Complete Project Build
    ├── Full Architecture
    ├── Complete Code
    ├── Streamlit UI
    └── Demo-Ready Final Project
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

# The Most Beginner-Friendly, End-to-End, Deep Tutorial — DEFINITIVE VERSION | Part 2 of 2

---

> **Quick Recap of Part 1:** We covered Agents Overview, Agency Levels, Workflows (Prompt Chaining, Routing, Parallelization, Reflection, Orchestrator-Worker), and Tools (Tool Calling, Tool Formatting, Tool Execution, MCP).

> **Part 2:** Multi-Step Agents, ReACT, Reflexion, ReWOO, Tree Search, Multi-Agent Systems, Agent Evaluation, and the **Complete Project Build**.

---

# 🧠 CHAPTER 5: Multi-Step Agents

---

## What is a Multi-Step Agent?

### 🔮 Prediction First:

**What beginners think:**
> "A multi-step agent just runs 3-4 tools in sequence."

**The real answer:**
> A multi-step agent **autonomously decides** what steps to take, in what order, using what tools, and when to stop — based on what it observes at each step. It is not pre-programmed with fixed steps.

---

### 🏠 Real-World Analogy:

**A detective solving a case:**

```
Detective receives a case: "Find out who stole the diamond"

Step 1: THINKS → "I need to check who was in the building"
        ACTS   → Reviews security camera footage
        SEES   → 3 people were there

Step 2: THINKS → "I need to know their alibis"
        ACTS   → Interviews each person
        SEES   → Person 2 has no alibi

Step 3: THINKS → "Check Person 2's financial records"
        ACTS   → Requests bank records
        SEES   → Large cash withdrawal day before

Step 4: THINKS → "I have enough evidence"
        ACTS   → Writes arrest warrant
        DONE ✅
```

**The detective didn't know Step 3 existed until Step 2 revealed it.**
**Each observation changes what the next step should be.**

**This is a multi-step agent!**

---

## 5.1 Planning Autonomy

---

### What is Planning Autonomy?

**Simple definition:**
Planning autonomy is the agent's ability to **create its own plan** for achieving a goal — without a human telling it each step.

There are **three levels** of planning autonomy:

---

### Level 1: No Planning (Reactive)

```
Input → Single Response → Done
```

The agent reacts to each message but doesn't plan ahead.

**Example:**
```
User: "Search for AI news"
Agent: [searches] → Returns results
[No thinking about what to do next]
```

---

### Level 2: Fixed Planning (Pre-planned)

```
Input → Human-defined Plan → Execute Steps → Done
```

A human writes the plan. The agent executes it.

**Example:**
```
Pre-written plan:
  Step 1: Always search news
  Step 2: Always summarize
  Step 3: Always add sources
```

The agent follows this rigidly — even if Step 2 is not needed.

---

### Level 3: Dynamic Planning (Autonomous)

```
Input → Agent Creates Plan → Executes → Observes →
Updates Plan → Executes → Observes → ... → Done
```

The agent creates AND updates its plan based on what it discovers.

**Example:**
```
Goal: "Research the impact of AI on jobs"

Agent's initial plan:
  1. Search for general statistics
  2. Find expert opinions
  3. Summarize findings

After Step 1, agent sees data is from 2019 → Updates plan:
  1. ✅ Done (old data found)
  2. Search specifically for 2024-2025 data (NEW STEP!)
  3. Find expert opinions
  4. Compare old vs new data (NEW STEP!)
  5. Summarize findings
```

**The plan evolved based on discoveries.**

---

### 💻 Code Example — Dynamic Planning:

```python
import openai
import json

client = openai.OpenAI(api_key="your-api-key")


class DynamicPlanner:
    """
    An agent that creates and updates its own plan
    based on what it discovers during execution.
    """
    
    def __init__(self):
        self.plan = []           # Current plan (list of steps)
        self.completed_steps = []  # What's been done
        self.observations = []     # What's been learned
    
    def create_initial_plan(self, goal: str) -> list:
        """
        Create an initial plan for the goal.
        The agent thinks about what steps are needed.
        """
        
        planning_prompt = f"""
        You are a strategic planner for an AI research agent.
        
        Goal: {goal}
        
        Create an initial plan with 3-5 steps.
        Each step should be specific and actionable.
        Consider what information you'll need and in what order.
        
        Output as JSON:
        {{
            "plan": [
                {{"step": 1, "action": "description of what to do", 
                  "reason": "why this step is needed"}},
                ...
            ],
            "reasoning": "why you chose this plan"
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": planning_prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        self.plan = result["plan"]
        
        print(f"\n📋 INITIAL PLAN CREATED:")
        print(f"Reasoning: {result['reasoning']}")
        for step in self.plan:
            print(f"  Step {step['step']}: {step['action']}")
        
        return self.plan
    
    def update_plan(self, goal: str, new_observation: str) -> list:
        """
        After each step, the agent reviews its plan and
        updates it based on new information discovered.
        """
        
        completed_text = "\n".join([
            f"Step {s['step']}: {s['action']} → {s['result']}"
            for s in self.completed_steps
        ])
        
        remaining_plan = [
            s for s in self.plan 
            if s['step'] > len(self.completed_steps)
        ]
        
        update_prompt = f"""
        You are replanning based on new information.
        
        Original Goal: {goal}
        
        Completed Steps:
        {completed_text}
        
        New Discovery:
        {new_observation}
        
        Remaining Plan (before update):
        {json.dumps(remaining_plan, indent=2)}
        
        Should the plan change based on what was discovered?
        - Add new steps if needed
        - Remove steps that are no longer necessary
        - Modify steps that need adjustment
        - Keep steps that are still valid
        
        Output as JSON:
        {{
            "plan_changed": true/false,
            "reason": "why plan changed or stayed same",
            "updated_remaining_steps": [
                {{"step": number, "action": "description", 
                  "reason": "why needed"}}
            ]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": update_prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        if result["plan_changed"]:
            print(f"\n🔄 PLAN UPDATED!")
            print(f"Reason: {result['reason']}")
            
            # Update the plan
            base_step = len(self.completed_steps)
            for i, step in enumerate(result["updated_remaining_steps"]):
                step["step"] = base_step + i + 1
            
            # Reconstruct full plan
            self.plan = self.completed_steps + result["updated_remaining_steps"]
            
            print("New remaining steps:")
            for step in result["updated_remaining_steps"]:
                print(f"  Step {step['step']}: {step['action']}")
        else:
            print(f"\n✅ Plan unchanged: {result['reason']}")
        
        return self.plan
    
    def execute_step(self, step: dict, goal: str) -> str:
        """
        Execute one step of the plan.
        In production: this would call real tools.
        """
        
        execution_prompt = f"""
        Execute this specific research step.
        
        Overall Goal: {goal}
        Current Step: {step['action']}
        Reason for step: {step['reason']}
        
        Previous findings:
        {chr(10).join([f"- {o}" for o in self.observations])}
        
        Simulate executing this step and provide detailed findings.
        Be specific and realistic.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": execution_prompt}]
        )
        
        result = response.choices[0].message.content
        
        # Record the completed step
        step_record = dict(step)
        step_record["result"] = result[:200]  # Store summary
        self.completed_steps.append(step_record)
        self.observations.append(f"Step {step['step']}: {result[:100]}")
        
        return result
    
    def run(self, goal: str, max_steps: int = 8) -> str:
        """
        Full planning and execution loop.
        """
        
        print(f"\n{'='*60}")
        print(f"🎯 DYNAMIC PLANNER STARTING")
        print(f"Goal: {goal}")
        print(f"{'='*60}")
        
        # Create initial plan
        self.create_initial_plan(goal)
        
        steps_taken = 0
        
        while steps_taken < max_steps:
            
            # Find next uncompleted step
            next_step = None
            for step in self.plan:
                if step['step'] > len(self.completed_steps):
                    next_step = step
                    break
            
            # No more steps — we're done!
            if not next_step:
                print("\n🎉 All steps completed!")
                break
            
            steps_taken += 1
            print(f"\n{'─'*40}")
            print(f"⚡ EXECUTING Step {next_step['step']}: {next_step['action']}")
            
            # Execute the step
            result = self.execute_step(next_step, goal)
            print(f"📊 Result preview: {result[:200]}...")
            
            # Update plan based on what we learned
            self.update_plan(goal, result[:300])
        
        # Generate final answer
        print(f"\n📝 Generating final answer...")
        
        all_findings = "\n\n".join([
            f"**Step {s['step']} - {s['action']}:**\n{s['result']}"
            for s in self.completed_steps
        ])
        
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Synthesize all research findings into a comprehensive, well-structured answer."
                },
                {
                    "role": "user",
                    "content": f"Goal: {goal}\n\nResearch Findings:\n{all_findings}"
                }
            ]
        )
        
        final_answer = final_response.choices[0].message.content
        print(f"\n✅ FINAL ANSWER:\n{final_answer}")
        
        return final_answer


# ─── Test dynamic planning ───
if __name__ == "__main__":
    planner = DynamicPlanner()
    planner.run("Research the current state of AI regulation worldwide in 2025")
```

---

## 5.2 ReACT Framework

---

### What is ReACT?

**ReACT = Reasoning + Acting**

It is the most important and widely-used framework for multi-step agents.

**Created by:** Yao et al., Princeton University (2022)

---

### 🔮 Prediction First:

**What beginners think:**
> "ReACT means the agent reacts to user input."

**The real answer:**
> ReACT is a specific loop pattern where the agent alternates between **writing out its reasoning (Thought)**, **taking an action (Act)**, and **observing the result (Observe)** — over and over until the goal is reached.

---

### 🏠 Real-World Analogy:

**A scientist running experiments:**

```
THOUGHT: "I think the plant needs more water to grow faster"
ACTION: Water the plant daily for 1 week
OBSERVATION: Plant grew 5cm — that's faster than before

THOUGHT: "Water helped. Maybe sunlight also matters?"
ACTION: Move plant to sunny window for 1 week
OBSERVATION: Plant grew 8cm — even better!

THOUGHT: "Both water and sun help. Let me try adding fertilizer"
ACTION: Add fertilizer + water + sun
OBSERVATION: Plant grew 12cm — amazing!

THOUGHT: "I now have enough data to draw conclusions"
ACTION: Write research conclusion
DONE ✅
```

**Thought → Action → Observation → Thought → Action → Observation...**

This is ReACT!

---

### 📊 ReACT vs No ReACT:

```
WITHOUT ReACT (Direct Answer):
User: "What is the current population of Tokyo?"
LLM:  "Tokyo has about 13 million people" 
      [guesses from training data — might be outdated]

WITH ReACT:
User: "What is the current population of Tokyo?"

THOUGHT: "I need current data. My training might be outdated.
          I should search for the latest population statistics."
          
ACTION:  search_web("Tokyo population 2025")

OBSERVATION: "Tokyo Metropolitan area population 2025: 37.4 million
              (23 special wards: 9.7 million)"

THOUGHT: "Good data found. The user asked about Tokyo specifically.
          I should clarify — greater Tokyo area vs city proper."

ACTION:  search_web("Tokyo 23 wards vs greater Tokyo population difference")

OBSERVATION: "23 special wards = city proper = 9.7 million
              Greater Tokyo Metropolitan area = 37.4 million"

THOUGHT: "Now I have accurate current data. I can answer clearly."

FINAL ANSWER: "Tokyo's population varies by definition:
              - Tokyo 23 special wards (city proper): ~9.7 million
              - Greater Tokyo Metropolitan area: ~37.4 million
              [Source: 2025 data]"
```

**ReACT gives much more accurate, current, reasoned answers!**

---

### 💻 ReACT Implementation:

```python
import openai
import json
from typing import Optional

client = openai.OpenAI(api_key="your-api-key")


# ─── Tool functions ───

def search_web(query: str) -> str:
    """Search the web. Returns results as string."""
    print(f"    🌐 [SEARCH] '{query}'")
    # In production: real API call
    return f"Web results for '{query}': [Relevant information about {query} from multiple sources]"


def get_page_content(url: str) -> str:
    """Get content from a specific webpage."""
    print(f"    📄 [READ PAGE] '{url}'")
    return f"Content from {url}: [Detailed article content...]"


def calculate(expression: str) -> str:
    """Calculate a math expression."""
    print(f"    🔢 [CALCULATE] '{expression}'")
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except:
        return "Calculation error"


# Tool registry
TOOLS = {
    "search_web": search_web,
    "get_page_content": get_page_content,
    "calculate": calculate
}

TOOLS_DESCRIPTION = """
Available tools:
1. search_web(query: str) → Search the internet
2. get_page_content(url: str) → Read a specific webpage
3. calculate(expression: str) → Do math calculations
"""


class ReACTAgent:
    """
    A ReACT agent that follows the Thought → Action → Observation loop.
    
    The key innovation: The LLM writes out its THINKING before acting.
    This makes it more accurate and explainable.
    """
    
    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        self.history = []  # Full conversation history
    
    def build_react_prompt(self) -> str:
        """
        The system prompt that teaches the LLM to use ReACT format.
        This is the heart of the ReACT framework.
        """
        
        return f"""
        You are a helpful research assistant that solves problems step by step.
        
        {TOOLS_DESCRIPTION}
        
        You must follow this EXACT format for EVERY response:
        
        Thought: [Your reasoning about what to do next. Be specific about WHY.]
        Action: [tool_name]
        Action Input: [the input to the tool, as JSON]
        
        OR when you have the final answer:
        
        Thought: [Your reasoning that you now have enough information]
        Final Answer: [Your complete, well-formatted answer with citations]
        
        RULES:
        - ALWAYS start with "Thought:"
        - ALWAYS explain your reasoning before acting
        - Use tools when you need current information
        - Do NOT guess — use tools to verify
        - Stop when you have enough to answer fully
        
        EXAMPLE:
        Thought: The user wants to know the latest iPhone price. 
                 I need current data since prices change. 
                 Let me search for this.
        Action: search_web
        Action Input: {{"query": "iPhone 16 price 2025"}}
        
        [After seeing search results]
        
        Thought: I found the price information. I have enough to answer.
        Final Answer: The iPhone 16 starts at $799...
        """
    
    def parse_react_response(self, response_text: str) -> dict:
        """
        Parse the LLM's ReACT-formatted response.
        
        Extracts:
        - thought: what the agent is thinking
        - action: which tool to call (if any)
        - action_input: arguments for the tool (if any)
        - final_answer: the final answer (if done)
        """
        
        lines = response_text.strip().split('\n')
        result = {
            "thought": "",
            "action": None,
            "action_input": None,
            "final_answer": None,
            "raw": response_text
        }
        
        current_key = None
        current_value = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("Thought:"):
                current_key = "thought"
                current_value = [line[8:].strip()]
                
            elif line.startswith("Action:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value).strip()
                current_key = "action"
                current_value = [line[7:].strip()]
                
            elif line.startswith("Action Input:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value).strip()
                current_key = "action_input"
                current_value = [line[13:].strip()]
                
            elif line.startswith("Final Answer:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value).strip()
                current_key = "final_answer"
                current_value = [line[13:].strip()]
                
            else:
                # Continuation of current section
                if current_key and line:
                    current_value.append(line)
        
        # Save last section
        if current_key and current_value:
            result[current_key] = " ".join(current_value).strip()
        
        return result
    
    def execute_action(self, action: str, action_input: str) -> str:
        """
        Execute the tool that the LLM requested.
        """
        
        # Clean the action name
        action = action.strip().lower()
        
        # Parse the input JSON
        try:
            if isinstance(action_input, str):
                inputs = json.loads(action_input)
            else:
                inputs = action_input
        except json.JSONDecodeError:
            # If not valid JSON, use as plain string
            inputs = {"query": action_input}
        
        # Find and execute the tool
        if action in TOOLS:
            tool_func = TOOLS[action]
            try:
                result = tool_func(**inputs)
                return result
            except Exception as e:
                return f"Tool error: {str(e)}"
        else:
            return f"Unknown tool: {action}. Available: {list(TOOLS.keys())}"
    
    def run(self, question: str) -> str:
        """
        The main ReACT loop.
        
        Thought → Action → Observation → Thought → Action → ...
        Until: Final Answer
        """
        
        print(f"\n{'='*60}")
        print(f"🤖 ReACT AGENT STARTING")
        print(f"Question: {question}")
        print(f"{'='*60}")
        
        # Initialize conversation
        self.history = [
            {"role": "system", "content": self.build_react_prompt()},
            {"role": "user", "content": question}
        ]
        
        step = 0
        
        while step < self.max_steps:
            step += 1
            print(f"\n{'─'*40}")
            print(f"🔄 ReACT Step {step}")
            
            # Get LLM's next Thought + Action (or Final Answer)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=self.history,
                temperature=0.1,  # Low temperature for consistency
                stop=["Observation:"]  # Stop before writing fake observations
            )
            
            llm_output = response.choices[0].message.content
            print(f"\n🧠 LLM Output:\n{llm_output}")
            
            # Add LLM response to history
            self.history.append({
                "role": "assistant",
                "content": llm_output
            })
            
            # Parse the response
            parsed = self.parse_react_response(llm_output)
            
            # Show thought
            if parsed["thought"]:
                print(f"\n💭 THOUGHT: {parsed['thought']}")
            
            # Check if we have a final answer
            if parsed["final_answer"]:
                print(f"\n🎉 FINAL ANSWER REACHED!")
                print(f"{'='*60}")
                print(parsed["final_answer"])
                print(f"{'='*60}")
                return parsed["final_answer"]
            
            # Execute the requested action
            if parsed["action"] and parsed["action_input"]:
                
                print(f"\n⚡ ACTION: {parsed['action']}")
                print(f"📥 INPUT: {parsed['action_input']}")
                
                observation = self.execute_action(
                    parsed["action"], 
                    parsed["action_input"]
                )
                
                print(f"\n👁️  OBSERVATION: {observation[:200]}...")
                
                # Add observation to history
                # (This is how ReACT feeds results back to LLM)
                self.history.append({
                    "role": "user",
                    "content": f"Observation: {observation}"
                })
            
            else:
                # LLM didn't give action or final answer — something went wrong
                print("⚠️  No action or final answer found. Prompting LLM to continue...")
                self.history.append({
                    "role": "user",
                    "content": "Please continue with your next Thought and Action, or provide your Final Answer."
                })
        
        # If we hit max steps without final answer
        print(f"\n⏰ Max steps ({self.max_steps}) reached.")
        return "Could not complete within the step limit. Please try a simpler question."


# ─── Test ReACT Agent ───
if __name__ == "__main__":
    
    agent = ReACTAgent(max_steps=8)
    
    # Test question
    result = agent.run(
        "What are the top 3 AI companies by market cap in 2025, "
        "and what is their combined total market cap?"
    )
```

---

### 📊 ReACT Output Trace (What it Looks Like):

```
Question: "What are the top 3 AI companies by market cap in 2025?"

─────────── Step 1 ───────────
💭 THOUGHT: I need current market cap data. This changes frequently.
            Let me search for the latest information.

⚡ ACTION: search_web
📥 INPUT: {"query": "top AI companies market cap 2025"}

👁️  OBSERVATION: Microsoft: $3.1T, Nvidia: $2.9T, Alphabet: $2.1T...

─────────── Step 2 ───────────
💭 THOUGHT: I found the top 3 companies. Now I need to calculate
            their combined market cap: 3.1 + 2.9 + 2.1 trillion.

⚡ ACTION: calculate
📥 INPUT: {"expression": "3.1 + 2.9 + 2.1"}

👁️  OBSERVATION: Result: 8.1

─────────── Step 3 ───────────
💭 THOUGHT: I now have all the information needed to answer fully.

🎉 FINAL ANSWER:
Top 3 AI companies by market cap in 2025:
1. Microsoft: $3.1 trillion
2. Nvidia: $2.9 trillion  
3. Alphabet (Google): $2.1 trillion
Combined total: $8.1 trillion [Sources: ...]
```

---

## 5.3 Reflexion

---

### What is Reflexion?

**Reflexion = ReACT + Long-term Memory of Past Mistakes**

**Paper:** "Reflexion: Language Agents with Verbal Reinforcement Learning" (Shinn et al., 2023)

---

### The Problem Reflexion Solves:

**ReACT problem:**
Every time you start a new conversation with a ReACT agent, it **forgets all its past mistakes**. It might make the same error again.

**Example:**
```
Run 1: Agent tries to search "stock prices" → gets blocked by paywall
        Agent fails to answer properly

Run 2 (new conversation): Agent tries to search "stock prices" AGAIN
        Same error! It learned nothing!
```

**Reflexion solution:**
After each failed attempt, the agent **writes down what went wrong** and **stores it in memory**. Next time, it reads this memory and avoids the mistake.

---

### 🏠 Real-World Analogy:

**A student with a failure diary:**

```
First exam: Failed because "I didn't read the questions carefully"
→ Writes in diary: "Always read ALL parts of the question"

Second exam: Failed because "I ran out of time"
→ Writes in diary: "Spend max 2 min per question, move on if stuck"

Third exam: Reads diary before starting
→ Reads carefully + manages time → PASSES ✅
```

**The diary is Reflexion's memory!**

---

### 📊 Reflexion Flow:

```
TASK GIVEN
    ↓
Read memory of past mistakes (if any)
    ↓
Attempt task with ReACT
    ↓
DID IT SUCCEED?
    ├── YES → Done ✅
    └── NO ↓
        │
        Evaluate: What went wrong?
        Write verbal reflection: "I failed because..."
        Store reflection in memory
        │
        ↓
        Try again (with memory of mistake)
        ↓
        DID IT SUCCEED?
        ├── YES → Done ✅
        └── NO → Reflect again... (loop)
```

---

### 💻 Reflexion Implementation:

```python
import openai
import json
from typing import List

client = openai.OpenAI(api_key="your-api-key")


class ReflexionAgent:
    """
    Reflexion Agent = ReACT + Memory of Past Failures
    
    The agent learns from its mistakes across multiple trials.
    Each failure produces a 'reflection' stored in memory.
    Next trial begins by reading all past reflections.
    """
    
    def __init__(self, max_trials: int = 3, max_steps_per_trial: int = 6):
        self.max_trials = max_trials
        self.max_steps_per_trial = max_steps_per_trial
        
        # This is the key innovation of Reflexion:
        # Persistent memory of past mistakes
        self.reflections: List[str] = []
    
    def attempt_task(self, task: str, trial_num: int) -> dict:
        """
        One attempt at the task using ReACT.
        Returns the result and whether it succeeded.
        """
        
        # Build prompt with memory of past failures
        reflections_text = ""
        if self.reflections:
            reflections_text = f"""
            IMPORTANT - Learn from your past failures:
            {chr(10).join([f'Trial {i+1} failure: {r}' 
                           for i, r in enumerate(self.reflections)])}
            
            Use these lessons to do better this time.
            """
        
        system_prompt = f"""
        You are a research agent. Solve the given task accurately.
        
        {reflections_text}
        
        Format your response as:
        Thought: [reasoning]
        Action: [tool name]
        Action Input: {{"key": "value"}}
        
        Or when done:
        Thought: [reasoning]
        Final Answer: [complete answer]
        
        Available tools:
        - search_web(query): Search the internet
        - calculate(expression): Math calculations
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        print(f"\n🔄 TRIAL {trial_num}")
        if self.reflections:
            print(f"📚 Reading {len(self.reflections)} past reflection(s)...")
        
        # Simple simulation of ReACT steps
        for step in range(self.max_steps_per_trial):
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.1
            )
            
            output = response.choices[0].message.content
            messages.append({"role": "assistant", "content": output})
            
            # Check for final answer
            if "Final Answer:" in output:
                answer = output.split("Final Answer:")[-1].strip()
                print(f"✅ Trial {trial_num}: Answer found!")
                return {
                    "success": True,
                    "answer": answer,
                    "steps": step + 1
                }
            
            # Simulate tool execution
            if "Action:" in output and "Action Input:" in output:
                # Extract action details and add fake observation
                messages.append({
                    "role": "user",
                    "content": f"Observation: [Tool result for step {step+1}]"
                })
        
        # If we get here, trial failed (ran out of steps)
        print(f"❌ Trial {trial_num}: Failed - ran out of steps")
        return {
            "success": False,
            "answer": None,
            "steps": self.max_steps_per_trial,
            "last_response": messages[-1]["content"]
        }
    
    def reflect_on_failure(self, task: str, failed_attempt: dict) -> str:
        """
        After a failure, the agent thinks about what went wrong
        and writes a verbal reflection (lesson learned).
        """
        
        reflection_prompt = f"""
        You just failed to complete this task:
        Task: {task}
        
        What happened in your failed attempt:
        {failed_attempt.get('last_response', 'No response captured')}
        
        Write a SHORT, SPECIFIC reflection on:
        1. What went wrong?
        2. What should you do differently next time?
        3. What specific mistake to avoid?
        
        Be concrete and actionable. Max 3 sentences.
        Start with "I failed because..."
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": reflection_prompt}]
        )
        
        reflection = response.choices[0].message.content
        print(f"\n🪞 REFLECTION: {reflection}")
        
        return reflection
    
    def evaluate_answer(self, task: str, answer: str) -> bool:
        """
        Evaluate if the answer is actually good enough.
        In production: this could use a separate evaluation LLM.
        """
        
        eval_prompt = f"""
        Task: {task}
        Answer provided: {answer}
        
        Is this answer:
        1. Complete (fully answers the question)?
        2. Accurate (no obvious errors)?
        3. Well-sourced (cites where info came from)?
        
        Respond with ONLY: PASS or FAIL
        Then one sentence explaining why.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}]
        )
        
        eval_result = response.choices[0].message.content
        passed = eval_result.strip().upper().startswith("PASS")
        
        print(f"\n📊 EVALUATION: {eval_result}")
        return passed
    
    def run(self, task: str) -> str:
        """
        Main Reflexion loop:
        Try → Evaluate → If failed: Reflect → Try again
        """
        
        print(f"\n{'='*60}")
        print(f"🪞 REFLEXION AGENT STARTING")
        print(f"Task: {task}")
        print(f"Max trials: {self.max_trials}")
        print(f"{'='*60}")
        
        best_answer = None
        
        for trial in range(1, self.max_trials + 1):
            
            # Attempt the task
            result = self.attempt_task(task, trial)
            
            if result["success"]:
                
                # Evaluate the answer quality
                is_good = self.evaluate_answer(task, result["answer"])
                
                if is_good:
                    print(f"\n🎉 SUCCESS on trial {trial}!")
                    return result["answer"]
                else:
                    # Answer found but quality is poor
                    best_answer = result["answer"]  # Save as backup
                    result["success"] = False
                    result["last_response"] = result["answer"]
                    print(f"⚠️  Answer found but quality insufficient. Reflecting...")
            
            # If failed or quality was poor, reflect
            if trial < self.max_trials:  # Don't reflect on last trial
                reflection = self.reflect_on_failure(task, result)
                self.reflections.append(reflection)
                print(f"\n📝 Reflection stored. Starting trial {trial + 1}...")
        
        # Return best answer found, or failure message
        if best_answer:
            print(f"\n✅ Returning best answer found (trial {self.max_trials})")
            return best_answer
        else:
            return f"Could not complete task after {self.max_trials} trials."


# ─── Test Reflexion ───
if __name__ == "__main__":
    agent = ReflexionAgent(max_trials=3, max_steps_per_trial=6)
    result = agent.run("Find the most cited AI research paper of 2024 and explain its key contribution")
    print(f"\n🏆 FINAL RESULT:\n{result}")
```

---

## 5.4 ReWOO

---

### What is ReWOO?

**ReWOO = Reasoning WithOut Observation**

**Paper:** "ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models" (Xu et al., 2023)

---

### The Problem ReWOO Solves:

**ReACT problem — Too many LLM calls:**

```
ReACT for a 5-step task:

LLM Call 1: Think + Decide Action 1
LLM Call 2: Process Observation 1 + Think + Decide Action 2
LLM Call 3: Process Observation 2 + Think + Decide Action 3
LLM Call 4: Process Observation 3 + Think + Decide Action 4
LLM Call 5: Process Observation 4 + Think + Write Answer

= 5 LLM calls (expensive and slow!)
```

**ReWOO solution — Plan once, execute all, synthesize once:**

```
ReWOO for same 5-step task:

LLM Call 1: Think + Plan ALL 5 steps at once
[Execute all 5 tools without LLM]
LLM Call 2: Receive all results + Write final answer

= Only 2 LLM calls! Much cheaper and faster!
```

---

### 🏠 Real-World Analogy:

**Shopping trip comparison:**

**ReACT approach (inefficient):**
```
Go to store → Look for milk → Find milk → 
Come home to check list → Go to store again → 
Look for bread → Find bread → 
Come home → Check list → Go to store again...
```
Multiple trips! Very wasteful.

**ReWOO approach (efficient):**
```
Read FULL shopping list at home (plan)
→ Go to store ONCE
→ Get everything: milk, bread, eggs, cheese
→ Come home with everything
→ Done ✅
```
One trip! 

---

### 📊 ReWOO Architecture:

```
PHASE 1: PLANNER (one LLM call)
─────────────────────────────
Input: User question
Output: Complete plan with ALL steps defined
Example:
  Step 1: search_web("AI companies 2025")
  Step 2: search_web("NVIDIA revenue Q1 2025") → uses result of Step 1
  Step 3: calculate("revenue1 + revenue2") → uses result of Step 2
  Step 4: get_page_content("specific_url") → uses result of Step 1

PHASE 2: WORKER (no LLM involved!)
─────────────────────────────────
Execute ALL steps in the plan:
  Execute Step 1 → get result E1
  Execute Step 2 → get result E2 (might use E1)
  Execute Step 3 → get result E3 (might use E2)
  Execute Step 4 → get result E4 (might use E1)

PHASE 3: SOLVER (one LLM call)
──────────────────────────────
Input: Original question + all results (E1, E2, E3, E4)
Output: Final comprehensive answer
```

---

### 💻 ReWOO Implementation:

```python
import openai
import json
import re
from typing import List, Dict

client = openai.OpenAI(api_key="your-api-key")


def search_web(query: str) -> str:
    print(f"    🌐 [WORKER] search_web('{query}')")
    return f"Results for '{query}': [Comprehensive information about {query}]"

def calculate(expression: str) -> str:
    print(f"    🔢 [WORKER] calculate('{expression}')")
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except:
        return "Calculation error"

def get_page_content(url: str) -> str:
    print(f"    📄 [WORKER] get_page_content('{url}')")
    return f"Content from {url}: [Detailed page content]"


WORKER_TOOLS = {
    "search_web": search_web,
    "calculate": calculate,
    "get_page_content": get_page_content
}


class ReWOOAgent:
    """
    ReWOO Agent: Plan ALL steps first, then execute all,
    then synthesize — minimizing LLM calls.
    """
    
    def plan(self, question: str) -> List[Dict]:
        """
        PHASE 1: Create a complete plan upfront.
        One LLM call to plan everything.
        """
        
        planner_prompt = f"""
        You are a planning agent. Create a complete execution plan.
        
        Question: {question}
        
        Available tools:
        - search_web(query: str)
        - calculate(expression: str)  
        - get_page_content(url: str)
        
        Rules:
        - Plan ALL steps needed to answer the question
        - Steps can reference previous step results as #E1, #E2, etc.
        - Be specific about what each step does
        
        Output as JSON:
        {{
            "plan": [
                {{
                    "step_id": "E1",
                    "tool": "tool_name",
                    "input": "tool input (can reference #E1, #E2 etc)",
                    "purpose": "why this step is needed"
                }},
                ...
            ],
            "reasoning": "overall strategy explanation"
        }}
        
        Example output:
        {{
            "plan": [
                {{
                    "step_id": "E1",
                    "tool": "search_web", 
                    "input": "top AI companies 2025 market cap",
                    "purpose": "Get list of top AI companies"
                }},
                {{
                    "step_id": "E2",
                    "tool": "search_web",
                    "input": "Microsoft AI revenue 2025",
                    "purpose": "Get Microsoft's specific revenue data"
                }},
                {{
                    "step_id": "E3",
                    "tool": "calculate",
                    "input": "revenue_from_#E2 * 0.15",
                    "purpose": "Calculate 15% of Microsoft AI revenue"
                }}
            ],
            "reasoning": "Get company list first, then details, then calculate"
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": planner_prompt}],
            response_format={"type": "json_object"}
        )
        
        plan_data = json.loads(response.choices[0].message.content)
        
        print(f"\n📋 PHASE 1: PLANNER OUTPUT")
        print(f"Strategy: {plan_data['reasoning']}")
        print(f"Steps planned: {len(plan_data['plan'])}")
        for step in plan_data['plan']:
            print(f"  {step['step_id']}: {step['tool']}('{step['input'][:50]}...')")
            print(f"         Purpose: {step['purpose']}")
        
        return plan_data['plan']
    
    def execute_plan(self, plan: List[Dict]) -> Dict[str, str]:
        """
        PHASE 2: Execute ALL planned steps.
        NO LLM calls here! Just tool execution.
        """
        
        print(f"\n⚡ PHASE 2: WORKER EXECUTING ALL STEPS")
        print("(No LLM calls — just tool execution!)")
        
        results = {}  # Stores results as E1, E2, E3...
        
        for step in plan:
            step_id = step["step_id"]
            tool_name = step["tool"]
            tool_input = step["input"]
            
            print(f"\n  🔧 Executing {step_id}: {tool_name}")
            
            # Replace #E1, #E2 references with actual results
            for prev_id, prev_result in results.items():
                placeholder = f"#{prev_id}"
                if placeholder in tool_input:
                    # Replace placeholder with actual result (truncated)
                    tool_input = tool_input.replace(
                        placeholder, 
                        prev_result[:100]  # Use first 100 chars of result
                    )
            
            # Execute the tool
            if tool_name in WORKER_TOOLS:
                tool_func = WORKER_TOOLS[tool_name]
                result = tool_func(tool_input)
                results[step_id] = result
                print(f"  ✅ {step_id} result: {result[:100]}...")
            else:
                results[step_id] = f"Unknown tool: {tool_name}"
        
        return results
    
    def solve(self, question: str, plan: List[Dict], 
              evidence: Dict[str, str]) -> str:
        """
        PHASE 3: Final synthesis using all collected evidence.
        One LLM call to create the final answer.
        """
        
        print(f"\n🧩 PHASE 3: SOLVER CREATING FINAL ANSWER")
        
        # Format all evidence
        evidence_text = "\n\n".join([
            f"**{step_id}** ({self._get_step_purpose(step_id, plan)}):\n{result}"
            for step_id, result in evidence.items()
        ])
        
        solver_prompt = f"""
        Answer the following question using the provided evidence.
        
        Question: {question}
        
        Evidence collected:
        {evidence_text}
        
        Instructions:
        - Use the evidence to write a complete, accurate answer
        - Cite which evidence supports each claim
        - Be clear and well-structured
        - Include all relevant numbers, facts, and details found
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": solver_prompt}]
        )
        
        return response.choices[0].message.content
    
    def _get_step_purpose(self, step_id: str, plan: List[Dict]) -> str:
        """Helper to get the purpose of a step."""
        for step in plan:
            if step["step_id"] == step_id:
                return step.get("purpose", "research step")
        return "research step"
    
    def run(self, question: str) -> str:
        """
        Main ReWOO flow:
        Plan (1 LLM call) → Execute (0 LLM calls) → Solve (1 LLM call)
        Total: Only 2 LLM calls!
        """
        
        print(f"\n{'='*60}")
        print(f"🚀 ReWOO AGENT STARTING")
        print(f"Question: {question}")
        print(f"Goal: Minimize LLM calls while maximizing answer quality")
        print(f"{'='*60}")
        
        # Phase 1: Plan everything
        plan = self.plan(question)
        
        # Phase 2: Execute all tools (no LLM!)
        evidence = self.execute_plan(plan)
        
        # Phase 3: Synthesize final answer
        final_answer = self.solve(question, plan, evidence)
        
        print(f"\n{'='*60}")
        print(f"✅ FINAL ANSWER:")
        print(final_answer)
        print(f"{'='*60}")
        print(f"\n💰 LLM CALLS USED: 2 (vs {len(plan) + 1} in ReACT)")
        
        return final_answer


# ─── Test ReWOO ───
if __name__ == "__main__":
    agent = ReWOOAgent()
    result = agent.run(
        "What are the top 3 AI research labs by publications in 2024, "
        "and what percentage of total AI papers did they publish?"
    )
```

---

## 5.5 Tree Search for Agents

---

### What is Tree Search?

**Simple definition:**
Instead of following ONE path of thoughts and actions, the agent **explores multiple possible paths** like a tree, evaluates each path, and chooses the best one.

---

### 🏠 Real-World Analogy:

**A chess player thinking ahead:**

```
Current position: My turn to move

Branch A: Move knight to d5
   → Branch A1: Opponent moves queen
      → Branch A1a: I take their bishop → Score: 7/10
      → Branch A1b: I castle → Score: 5/10
   → Branch A2: Opponent moves pawn
      → Branch A2a: I take knight → Score: 8/10 ⭐

Branch B: Move bishop to f4
   → Branch B1: Opponent moves rook
      → Branch B1a: I move king → Score: 3/10
      → Branch B1b: I sacrifice knight → Score: 4/10

BEST PATH: Branch A → A2 → A2a (Score: 8/10)
```

**The chess player doesn't just play the first move that comes to mind. They think ahead along MULTIPLE branches and choose the best path.**

---

### Types of Tree Search in Agents:

---

### Type 1: ToT — Tree of Thoughts

**Paper:** "Tree of Thoughts: Deliberate Problem Solving with LLMs" (Yao et al., 2023)

```
Root: User Question
    │
    ├── Thought Path 1: Approach problem via X
    │       ├── Step 1a → evaluate → score 6/10
    │       └── Step 1b → evaluate → score 8/10 ⭐
    │
    ├── Thought Path 2: Approach problem via Y
    │       ├── Step 2a → evaluate → score 4/10
    │       └── Step 2b → evaluate → score 7/10
    │
    └── Thought Path 3: Approach problem via Z
            ├── Step 3a → evaluate → score 9/10 ⭐⭐
            └── Step 3b → evaluate → score 5/10

Best path: Path 3 → Step 3a (score 9/10)
```

---

### Type 2: MCTS — Monte Carlo Tree Search

**Used in:** AlphaGo, game-playing AI, complex reasoning

```
1. SELECTION: Go down tree following best nodes
2. EXPANSION: Add new possible actions
3. SIMULATION: "Imagine" how this path plays out
4. BACKPROPAGATION: Update scores back up the tree
5. Repeat many times → choose best path
```

---

### 💻 Tree of Thoughts Implementation:

```python
import openai
import json
from typing import List, Dict
from dataclasses import dataclass, field

client = openai.OpenAI(api_key="your-api-key")


@dataclass
class ThoughtNode:
    """
    One node in the Tree of Thoughts.
    Represents one possible direction of thinking.
    """
    thought: str          # The actual thought/reasoning
    score: float = 0.0    # How good is this thought? (0-10)
    depth: int = 0        # How deep in the tree?
    children: List = field(default_factory=list)  # Child thoughts
    parent: 'ThoughtNode' = None  # Parent thought
    is_terminal: bool = False     # Is this a final answer?
    answer: str = ""              # Final answer if terminal


class TreeOfThoughts:
    """
    Tree of Thoughts Agent.
    
    Instead of one linear chain of thought,
    explores MULTIPLE thought branches and 
    picks the most promising path.
    
    Better for:
    - Complex reasoning problems
    - Creative tasks with many possible approaches
    - Tasks where first intuition might be wrong
    """
    
    def __init__(self, 
                 branching_factor: int = 3,   # How many branches per node
                 max_depth: int = 3,           # How deep to go
                 beam_width: int = 2):         # How many best paths to keep
        
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self.beam_width = beam_width
    
    def generate_thoughts(self, 
                         question: str, 
                         current_thought: str,
                         depth: int) -> List[str]:
        """
        Generate multiple possible next thoughts.
        Like a chess player considering multiple moves.
        """
        
        context = f"Question: {question}"
        if current_thought:
            context += f"\nCurrent thinking: {current_thought}"
        
        prompt = f"""
        {context}
        
        Generate {self.branching_factor} DIFFERENT approaches or 
        next steps to answer this question.
        
        Each approach should be:
        - Distinctly different from the others
        - A concrete direction to explore
        - Specific and actionable
        
        Output as JSON:
        {{
            "thoughts": [
                "First distinct approach...",
                "Second distinct approach...",
                "Third distinct approach..."
            ]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        return data.get("thoughts", [])
    
    def evaluate_thought(self, 
                        question: str, 
                        thought_path: List[str]) -> Dict:
        """
        Score a thought path: how promising is it?
        This is the key step that separates good paths from bad ones.
        """
        
        path_text = " → ".join(thought_path)
        
        eval_prompt = f"""
        Question: {question}
        
        Thinking path explored: {path_text}
        
        Evaluate this thinking path on these criteria:
        1. Relevance (0-10): Does it address the actual question?
        2. Completeness (0-10): Would following this path give a full answer?
        3. Feasibility (0-10): Is this practically achievable?
        4. Uniqueness (0-10): Does it offer insights others might miss?
        
        Output as JSON:
        {{
            "relevance": 8,
            "completeness": 7,
            "feasibility": 9,
            "uniqueness": 6,
            "overall_score": 7.5,
            "assessment": "one sentence summary",
            "should_explore_further": true/false
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def generate_answer(self, question: str, best_path: List[str]) -> str:
        """
        Using the best thought path found,
        generate the final comprehensive answer.
        """
        
        path_text = "\n".join([f"Step {i+1}: {t}" 
                               for i, t in enumerate(best_path)])
        
        answer_prompt = f"""
        Question: {question}
        
        Thinking process (best path found):
        {path_text}
        
        Using this reasoning path, write a complete, 
        accurate, well-structured answer.
        Include:
        - Direct answer to the question
        - Supporting reasoning and evidence
        - Clear structure with any relevant details
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": answer_prompt}]
        )
        
        return response.choices[0].message.content
    
    def run(self, question: str) -> str:
        """
        Main Tree of Thoughts algorithm:
        
        1. Generate multiple initial thoughts
        2. Evaluate each thought
        3. Keep best beam_width thoughts
        4. Expand each further
        5. Repeat to max_depth
        6. Generate answer from best final path
        """
        
        print(f"\n{'='*60}")
        print(f"🌳 TREE OF THOUGHTS STARTING")
        print(f"Question: {question}")
        print(f"Branching factor: {self.branching_factor}")
        print(f"Max depth: {self.max_depth}")
        print(f"Beam width: {self.beam_width}")
        print(f"{'='*60}")
        
        # Current beam: list of (thought_path, score)
        # Start with empty path
        current_beam = [([], 0.0)]
        
        for depth in range(self.max_depth):
            
            print(f"\n🌿 DEPTH {depth + 1}")
            print(f"Exploring {len(current_beam)} path(s)...")
            
            all_new_paths = []
            
            # Expand each path in the beam
            for path, path_score in current_beam:
                
                current_thought = path[-1] if path else ""
                
                # Generate new thoughts from this path
                new_thoughts = self.generate_thoughts(
                    question, current_thought, depth
                )
                
                print(f"  Generated {len(new_thoughts)} new thoughts")
                
                # Evaluate each new thought
                for thought in new_thoughts:
                    
                    new_path = path + [thought]
                    evaluation = self.evaluate_thought(question, new_path)
                    score = evaluation.get("overall_score", 5.0)
                    
                    print(f"  • '{thought[:60]}...' → Score: {score}/10")
                    
                    all_new_paths.append((new_path, score))
            
            # Keep only the best beam_width paths (beam search!)
            all_new_paths.sort(key=lambda x: x[1], reverse=True)
            current_beam = all_new_paths[:self.beam_width]
            
            print(f"\n  ✅ Top {self.beam_width} path(s) kept:")
            for i, (path, score) in enumerate(current_beam):
                print(f"  Path {i+1} (score {score:.1f}): {path[-1][:80]}...")
        
        # Best path is the first in beam (highest scored)
        best_path, best_score = current_beam[0]
        
        print(f"\n🏆 BEST PATH FOUND (score: {best_score:.1f})")
        for i, thought in enumerate(best_path):
            print(f"  Step {i+1}: {thought}")
        
        # Generate final answer from best path
        print(f"\n📝 GENERATING FINAL ANSWER...")
        final_answer = self.generate_answer(question, best_path)
        
        print(f"\n✅ FINAL ANSWER:\n{final_answer}")
        
        return final_answer


# ─── Test Tree of Thoughts ───
if __name__ == "__main__":
    
    tot = TreeOfThoughts(
        branching_factor=3,
        max_depth=2,
        beam_width=2
    )
    
    result = tot.run(
        "What strategy should a startup follow to compete "
        "against established AI companies in 2025?"
    )
```

---

### 📊 Comparison of Multi-Step Agent Approaches:

```
┌─────────────┬──────────┬──────────┬──────────┬──────────┐
│ Framework   │ Speed    │ Cost     │ Quality  │ Best For │
├─────────────┼──────────┼──────────┼──────────┼──────────┤
│ ReACT       │ Medium   │ Medium   │ Good     │ General  │
│             │          │          │          │ research │
├─────────────┼──────────┼──────────┼──────────┼──────────┤
│ Reflexion   │ Slow     │ High     │ Better   │ Tasks    │
│             │          │          │          │ needing  │
│             │          │          │          │ accuracy │
├─────────────┼──────────┼──────────┼──────────┼──────────┤
│ ReWOO       │ Fast     │ Low      │ Good     │ Known    │
│             │          │          │          │ step     │
│             │          │          │          │ tasks    │
├─────────────┼──────────┼──────────┼──────────┼──────────┤
│ Tree of     │ Slow     │ Very     │ Best     │ Complex  │
│ Thoughts    │          │ High     │          │ reasoning│
│             │          │          │          │ problems │
└─────────────┴──────────┴──────────┴──────────┴──────────┘
```

---

# 👥 CHAPTER 6: Multi-Agent Systems

---

## What is a Multi-Agent System?

**Simple definition:**
Multiple AI agents working together, each with specialized roles, communicating with each other, to solve problems that one agent alone cannot handle well.

---

### 🏠 Real-World Analogy:

**A hospital emergency room:**

```
TRIAGE NURSE (Router Agent):
"Car accident patient — multiple injuries"
        ↓ (assigns to specialists)
        
TRAUMA SURGEON (Specialist Agent 1):
"Handles the physical injuries"
        ↓ (reports to)
        
NEUROLOGIST (Specialist Agent 2):
"Checks for brain injury"
        ↓ (reports to)
        
CARDIOLOGIST (Specialist Agent 3):
"Monitors heart"
        ↓
ATTENDING PHYSICIAN (Orchestrator Agent):
"Coordinates all specialists, makes final decisions"
        ↓
PATIENT TREATED SUCCESSFULLY ✅
```

No single doctor can do everything. Specialists working together = better outcome.

---

## 6.1 Challenges of Multi-Agent Systems

---

### Challenge 1: Communication Overhead

```
Problem: Agents spend more time talking to each other
         than actually doing work.

Example:
Agent A → sends message to Agent B (takes time)
Agent B → processes message (takes time)
Agent B → sends reply to Agent A (takes time)
Agent A → processes reply (takes time)
[All this before any real work is done!]

Solution: Design clear, minimal communication protocols.
          Don't over-communicate.
```

---

### Challenge 2: Coordination and Conflicts

```
Problem: Two agents try to do the same task or give 
         conflicting answers.

Example:
Agent A says: "The answer is X"
Agent B says: "The answer is Y"
No one decides which is correct!

Solution: Clear hierarchy. One orchestrator makes final calls.
          Or voting system for conflicts.
```

---

### Challenge 3: Error Propagation

```
Problem: If early agent makes mistake, all later agents
         build on that mistake.

Example:
Agent 1 (Search): Returns wrong information
        ↓
Agent 2 (Analyzer): Analyzes the wrong information
        ↓
Agent 3 (Writer): Writes answer based on wrong analysis
        ↓
Final answer: Completely wrong ❌

Solution: Each agent validates input before using it.
          Add verification agents.
```

---

### Challenge 4: Infinite Loops

```
Problem: Agent A waits for Agent B.
         Agent B waits for Agent C.
         Agent C waits for Agent A.
         → Deadlock! Nothing moves!

Solution: Timeouts on all agent communication.
          Max iteration limits.
          Supervisor that monitors and breaks deadlocks.
```

---

### Challenge 5: Cost Explosion

```
Problem: 10 agents each making 5 LLM calls each
         = 50 LLM calls for one user question!

At $0.01 per call: $0.50 per question
1000 users/day: $500/day in API costs alone!

Solution: Only use agents when necessary.
          Use smaller/cheaper models for simple sub-tasks.
          Cache common results.
```

---

### Challenge 6: Trust and Safety

```
Problem: Agent A tells Agent B: "Delete all user data"
         Should Agent B follow this instruction?
         Who verifies that Agent A has authority?

Solution: 
- Permission system for each agent
- Actions require approval for high-risk operations
- Audit logging of all agent actions
- Human-in-the-loop for dangerous actions
```

---

## 6.2 Use Cases for Multi-Agent Systems

---

### Use Case 1: Our Perplexity Clone (Research Agent)

```
User Question
     ↓
COORDINATOR AGENT: Analyzes question, creates research plan
     ↓
SEARCH AGENT 1: Searches for recent news
SEARCH AGENT 2: Searches for academic sources    [Parallel]
SEARCH AGENT 3: Searches for expert opinions
     ↓
FACT-CHECK AGENT: Verifies claims across sources
     ↓
WRITER AGENT: Synthesizes into clear answer
     ↓
CITATION AGENT: Formats sources properly
     ↓
Final answer with proper citations ✅
```

---

### Use Case 2: Software Development Team

```
PRODUCT MANAGER AGENT: Receives feature request
     ↓
ARCHITECT AGENT: Designs technical solution
     ↓
CODER AGENT: Writes the code
     ↓
TESTER AGENT: Writes and runs tests
     ↓
CODE REVIEWER AGENT: Reviews code quality
     ↓
DOCUMENTATION AGENT: Writes documentation
     ↓
Complete feature delivered ✅
```

---

### Use Case 3: Financial Analysis

```
DATA COLLECTOR AGENT: Gets market data
     ↓
FUNDAMENTAL ANALYST: Analyzes company financials
TECHNICAL ANALYST: Analyzes price patterns        [Parallel]
SENTIMENT ANALYST: Analyzes news sentiment
     ↓
RISK ASSESSOR AGENT: Evaluates risk levels
     ↓
REPORT WRITER AGENT: Creates investment report
     ↓
Investment recommendation report ✅
```

---

## 6.3 A2A Protocol — Agent-to-Agent Communication

---

### What is A2A Protocol?

**A2A = Agent-to-Agent**

A2A is a standard protocol (created by Google, 2025) that defines **how AI agents talk to each other** — regardless of which company made them or what framework they use.

**Think of it like:** Email protocol. Gmail can send email to Outlook because both follow the same email standards (SMTP, IMAP). A2A does the same for agents.

---

### Why A2A is Needed:

```
WITHOUT A2A:
LangChain agent cannot talk to CrewAI agent
OpenAI agent cannot talk to Claude agent
Your custom agent cannot talk to Google agent

Each uses different formats → No interoperability

WITH A2A:
ANY agent can talk to ANY other agent
Standard format everyone follows
Build once, work with everyone
```

---

### A2A Core Concepts:

```
1. AGENT CARD
   ─────────────────────────────────
   Like a business card for an agent.
   Describes what the agent can do.
   
   {
     "name": "WebSearchAgent",
     "description": "Searches the web for information",
     "capabilities": ["web_search", "summarization"],
     "endpoint": "https://myagent.com/api",
     "input_format": {...},
     "output_format": {...}
   }

2. TASK
   ─────────────────────────────────
   A request from one agent to another.
   
   {
     "task_id": "task_123",
     "from_agent": "OrchestratorAgent",
     "to_agent": "WebSearchAgent",
     "instruction": "Search for latest AI news",
     "parameters": {"query": "AI news 2025"},
     "expected_output": "list of articles"
   }

3. ARTIFACT
   ─────────────────────────────────
   The output/result of a task.
   
   {
     "task_id": "task_123",
     "status": "completed",
     "result": [...search results...],
     "metadata": {
       "sources": [...],
       "time_taken": "2.3s"
     }
   }
```

---

### 💻 A2A Communication Implementation:

```python
import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    """Status of a task in the A2A system."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentCard:
    """
    A2A Agent Card — describes an agent's capabilities.
    Other agents read this to know what to send here.
    """
    name: str
    description: str
    capabilities: list
    endpoint: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Task:
    """
    A2A Task — request from one agent to another.
    """
    task_id: str
    from_agent: str
    to_agent: str
    instruction: str
    parameters: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d


@dataclass
class Artifact:
    """
    A2A Artifact — result from completing a task.
    """
    task_id: str
    status: str
    result: Any
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class A2AAgent:
    """
    Base class for A2A-compatible agents.
    Any agent built on this can communicate with any other.
    """
    
    def __init__(self, name: str, description: str, capabilities: list):
        self.card = AgentCard(
            name=name,
            description=description,
            capabilities=capabilities,
            endpoint=f"http://localhost:8000/{name.lower()}"
        )
        self.task_history = []
        print(f"🤖 Agent '{name}' initialized")
        print(f"   Capabilities: {capabilities}")
    
    def get_card(self) -> dict:
        """Share this agent's capabilities."""
        return self.card.to_dict()
    
    async def receive_task(self, task: Task) -> Artifact:
        """
        Receive and process a task from another agent.
        Subclasses implement the actual logic.
        """
        task.status = TaskStatus.IN_PROGRESS
        self.task_history.append(task)
        
        try:
            result = await self.process_task(task)
            task.status = TaskStatus.COMPLETED
            
            return Artifact(
                task_id=task.task_id,
                status="completed",
                result=result
            )
        except Exception as e:
            task.status = TaskStatus.FAILED
            return Artifact(
                task_id=task.task_id,
                status="failed",
                result=None,
                error=str(e)
            )
    
    async def process_task(self, task: Task) -> Any:
        """Override this in subclasses."""
        raise NotImplementedError
    
    async def send_task(self, 
                        to_agent: 'A2AAgent',
                        instruction: str,
                        parameters: Dict) -> Artifact:
        """
        Send a task to another agent.
        This is how agents communicate in A2A.
        """
        
        task = Task(
            task_id=str(uuid.uuid4()),
            from_agent=self.card.name,
            to_agent=to_agent.card.name,
            instruction=instruction,
            parameters=parameters
        )
        
        print(f"\n  📤 {self.card.name} → {to_agent.card.name}")
        print(f"     Task: {instruction}")
        print(f"     Params: {parameters}")
        
        artifact = await to_agent.receive_task(task)
        
        print(f"\n  📥 {to_agent.card.name} → {self.card.name}")
        print(f"     Status: {artifact.status}")
        print(f"     Result preview: {str(artifact.result)[:100]}...")
        
        return artifact


# ─── Concrete Agent Implementations ───

class SearchAgent(A2AAgent):
    """Specialist agent for web searching."""
    
    def __init__(self):
        super().__init__(
            name="SearchAgent",
            description="Searches the web for current information",
            capabilities=["web_search", "news_search"]
        )
    
    async def process_task(self, task: Task) -> Any:
        """Execute a web search."""
        await asyncio.sleep(0.1)  # Simulate API call
        
        query = task.parameters.get("query", "")
        print(f"    🌐 SearchAgent: Searching for '{query}'")
        
        # In production: real API call here
        return {
            "query": query,
            "results": [
                {"title": f"Result 1 for {query}", "url": "http://source1.com", 
                 "snippet": f"Information about {query}..."},
                {"title": f"Result 2 for {query}", "url": "http://source2.com",
                 "snippet": f"More about {query}..."},
                {"title": f"Result 3 for {query}", "url": "http://source3.com",
                 "snippet": f"Additional {query} details..."}
            ],
            "total_results": 3
        }


class SummarizerAgent(A2AAgent):
    """Specialist agent for summarizing content."""
    
    def __init__(self):
        super().__init__(
            name="SummarizerAgent",
            description="Summarizes and synthesizes information",
            capabilities=["summarization", "synthesis", "key_points"]
        )
    
    async def process_task(self, task: Task) -> Any:
        """Summarize provided content."""
        await asyncio.sleep(0.1)
        
        content = task.parameters.get("content", "")
        instruction = task.instruction
        
        print(f"    📝 SummarizerAgent: Summarizing content...")
        
        # In production: call LLM here
        return {
            "summary": f"Synthesized summary of the provided content about {instruction}",
            "key_points": [
                "Key finding 1 from the research",
                "Key finding 2 from the research",
                "Key finding 3 from the research"
            ],
            "word_count": 150
        }


class FactCheckerAgent(A2AAgent):
    """Specialist agent for fact verification."""
    
    def __init__(self):
        super().__init__(
            name="FactCheckerAgent",
            description="Verifies factual accuracy of content",
            capabilities=["fact_checking", "verification", "source_validation"]
        )
    
    async def process_task(self, task: Task) -> Any:
        """Verify facts in the provided content."""
        await asyncio.sleep(0.1)
        
        content = task.parameters.get("content", "")
        print(f"    ✅ FactCheckerAgent: Verifying claims...")
        
        return {
            "verified": True,
            "confidence": 0.87,
            "flagged_claims": [],
            "sources_verified": 3
        }


class OrchestratorAgent(A2AAgent):
    """
    The main orchestrator agent.
    Coordinates all other agents to answer user questions.
    """
    
    def __init__(self):
        super().__init__(
            name="OrchestratorAgent",
            description="Coordinates research agents to answer questions",
            capabilities=["orchestration", "planning", "synthesis"]
        )
        
        # Register available sub-agents
        self.search_agent = SearchAgent()
        self.summarizer_agent = SummarizerAgent()
        self.fact_checker_agent = FactCheckerAgent()
        
        print(f"\n🎯 Orchestrator ready with {3} sub-agents")
    
    async def process_task(self, task: Task) -> Any:
        """The main orchestration logic."""
        return await self.answer_question(task.instruction)
    
    async def answer_question(self, question: str) -> dict:
        """
        Coordinate multiple agents to answer a question.
        Uses A2A protocol throughout.
        """
        
        print(f"\n{'='*60}")
        print(f"🎯 ORCHESTRATOR: Processing question")
        print(f"Question: {question}")
        print(f"{'='*60}")
        
        # Step 1: Search for information
        print(f"\n📋 Step 1: Requesting search from SearchAgent...")
        search_result = await self.send_task(
            to_agent=self.search_agent,
            instruction=f"Search for comprehensive information about: {question}",
            parameters={"query": question, "max_results": 5}
        )
        
        # Step 2: Summarize the search results (in parallel with fact-check)
        print(f"\n📋 Step 2: Requesting summarization AND fact-checking (parallel)...")
        
        summary_task = self.send_task(
            to_agent=self.summarizer_agent,
            instruction=f"Summarize search results for: {question}",
            parameters={"content": str(search_result.result)}
        )
        
        fact_check_task = self.send_task(
            to_agent=self.fact_checker_agent,
            instruction="Verify factual accuracy",
            parameters={"content": str(search_result.result)}
        )
        
        # Run both in parallel!
        summary_result, fact_check_result = await asyncio.gather(
            summary_task, fact_check_task
        )
        
        # Step 3: Compile final answer
        print(f"\n📋 Step 3: Compiling final answer...")
        
        final_answer = {
            "question": question,
            "answer": summary_result.result.get("summary", ""),
            "key_points": summary_result.result.get("key_points", []),
            "verified": fact_check_result.result.get("verified", False),
            "confidence": fact_check_result.result.get("confidence", 0),
            "sources": search_result.result.get("results", []),
            "agent_chain": [
                "OrchestratorAgent",
                "SearchAgent",
                "SummarizerAgent (parallel)",
                "FactCheckerAgent (parallel)",
                "OrchestratorAgent (synthesis)"
            ]
        }
        
        return final_answer


# ─── Test Multi-Agent A2A System ───
async def main():
    
    # Create the orchestrator (which creates all sub-agents)
    orchestrator = OrchestratorAgent()
    
    # Discover available agents (A2A capability)
    print("\n📋 AGENT CARDS (A2A Discovery):")
    for agent in [orchestrator.search_agent, 
                  orchestrator.summarizer_agent,
                  orchestrator.fact_checker_agent]:
        card = agent.get_card()
        print(f"\n  🤖 {card['name']}")
        print(f"     Description: {card['description']}")
        print(f"     Capabilities: {card['capabilities']}")
    
    # Answer a question using the multi-agent system
    result = await orchestrator.answer_question(
        "What are the most important AI breakthroughs of 2025?"
    )
    
    print(f"\n{'='*60}")
    print(f"🎉 FINAL RESULT FROM MULTI-AGENT SYSTEM:")
    print(f"{'='*60}")
    print(f"Answer: {result['answer']}")
    print(f"\nKey Points:")
    for point in result['key_points']:
        print(f"  • {point}")
    print(f"\nVerified: {result['verified']} (Confidence: {result['confidence']})")
    print(f"\nAgent Chain Used: {' → '.join(result['agent_chain'])}")
    print(f"\nSources ({len(result['sources'])}):")
    for source in result['sources']:
        print(f"  • {source['url']}: {source['title']}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

# 📊 CHAPTER 7: Agent Evaluation

---

## Why is Agent Evaluation So Hard?

---

### 🔮 Prediction First:

**What beginners think:**
> "Just check if the answer is correct."

**The real challenge:**
> Agent evaluation is much harder than model evaluation because agents have **multiple steps**, **dynamic behavior**, **tool usage**, **variable paths**, and **no single correct answer** for many questions.

---

### 🏠 Real-World Analogy:

**Evaluating a student's research paper:**

```
You can't just ask: "Is the paper correct?"

You need to evaluate:
1. Did they research enough sources?
2. Is their reasoning logical?
3. Are their citations accurate?
4. Is the writing clear?
5. Did they address the actual question?
6. Did they manage their time well?
7. Is the conclusion supported by evidence?

Each dimension needs its own evaluation!
```

**Same with AI agents!**

---

## 7.1 What to Evaluate

---

### Dimension 1: Task Completion

```
Did the agent actually finish the task?

Metric: Success rate (0-100%)

Examples:
- Did it answer the question? ✅/❌
- Did it find relevant sources? ✅/❌
- Did it complete all required steps? ✅/❌
```

---

### Dimension 2: Answer Quality

```
How good is the final answer?

Metrics:
- Accuracy: Is the information correct?
- Completeness: Does it fully answer the question?
- Relevance: Is it actually about what was asked?
- Clarity: Is it easy to understand?

Scale: 1-5 for each dimension
```

---

### Dimension 3: Efficiency

```
How efficiently did the agent work?

Metrics:
- Number of steps taken
- Number of tool calls made
- Time to complete
- API cost ($ spent)
- Token count used

Goal: High quality with minimum steps/cost
```

---

### Dimension 4: Tool Usage

```
Did the agent use tools correctly?

Metrics:
- Tool selection accuracy: Right tool for the job?
- Tool call success rate: Tools called correctly?
- Unnecessary tool calls: Over-using tools?
- Missing tool calls: Under-using tools when needed?
```

---

### Dimension 5: Reasoning Quality

```
Was the agent's thinking process logical?

Metrics:
- Logical coherence of thought chain
- Correct identification of what information is needed
- Proper handling of contradictory information
- Knowing when to stop (not over-researching)
```

---

### Dimension 6: Safety and Reliability

```
Did the agent behave safely?

Metrics:
- Hallucination rate: Making up facts?
- Harmful content: Producing dangerous content?
- Error handling: Graceful failure when things go wrong?
- Consistency: Same answer for same question?
```

---

## 7.2 Evaluation Methods

---

### Method 1: Human Evaluation (Gold Standard)

```
Humans read agent's work and score it.

Pros:
+ Most accurate
+ Catches nuanced errors
+ Can evaluate creativity and quality

Cons:
- Expensive (human time)
- Slow (can't evaluate thousands of examples)
- Subjective (different humans give different scores)
- Doesn't scale

Best for: Final evaluation of important use cases
```

---

### Method 2: LLM-as-Judge

```
Use a powerful LLM (GPT-4, Claude) to evaluate 
the agent's output.

Pros:
+ Scalable (evaluate thousands automatically)
+ Fast and cheap
+ Can evaluate complex dimensions

Cons:
- LLM judge can also make mistakes
- Biased toward its own style
- Might miss domain-specific errors

Best for: Large-scale automatic evaluation
```

---

### Method 3: Reference-Based Evaluation

```
Compare agent output to a "gold standard" reference answer.

Metrics:
- BLEU score: Word overlap with reference
- ROUGE score: N-gram overlap
- BERTScore: Semantic similarity
- Exact match: For factual answers

Pros:
+ Fully automatic
+ Objective

Cons:
- Need reference answers (expensive to create)
- One correct answer assumption (often wrong)
- Misses creativity and alternative correct answers

Best for: Factual Q&A tasks with clear correct answers
```

---

### Method 4: Trajectory Evaluation

```
Evaluate the PROCESS, not just the final answer.
Look at each step the agent took.

Check:
- Was each tool call justified?
- Were observations correctly interpreted?
- Were wrong paths abandoned appropriately?
- Was the reasoning chain logical?

Best for: Complex multi-step agent evaluation
```

---

## 7.3 Evaluation Frameworks

---

### Framework 1: RAGAS (for RAG + Agent evaluation)

```
RAGAS metrics for our Perplexity agent:

1. Answer Relevancy
   "How relevant is the answer to the question?"
   Score: 0 to 1

2. Faithfulness
   "Is every claim in the answer supported by sources?"
   Score: 0 to 1

3. Context Precision
   "Did the agent retrieve the right information?"
   Score: 0 to 1

4. Context Recall
   "Did the agent find ALL needed information?"
   Score: 0 to 1
```

---

### Framework 2: AgentBench

```
Benchmarks specifically designed for agent evaluation.

Tests agents on:
- Operating system tasks
- Database queries
- Web browsing tasks
- Knowledge retrieval
- Code execution

Measures:
- Task completion rate
- Error rate
- Step efficiency
```

---

### Framework 3: Custom Evaluation Pipeline

---

### 💻 Complete Agent Evaluation System:

```python
import openai
import json
from typing import List, Dict, Any
from dataclasses import dataclass
import statistics

client = openai.OpenAI(api_key="your-api-key")


@dataclass
class EvaluationResult:
    """Result of evaluating one agent response."""
    question: str
    agent_answer: str
    reference_answer: str
    
    # Scores (0-10)
    accuracy_score: float
    completeness_score: float
    relevance_score: float
    clarity_score: float
    
    # Tool usage metrics
    tool_calls_made: int
    unnecessary_tool_calls: int
    missing_tool_calls: int
    
    # Efficiency metrics
    steps_taken: int
    tokens_used: int
    time_seconds: float
    
    # Safety metrics
    has_hallucination: bool
    has_citations: bool
    
    @property
    def quality_score(self) -> float:
        """Average of all quality dimensions."""
        return statistics.mean([
            self.accuracy_score,
            self.completeness_score,
            self.relevance_score,
            self.clarity_score
        ])
    
    @property
    def tool_accuracy(self) -> float:
        """How accurately were tools used? (0-1)"""
        total = self.tool_calls_made + self.missing_tool_calls
        if total == 0:
            return 1.0
        correct = max(0, self.tool_calls_made - self.unnecessary_tool_calls)
        return correct / total
    
    def to_dict(self) -> dict:
        return {
            "question": self.question[:50] + "...",
            "quality_score": round(self.quality_score, 2),
            "accuracy": self.accuracy_score,
            "completeness": self.completeness_score,
            "relevance": self.relevance_score,
            "clarity": self.clarity_score,
            "tool_accuracy": round(self.tool_accuracy, 2),
            "efficiency": {
                "steps": self.steps_taken,
                "tokens": self.tokens_used,
                "time_sec": self.time_seconds
            },
            "safety": {
                "hallucination": self.has_hallucination,
                "has_citations": self.has_citations
            }
        }


class AgentEvaluator:
    """
    Comprehensive evaluation system for AI agents.
    Uses LLM-as-Judge for quality metrics.
    """
    
    def __init__(self):
        self.results: List[EvaluationResult] = []
    
    def llm_judge(self, 
                  question: str, 
                  agent_answer: str, 
                  reference_answer: str = "") -> Dict:
        """
        Use GPT-4 as a judge to evaluate answer quality.
        This is the LLM-as-Judge pattern.
        """
        
        reference_text = ""
        if reference_answer:
            reference_text = f"\nReference Answer:\n{reference_answer}\n"
        
        judge_prompt = f"""
        You are an expert evaluator for AI research agents.
        
        Question: {question}
        
        Agent's Answer:
        {agent_answer}
        {reference_text}
        
        Evaluate the agent's answer on these dimensions (score 0-10):
        
        1. ACCURACY (0-10):
           - Are all facts correct?
           - No false information?
           - Numbers and statistics accurate?
        
        2. COMPLETENESS (0-10):
           - Does it fully answer the question?
           - All important aspects covered?
           - No significant gaps?
        
        3. RELEVANCE (0-10):
           - Is the answer on-topic?
           - No unnecessary information?
           - Directly addresses what was asked?
        
        4. CLARITY (0-10):
           - Easy to understand?
           - Well-organized?
           - Clear language?
        
        5. HALLUCINATION CHECK:
           - Does the answer contain made-up facts?
           - Claims not supported by evidence?
        
        6. CITATION CHECK:
           - Does it cite sources?
           - Are sources mentioned?
        
        Output ONLY valid JSON:
        {{
            "accuracy": 8,
            "completeness": 7,
            "relevance": 9,
            "clarity": 8,
            "has_hallucination": false,
            "has_citations": true,
            "feedback": "Specific feedback about the answer",
            "strengths": ["strength 1", "strength 2"],
            "weaknesses": ["weakness 1"]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": judge_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1  # Low temperature for consistent scoring
        )
        
        return json.loads(response.choices[0].message.content)
    
    def evaluate_trajectory(self, 
                            trajectory: List[Dict]) -> Dict:
        """
        Evaluate the PROCESS the agent used.
        Checks each step, not just final answer.
        
        trajectory: List of steps like:
        [
          {"type": "thought", "content": "..."},
          {"type": "action", "tool": "search_web", "input": "..."},
          {"type": "observation", "content": "..."},
          ...
        ]
        """
        
        tool_calls = [s for s in trajectory if s.get("type") == "action"]
        thoughts = [s for s in trajectory if s.get("type") == "thought"]
        
        trajectory_text = "\n".join([
            f"[{s['type'].upper()}]: {s.get('content', s.get('tool', ''))}"
            for s in trajectory
        ])
        
        traj_prompt = f"""
        Evaluate this agent's reasoning trajectory:
        
        {trajectory_text}
        
        Score on these dimensions (0-10):
        
        1. REASONING_QUALITY: Was each thought logical and necessary?
        2. TOOL_SELECTION: Did it use the right tools?
        3. EFFICIENCY: Did it avoid unnecessary steps?
        4. ERROR_HANDLING: Did it handle problems well?
        
        Also count:
        - unnecessary_tool_calls: Tools called that weren't needed
        - missing_tool_calls: Times it should have used a tool but didn't
        
        Output as JSON:
        {{
            "reasoning_quality": 8,
            "tool_selection": 7,
            "efficiency": 9,
            "error_handling": 8,
            "unnecessary_tool_calls": 1,
            "missing_tool_calls": 0,
            "trajectory_feedback": "Specific feedback"
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": traj_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        return json.loads(response.choices[0].message.content)
    
    def evaluate(self,
                question: str,
                agent_answer: str,
                trajectory: List[Dict],
                steps_taken: int,
                tokens_used: int,
                time_seconds: float,
                reference_answer: str = "") -> EvaluationResult:
        """
        Complete evaluation of one agent interaction.
        """
        
        print(f"\n📊 EVALUATING: '{question[:50]}...'")
        
        # Quality evaluation (LLM judge)
        print("  🔍 Running LLM judge evaluation...")
        quality_eval = self.llm_judge(question, agent_answer, reference_answer)
        
        # Trajectory evaluation
        print("  🔍 Running trajectory evaluation...")
        traj_eval = self.evaluate_trajectory(trajectory)
        
        # Create evaluation result
        result = EvaluationResult(
            question=question,
            agent_answer=agent_answer,
            reference_answer=reference_answer,
            
            accuracy_score=quality_eval.get("accuracy", 5),
            completeness_score=quality_eval.get("completeness", 5),
            relevance_score=quality_eval.get("relevance", 5),
            clarity_score=quality_eval.get("clarity", 5),
            
            tool_calls_made=len([s for s in trajectory 
                                 if s.get("type") == "action"]),
            unnecessary_tool_calls=traj_eval.get("unnecessary_tool_calls", 0),
            missing_tool_calls=traj_eval.get("missing_tool_calls", 0),
            
            steps_taken=steps_taken,
            tokens_used=tokens_used,
            time_seconds=time_seconds,
            
            has_hallucination=quality_eval.get("has_hallucination", False),
            has_citations=quality_eval.get("has_citations", False)
        )
        
        self.results.append(result)
        
        # Print evaluation
        print(f"\n  📈 SCORES:")
        print(f"     Quality:      {result.quality_score:.1f}/10")
        print(f"     Accuracy:     {result.accuracy_score:.1f}/10")
        print(f"     Completeness: {result.completeness_score:.1f}/10")
        print(f"     Tool usage:   {result.tool_accuracy:.0%}")
        print(f"     Hallucination: {'⚠️ YES' if result.has_hallucination else '✅ NO'}")
        print(f"     Citations:    {'✅ YES' if result.has_citations else '❌ NO'}")
        print(f"\n  💬 Feedback: {quality_eval.get('feedback', 'N/A')}")
        
        return result
    
    def generate_report(self) -> Dict:
        """
        Generate a comprehensive evaluation report
        across all evaluated interactions.
        """
        
        if not self.results:
            return {"error": "No evaluations completed yet"}
        
        # Calculate aggregate metrics
        avg_quality = statistics.mean([r.quality_score for r in self.results])
        avg_accuracy = statistics.mean([r.accuracy_score for r in self.results])
        avg_completeness = statistics.mean([r.completeness_score for r in self.results])
        avg_tool_accuracy = statistics.mean([r.tool_accuracy for r in self.results])
        avg_steps = statistics.mean([r.steps_taken for r in self.results])
        avg_tokens = statistics.mean([r.tokens_used for r in self.results])
        avg_time = statistics.mean([r.time_seconds for r in self.results])
        
        hallucination_rate = sum(1 for r in self.results 
                                 if r.has_hallucination) / len(self.results)
        citation_rate = sum(1 for r in self.results 
                            if r.has_citations) / len(self.results)
        
        report = {
            "total_evaluations": len(self.results),
            "overall_quality": round(avg_quality, 2),
            
            "quality_breakdown": {
                "accuracy": round(avg_accuracy, 2),
                "completeness": round(avg_completeness, 2),
                "tool_usage": round(avg_tool_accuracy, 2)
            },
            
            "efficiency_metrics": {
                "avg_steps": round(avg_steps, 1),
                "avg_tokens": round(avg_tokens, 0),
                "avg_time_seconds": round(avg_time, 2)
            },
            
            "safety_metrics": {
                "hallucination_rate": f"{hallucination_rate:.0%}",
                "citation_rate": f"{citation_rate:.0%}"
            },
            
            "grade": self._calculate_grade(avg_quality),
            
            "recommendations": self._generate_recommendations(
                avg_quality, avg_accuracy, avg_tool_accuracy, 
                hallucination_rate, citation_rate
            )
        }
        
        return report
    
    def _calculate_grade(self, score: float) -> str:
        if score >= 9: return "A+ (Excellent)"
        elif score >= 8: return "A (Very Good)"
        elif score >= 7: return "B (Good)"
        elif score >= 6: return "C (Acceptable)"
        elif score >= 5: return "D (Needs Improvement)"
        else: return "F (Poor)"
    
    def _generate_recommendations(self, quality, accuracy, 
                                   tool_accuracy, hallucination_rate,
                                   citation_rate) -> List[str]:
        recs = []
        if accuracy < 7:
            recs.append("Improve factual accuracy — add fact-checking step")
        if tool_accuracy < 0.8:
            recs.append("Improve tool selection — refine tool descriptions")
        if hallucination_rate > 0.1:
            recs.append("High hallucination rate — add grounding and verification")
        if citation_rate < 0.8:
            recs.append("Add citations more consistently")
        if quality >= 8:
            recs.append("Agent performing well — consider scaling")
        return recs if recs else ["Agent performance is satisfactory"]
    
    def print_report(self):
        """Print a formatted evaluation report."""
        report = self.generate_report()
        
        print(f"\n{'='*60}")
        print(f"📊 AGENT EVALUATION REPORT")
        print(f"{'='*60}")
        print(f"Total Evaluations: {report['total_evaluations']}")
        print(f"Overall Quality Score: {report['overall_quality']}/10")
        print(f"Grade: {report['grade']}")
        
        print(f"\n📈 Quality Breakdown:")
        for metric, score in report['quality_breakdown'].items():
            bar = "█" * int(score) + "░" * (10 - int(score))
            print(f"  {metric:15} [{bar}] {score}/10")
        
        print(f"\n⚡ Efficiency Metrics:")
        eff = report['efficiency_metrics']
        print(f"  Avg Steps:   {eff['avg_steps']}")
        print(f"  Avg Tokens:  {eff['avg_tokens']}")
        print(f"  Avg Time:    {eff['avg_time_seconds']}s")
        
        print(f"\n🛡️  Safety Metrics:")
        safety = report['safety_metrics']
        print(f"  Hallucination Rate: {safety['hallucination_rate']}")
        print(f"  Citation Rate:      {safety['citation_rate']}")
        
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        print(f"{'='*60}")


# ─── Test the evaluation system ───
if __name__ == "__main__":
    
    evaluator = AgentEvaluator()
    
    # Simulate evaluating an agent response
    sample_trajectory = [
        {"type": "thought", "content": "I need to search for current AI news"},
        {"type": "action", "tool": "search_web", "input": "AI trends 2025"},
        {"type": "observation", "content": "Found 5 results about AI trends"},
        {"type": "thought", "content": "I have enough info to answer"},
        {"type": "action", "tool": "search_web", "input": "More AI news"}  # Unnecessary
    ]
    
    result = evaluator.evaluate(
        question="What are the top AI trends in 2025?",
        agent_answer="""
        The top AI trends in 2025 include:
        1. Agentic AI systems becoming mainstream [Source: TechCrunch]
        2. Multimodal models handling text, image, and audio [Source: OpenAI Blog]
        3. AI agents with tool use and planning capabilities [Source: Anthropic]
        4. Open-source models catching up to proprietary ones [Source: HuggingFace]
        5. AI regulation becoming law in EU and US [Source: Reuters]
        """,
        trajectory=sample_trajectory,
        steps_taken=5,
        tokens_used=1250,
        time_seconds=3.7,
        reference_answer="AI trends include agentic systems, multimodal models, and regulation..."
    )
    
    # Generate full report
    evaluator.print_report()
```

---

# 🏗️ CHAPTER 8: Complete Project Build

## The Full Perplexity-like Agent

---

### 8.1 Complete Architecture

```
┌─────────────────────────────────────────────────────────┐
│              "Ask-the-Web" Agent — Full System          │
│                                                         │
│  ┌──────────┐    ┌──────────────────────────────────┐  │
│  │Streamlit │    │         Agent Core               │  │
│  │   UI     │───▶│                                  │  │
│  │          │    │  ┌────────────┐  ┌────────────┐  │  │
│  │ - Input  │    │  │  ROUTER    │  │  PLANNER   │  │  │
│  │ - Output │    │  │ (classify) │  │ (ReACT)    │  │  │
│  │ - Sources│    │  └────────────┘  └────────────┘  │  │
│  │ - Steps  │    │         ↓               ↓        │  │
│  └──────────┘    │  ┌──────────────────────────┐    │  │
│                  │  │     TOOL EXECUTOR        │    │  │
│                  │  │ ┌────────┐ ┌───────────┐ │    │  │
│                  │  │ │Tavily  │ │Calculator │ │    │  │
│                  │  │ │Search  │ │           │ │    │  │
│                  │  │ └────────┘ └───────────┘ │    │  │
│                  │  └──────────────────────────┘    │  │
│                  │         ↓                        │  │
│                  │  ┌──────────────────────────┐    │  │
│                  │  │    REFLECTION LOOP        │    │  │
│                  │  │  (quality check)          │    │  │
│                  │  └──────────────────────────┘    │  │
│                  │         ↓                        │  │
│                  │  ┌──────────────────────────┐    │  │
│                  │  │   ANSWER GENERATOR        │    │  │
│                  │  │  (with citations)         │    │  │
│                  │  └──────────────────────────┘    │  │
│                  └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

### 8.2 Complete Agent Code

```python
# ═══════════════════════════════════════════════════════════
# FILE: agent.py
# The complete Perplexity-like agent
# ═══════════════════════════════════════════════════════════

import openai
import json
import time
import asyncio
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass, field
from enum import Enum
import os


# ─── Configuration ───

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-key-here")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "your-key-here")

client = openai.OpenAI(api_key=OPENAI_API_KEY)


# ─── Data Classes ───

@dataclass
class Source:
    """A web source found during research."""
    title: str
    url: str
    snippet: str
    relevance_score: float = 0.0


@dataclass
class AgentStep:
    """One step in the agent's reasoning process."""
    step_type: str      # "thought", "action", "observation", "answer"
    content: str
    tool_used: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentResponse:
    """Complete response from the agent."""
    question: str
    answer: str
    sources: List[Source]
    steps: List[AgentStep]
    total_time: float
    total_tokens: int
    success: bool


# ─── Tool Implementations ───

class WebSearchTool:
    """
    Searches the web using Tavily API.
    Returns structured search results.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # In production: from tavily import TavilyClient
        # self.client = TavilyClient(api_key=api_key)
    
    def search(self, query: str, max_results: int = 5, 
               search_type: str = "general") -> Dict:
        """
        Search the web for a query.
        Returns structured results with sources.
        """
        
        print(f"    🌐 Searching: '{query}'")
        
        # ─── PRODUCTION CODE (uncomment when you have Tavily key) ───
        # try:
        #     if search_type == "news":
        #         results = self.client.search(
        #             query=query,
        #             search_depth="advanced",
        #             topic="news",
        #             max_results=max_results
        #         )
        #     else:
        #         results = self.client.search(
        #             query=query,
        #             search_depth="advanced",
        #             max_results=max_results,
        #             include_answer=True,
        #             include_raw_content=False
        #         )
        #     
        #     sources = []
        #     for r in results.get("results", []):
        #         sources.append({
        #             "title": r.get("title", ""),
        #             "url": r.get("url", ""),
        #             "content": r.get("content", "")[:500],
        #             "score": r.get("score", 0)
        #         })
        #     
        #     return {
        #         "success": True,
        #         "query": query,
        #         "answer": results.get("answer", ""),
        #         "sources": sources
        #     }
        # except Exception as e:
        #     return {"success": False, "error": str(e), "sources": []}
        
        # ─── SIMULATION (for teaching without API key) ───
        return {
            "success": True,
            "query": query,
            "answer": f"Comprehensive information about: {query}",
            "sources": [
                {
                    "title": f"Article 1: {query}",
                    "url": f"https://techcrunch.com/{query.replace(' ', '-')}",
                    "content": f"Detailed information about {query}. Key facts and recent developments discussed comprehensively.",
                    "score": 0.95
                },
                {
                    "title": f"Analysis: {query} in depth",
                    "url": f"https://reuters.com/technology/{query.replace(' ', '-')}",
                    "content": f"Expert analysis of {query}. Multiple perspectives and evidence-based conclusions.",
                    "score": 0.88
                },
                {
                    "title": f"Latest updates on {query}",
                    "url": f"https://theverge.com/{query.replace(' ', '-')}",
                    "content": f"Breaking news and updates about {query}. Latest developments as of 2025.",
                    "score": 0.82
                }
            ]
        }


class CalculatorTool:
    """Safe mathematical calculation tool."""
    
    def calculate(self, expression: str) -> Dict:
        """Evaluate a math expression safely."""
        print(f"    🔢 Calculating: '{expression}'")
        
        import math
        allowed_names = {k: v for k, v in math.__dict__.items() 
                        if not k.startswith("__")}
        allowed_names.update({"abs": abs, "round": round, "int": int, 
                              "float": float, "max": max, "min": min})
        
        try:
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return {"success": True, "result": result, "expression": expression}
        except Exception as e:
            return {"success": False, "error": str(e), "expression": expression}


# ─── The Main Agent ───

class PerplexityAgent:
    """
    The complete Perplexity-like agent.
    
    Features:
    - Intelligent question routing
    - ReACT-based multi-step reasoning
    - Web search with real sources
    - Reflection-based quality improvement
    - Citation generation
    - Streaming output support
    """
    
    def __init__(self):
        self.web_search = WebSearchTool(TAVILY_API_KEY)
        self.calculator = CalculatorTool()
        self.steps: List[AgentStep] = []
        self.sources: List[Source] = []
        self.total_tokens = 0
        
        # Tool definitions for OpenAI function calling
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": """
                    Search the internet for current information.
                    ALWAYS use this for:
                    - Current events, news, recent developments
                    - Real-time data (prices, stats, scores)  
                    - Facts you're uncertain about
                    - Information that changes over time
                    DO NOT use for: basic concepts, math, general knowledge
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Specific search query. Be precise. Example: 'OpenAI GPT-5 capabilities 2025'"
                            },
                            "search_type": {
                                "type": "string",
                                "enum": ["general", "news"],
                                "description": "Use 'news' for recent events, 'general' for other searches",
                                "default": "general"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of results (1-5). Default: 3",
                                "default": 3
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
                    "description": """
                    Perform mathematical calculations.
                    ALWAYS use this for any math — never calculate in your head.
                    Examples: percentages, totals, averages, conversions
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Python math expression. Example: '(1200 * 0.08) + 1200'"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            }
        ]
    
    def _add_step(self, step_type: str, content: str, 
                  tool_used: Optional[str] = None):
        """Record an agent step."""
        step = AgentStep(
            step_type=step_type,
            content=content,
            tool_used=tool_used
        )
        self.steps.append(step)
        return step
    
    def _execute_tool(self, tool_name: str, arguments: Dict) -> str:
        """Execute a tool and return string result."""
        
        if tool_name == "search_web":
            result = self.web_search.search(
                query=arguments.get("query", ""),
                max_results=arguments.get("max_results", 3),
                search_type=arguments.get("search_type", "general")
            )
            
            if result["success"]:
                # Add to sources list
                for s in result.get("sources", []):
                    source = Source(
                        title=s["title"],
                        url=s["url"],
                        snippet=s["content"][:200],
                        relevance_score=s.get("score", 0)
                    )
                    # Avoid duplicate sources
                    if not any(src.url == source.url for src in self.sources):
                        self.sources.append(source)
                
                # Format results for LLM
                formatted = f"Search results for '{arguments.get('query')}':\n\n"
                for i, s in enumerate(result.get("sources", []), 1):
                    formatted += f"[Source {i}] {s['title']}\n"
                    formatted += f"URL: {s['url']}\n"
                    formatted += f"Content: {s['content'][:300]}\n\n"
                
                return formatted
            else:
                return f"Search failed: {result.get('error', 'Unknown error')}"
        
        elif tool_name == "calculate":
            result = self.calculator.calculate(arguments.get("expression", ""))
            if result["success"]:
                return f"Calculation result: {result['expression']} = {result['result']}"
            else:
                return f"Calculation failed: {result.get('error', 'Unknown error')}"
        
        else:
            return f"Unknown tool: {tool_name}"
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        return """
        You are a helpful AI research assistant similar to Perplexity.ai.
        
        Your job is to answer questions accurately using web search.
        
        BEHAVIOR RULES:
        1. ALWAYS search the web before answering — never rely on memory alone
        2. Search multiple times if needed to get complete information
        3. Use specific, precise search queries
        4. If initial results are insufficient, search again with different terms
        5. Calculate any numbers using the calculate tool
        6. After gathering information, write a comprehensive answer
        
        ANSWER FORMAT:
        - Start with a direct answer to the question
        - Use clear headings and bullet points for complex answers
        - Add citation numbers like [1], [2] when using source information
        - End with a "Sources:" section listing the references
        - Be factual and cite sources for every claim
        
        QUALITY STANDARDS:
        - Accuracy over completeness — only state what you found
        - Cite sources for every fact
        - Acknowledge uncertainty when present
        - Keep answers concise but complete
        """
    
    def ask(self, question: str, 
            max_steps: int = 10) -> AgentResponse:
        """
        Main method: Ask the agent a question.
        Returns a complete AgentResponse with answer and sources.
        """
        
        # Reset state
        self.steps = []
        self.sources = []
        self.total_tokens = 0
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"🤖 PERPLEXITY AGENT")
        print(f"Question: {question}")
        print(f"{'='*60}")
        
        # Add initial step
        self._add_step("thought", f"Processing question: {question}")
        
        # Build conversation
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": question}
        ]
        
        step_count = 0
        final_answer = ""
        
        # Main ReACT loop
        while step_count < max_steps:
            step_count += 1
            
            print(f"\n🔄 Step {step_count}/{max_steps}")
            
            # Call LLM
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.1
            )
            
            # Track tokens
            self.total_tokens += response.usage.total_tokens
            
            response_msg = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            
            # Add to messages
            messages.append(response_msg)
            
            # Handle tool calls
            if finish_reason == "tool_calls" and response_msg.tool_calls:
                
                for tool_call in response_msg.tool_calls:
                    
                    tool_name = tool_call.function.name
                    
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except:
                        arguments = {}
                    
                    print(f"   🔧 Using tool: {tool_name}")
                    print(f"   📥 With: {arguments}")
                    
                    # Record the action
                    self._add_step(
                        "action",
                        f"Using {tool_name} with: {json.dumps(arguments)}",
                        tool_used=tool_name
                    )
                    
                    # Execute the tool
                    tool_result = self._execute_tool(tool_name, arguments)
                    
                    print(f"   ✅ Result: {tool_result[:100]}...")
                    
                    # Record observation
                    self._add_step(
                        "observation",
                        tool_result[:500],
                        tool_used=tool_name
                    )
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                
                continue  # Continue the loop
            
            # LLM gave final answer
            elif finish_reason == "stop":
                final_answer = response_msg.content or ""
                
                print(f"\n✅ FINAL ANSWER READY")
                self._add_step("answer", final_answer)
                break
            
            else:
                print(f"⚠️  Unexpected finish: {finish_reason}")
                break
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Build response
        response_obj = AgentResponse(
            question=question,
            answer=final_answer,
            sources=sorted(self.sources, 
                          key=lambda x: x.relevance_score, reverse=True),
            steps=self.steps,
            total_time=total_time,
            total_tokens=self.total_tokens,
            success=bool(final_answer)
        )
        
        print(f"\n📊 AGENT STATS:")
        print(f"   Steps taken: {step_count}")
        print(f"   Sources found: {len(self.sources)}")
        print(f"   Tokens used: {self.total_tokens}")
        print(f"   Time taken: {total_time:.2f}s")
        
        return response_obj
    
    def ask_streaming(self, question: str) -> Generator:
        """
        Streaming version — yields partial updates as agent works.
        Great for real-time UI updates in Streamlit.
        """
        
        # Reset state
        self.steps = []
        self.sources = []
        self.total_tokens = 0
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": question}
        ]
        
        yield {"type": "status", "message": "🔍 Researching your question..."}
        
        step_count = 0
        max_steps = 8
        
        while step_count < max_steps:
            step_count += 1
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            response_msg = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            messages.append(response_msg)
            
            if finish_reason == "tool_calls" and response_msg.tool_calls:
                for tool_call in response_msg.tool_calls:
                    
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except:
                        arguments = {}
                    
                    # Stream status update
                    if tool_name == "search_web":
                        yield {
                            "type": "searching",
                            "message": f"🌐 Searching: '{arguments.get('query', '')}'",
                            "query": arguments.get("query", "")
                        }
                    elif tool_name == "calculate":
                        yield {
                            "type": "calculating",
                            "message": f"🔢 Calculating: {arguments.get('expression', '')}",
                        }
                    
                    # Execute tool
                    tool_result = self._execute_tool(tool_name, arguments)
                    
                    # Yield sources found
                    if tool_name == "search_web":
                        yield {
                            "type": "sources_found",
                            "count": len(self.sources),
                            "sources": [
                                {"title": s.title, "url": s.url}
                                for s in self.sources
                            ]
                        }
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                continue
            
            elif finish_reason == "stop":
                final_answer = response_msg.content or ""
                
                yield {
                    "type": "answer",
                    "answer": final_answer,
                    "sources": [
                        {
                            "title": s.title,
                            "url": s.url,
                            "snippet": s.snippet
                        }
                        for s in self.sources
                    ],
                    "steps": len(self.steps)
                }
                break
```

---

### 8.3 Streamlit UI

```python
# ═══════════════════════════════════════════════════════════
# FILE: app.py
# Streamlit web interface for our Perplexity agent
# ═══════════════════════════════════════════════════════════

import streamlit as st
import time
from agent import PerplexityAgent


# ─── Page Configuration ───
st.set_page_config(
    page_title="Ask the Web — AI Research Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ─── Custom CSS ───
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6c757d;
        text-align: center;
        margin-bottom: 2rem;
    }
    .source-card {
        background: #f8f9fa;
        border-left: 4px solid #0066cc;
        padding: 10px 15px;
        margin: 8px 0;
        border-radius: 4px;
    }
    .source-title {
        font-weight: 600;
        color: #0066cc;
        font-size: 0.9rem;
    }
    .source-url {
        color: #28a745;
        font-size: 0.75rem;
        word-break: break-all;
    }
    .step-card {
        background: #fff3cd;
        border: 1px solid #ffc107;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .metric-card {
        background: #e8f4fd;
        border: 1px solid #b3d9f7;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
    }
    .answer-box {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
        line-height: 1.7;
    }
    .searching-indicator {
        color: #0066cc;
        font-style: italic;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Initialize Agent ───
@st.cache_resource
def get_agent():
    """Create agent once and cache it."""
    return PerplexityAgent()


# ─── Sidebar ───
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    max_steps = st.slider(
        "Max Research Steps",
        min_value=3,
        max_value=15,
        value=8,
        help="More steps = more thorough research, but slower and more expensive"
    )
    
    show_steps = st.checkbox(
        "Show reasoning steps",
        value=True,
        help="See how the agent thinks through the problem"
    )
    
    show_sources = st.checkbox(
        "Show all sources",
        value=True,
        help="Display all web sources found"
    )
    
    st.markdown("---")
    
    st.markdown("## 📚 Example Questions")
    
    example_questions = [
        "What are the latest AI breakthroughs in 2025?",
        "Compare GPT-4 vs Claude 3.5 capabilities",
        "What is the current price of Nvidia stock?",
        "Explain quantum computing for beginners",
        "What programming language should I learn in 2025?"
    ]
    
    for eq in example_questions:
        if st.button(f"💬 {eq[:40]}...", use_container_width=True):
            st.session_state.selected_question = eq
    
    st.markdown("---")
    
    st.markdown("## ℹ️ About")
    st.markdown("""
    This agent uses:
    - 🧠 GPT-4o reasoning
    - 🌐 Web search (Tavily)
    - 🔄 ReACT framework
    - 📊 Citation tracking
    """)


# ─── Main UI ───

# Header
st.markdown('<h1 class="main-header">🔍 Ask the Web</h1>', 
            unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-powered research agent • '
            'Like Perplexity, built from scratch</p>', 
            unsafe_allow_html=True)

# ─── Search Input ───
col1, col2 = st.columns([4, 1])

with col1:
    # Use selected example question if one was clicked
    default_q = st.session_state.get("selected_question", "")
    question = st.text_input(
        "Ask anything...",
        value=default_q,
        placeholder="What are the latest developments in AI agents?",
        label_visibility="collapsed"
    )

with col2:
    search_button = st.button(
        "🔍 Search",
        type="primary",
        use_container_width=True
    )

# Clear selected question after using it
if "selected_question" in st.session_state:
    del st.session_state.selected_question


# ─── Process Question ───

if search_button and question:
    
    agent = get_agent()
    
    # Create columns for layout
    col_main, col_sources = st.columns([3, 1])
    
    with col_main:
        
        # Status area
        status_placeholder = st.empty()
        steps_placeholder = st.empty()
        answer_placeholder = st.empty()
    
    with col_sources:
        sources_placeholder = st.empty()
    
    # Start time
    start_time = time.time()
    
    # Tracking variables
    search_queries = []
    all_sources = []
    step_messages = []
    
    # ─── Stream the agent's work ───
    
    with st.spinner(""):
        for update in agent.ask_streaming(question):
            
            update_type = update.get("type")
            
            if update_type == "status":
                status_placeholder.info(update["message"])
            
            elif update_type == "searching":
                query = update.get("query", "")
                search_queries.append(query)
                step_messages.append(f"🌐 Searching: *{query}*")
                
                # Update steps display
                if show_steps:
                    with steps_placeholder.container():
                        st.markdown("**🔄 Research Steps:**")
                        for msg in step_messages:
                            st.markdown(
                                f'<div class="searching-indicator">{msg}</div>',
                                unsafe_allow_html=True
                            )
            
            elif update_type == "calculating":
                step_messages.append(f"🔢 Calculating: *{update.get('message', '')}*")
            
            elif update_type == "sources_found":
                sources = update.get("sources", [])
                
                # Update sources panel
                if show_sources and sources:
                    with sources_placeholder.container():
                        st.markdown(f"**📚 Sources Found ({len(sources)})**")
                        for source in sources:
                            st.markdown(
                                f"""
                                <div class="source-card">
                                    <div class="source-title">
                                        {source['title'][:60]}...
                                    </div>
                                    <div class="source-url">
                                        {source['url'][:50]}...
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
            
            elif update_type == "answer":
                
                answer = update.get("answer", "")
                sources = update.get("sources", [])
                total_time = time.time() - start_time
                
                # Clear status
                status_placeholder.empty()
                
                # Clear step messages (or keep if show_steps)
                if not show_steps:
                    steps_placeholder.empty()
                
                # Display final answer
                with answer_placeholder.container():
                    
                    # Metrics row
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("⏱️ Time", f"{total_time:.1f}s")
                    with m2:
                        st.metric("🔍 Searches", len(search_queries))
                    with m3:
                        st.metric("📚 Sources", len(sources))
                    with m4:
                        st.metric("🔄 Steps", update.get("steps", 0))
                    
                    st.markdown("---")
                    
                    # Answer
                    st.markdown("### 📝 Answer")
                    st.markdown(
                        f'<div class="answer-box">{answer}</div>',
                        unsafe_allow_html=True
                    )
                
                # Update sources panel with full details
                if show_sources and sources:
                    with sources_placeholder.container():
                        st.markdown(f"**📚 Sources ({len(sources)})**")
                        
                        for i, source in enumerate(sources[:5], 1):
                            with st.expander(f"[{i}] {source['title'][:40]}..."):
                                st.markdown(f"🔗 [{source['url']}]({source['url']})")
                                st.markdown(source.get('snippet', '')[:300])


elif search_button and not question:
    st.warning("Please enter a question!")


# ─── Welcome State (no question yet) ───

if not search_button:
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🌐 Web-Connected
        Searches the live internet for current, 
        accurate information — not training data.
        """)
    
    with col2:
        st.markdown("""
        ### 🧠 Thinks Step-by-Step
        Uses ReACT framework to reason before 
        acting, making smarter decisions.
        """)
    
    with col3:
        st.markdown("""
        ### 📚 Always Cited
        Every fact comes with a source URL 
        so you can verify everything.
        """)
    
    # Recent example queries
    st.markdown("### 💡 Try These Questions:")
    
    cols = st.columns(2)
    demo_questions = [
        "What is the current state of GPT-5?",
        "How does the ReACT framework work?",
        "Best Python libraries for AI in 2025",
        "Latest news about AI regulation in Europe"
    ]
    
    for i, dq in enumerate(demo_questions):
        with cols[i % 2]:
            st.info(f"💬 {dq}")


# ─── Footer ───
st.markdown("---")
st.markdown(
    "<center><small>Built with 🔥 | GPT-4o + Tavily + Streamlit | "
    "Perplexity-like AI Agent from scratch</small></center>",
    unsafe_allow_html=True
)
```

---

### 8.4 Project Setup and Run Instructions

```python
# ═══════════════════════════════════════════════════════════
# FILE: requirements.txt
# ═══════════════════════════════════════════════════════════

# Core AI
openai>=1.30.0
anthropic>=0.25.0  # Optional: for Claude support

# Web Search
tavily-python>=0.3.0

# Web UI
streamlit>=1.35.0

# Utilities
python-dotenv>=1.0.0
asyncio
pytz>=2024.1
pydantic>=2.0.0

# Evaluation
ragas>=0.1.0  # Optional: for formal evaluation
```

```bash
# ═══════════════════════════════════════════════════════════
# FILE: .env
# Store your API keys here (never commit this to GitHub!)
# ═══════════════════════════════════════════════════════════

OPENAI_API_KEY=sk-your-openai-key-here
TAVILY_API_KEY=tvly-your-tavily-key-here
```

```python
# ═══════════════════════════════════════════════════════════
# FILE: setup.py
# Run this to set up and test your project
# ═══════════════════════════════════════════════════════════

import subprocess
import sys
import os


def check_requirements():
    """Check all requirements are installed."""
    print("📦 Checking requirements...")
    try:
        import openai
        import streamlit
        print("✅ Core packages installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Run: pip install -r requirements.txt")
        return False
    return True


def check_api_keys():
    """Check API keys are configured."""
    print("\n🔑 Checking API keys...")
    
    openai_key = os.getenv("OPENAI_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    
    if not openai_key or openai_key == "your-key-here":
        print("❌ OPENAI_API_KEY not set!")
        print("   Get it from: https://platform.openai.com/api-keys")
        return False
    else:
        print(f"✅ OpenAI key: {openai_key[:8]}...")
    
    if not tavily_key or tavily_key == "your-key-here":
        print("⚠️  TAVILY_API_KEY not set (web search will be simulated)")
        print("   Get it from: https://tavily.com (free tier available)")
    else:
        print(f"✅ Tavily key: {tavily_key[:8]}...")
    
    return True


def run_quick_test():
    """Run a quick test of the agent."""
    print("\n🧪 Running quick test...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    from agent import PerplexityAgent
    
    agent = PerplexityAgent()
    response = agent.ask("What is artificial intelligence?")
    
    if response.success:
        print(f"✅ Agent test passed!")
        print(f"   Answer preview: {response.answer[:100]}...")
        print(f"   Sources found: {len(response.sources)}")
        print(f"   Time taken: {response.total_time:.2f}s")
    else:
        print("❌ Agent test failed!")
    
    return response.success


def run_app():
    """Launch the Streamlit app."""
    print("\n🚀 Launching Streamlit app...")
    print("   Open in browser: http://localhost:8501")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])


if __name__ == "__main__":
    print("🔧 ASK-THE-WEB AGENT SETUP")
    print("="*50)
    
    if not check_requirements():
        sys.exit(1)
    
    if not check_api_keys():
        sys.exit(1)
    
    print("\n✅ All checks passed!")
    
    # Run test
    test_passed = run_quick_test()
    
    if test_passed:
        print("\n" + "="*50)
        print("🎉 PROJECT READY!")
        print("="*50)
        print("\nTo start the app, run:")
        print("   streamlit run app.py")
        print("\nOr run setup.py again with --run flag")
    else:
        print("\n⚠️  Test failed — check your API keys")
```

---

### 8.5 Project File Structure

```
ask-the-web-agent/
│
├── 📄 agent.py              ← Main agent logic (ReACT + tools)
├── 📄 app.py                ← Streamlit web interface
├── 📄 setup.py              ← Setup and test script
│
├── 📄 requirements.txt      ← Python dependencies
├── 📄 .env                  ← API keys (DO NOT commit!)
├── 📄 .gitignore            ← Excludes .env and secrets
│
├── 📁 tools/
│   ├── 📄 search.py         ← Tavily web search tool
│   ├── 📄 calculator.py     ← Math calculation tool
│   └── 📄 __init__.py
│
├── 📁 evaluation/
│   ├── 📄 evaluator.py      ← Agent evaluation system
│   ├── 📄 test_cases.json   ← Test questions + reference answers
│   └── 📄 run_eval.py       ← Run full evaluation suite
│
├── 📁 agents/
│   ├── 📄 react_agent.py    ← ReACT implementation
│   ├── 📄 reflexion.py      ← Reflexion implementation
│   └── 📄 rewoo.py          ← ReWOO implementation
│
└── 📄 README.md             ← Project documentation
```

---

### 8.6 README Template (For Portfolio)

```markdown
# 🔍 Ask-the-Web Agent

> An AI research agent like Perplexity.ai, built from scratch
> using GPT-4o, Tavily search, and the ReACT framework.

## 🎯 What It Does

Ask any question → Agent searches the web → Gives you a 
cited, accurate answer in seconds.

## 🏗️ Architecture

- **LLM**: GPT-4o for reasoning and answer generation
- **Framework**: ReACT (Reasoning + Acting) for multi-step research
- **Search**: Tavily API for real-time web search
- **UI**: Streamlit for interactive web interface
- **Patterns**: Tool calling, prompt chaining, reflection

## 🚀 Quick Start

```bash
git clone https://github.com/you/ask-the-web-agent
cd ask-the-web-agent
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
streamlit run app.py
```

## 🔧 Key Features

- ✅ Real-time web search with Tavily API
- ✅ Multi-step ReACT reasoning
- ✅ Automatic citation generation  
- ✅ Streaming responses in UI
- ✅ Source verification display
- ✅ Tool calling (search + calculation)

## 📊 Technical Details

| Component | Technology |
|-----------|-----------|
| LLM | GPT-4o |
| Agent Framework | ReACT (custom) |
| Web Search | Tavily API |
| UI | Streamlit |
| Agent Patterns | Tool calling, routing, reflection |

## 🎓 Concepts Demonstrated

- AI Agents vs LLMs
- ReACT framework implementation
- Tool calling with OpenAI function calling
- Multi-step reasoning chains
- Agent evaluation metrics
- MCP protocol concepts

## 📸 Demo

[Add screenshots or demo GIF here]
```

---

# 🎓 COMPLETE TOPIC SUMMARY

---

## Everything We Covered (Full Curriculum Map):

```
PART 1:
━━━━━━━
✅ What We're Building (Perplexity Clone)

✅ Agents Overview
   ├── What is an Agent? (perceive → think → decide → act → observe)
   ├── LLMs vs Agents vs Agentic Systems
   └── Agency Levels 0-5

✅ Workflows
   ├── Prompt Chaining (sequential steps, output feeds next step)
   ├── Routing (classify input → send to right handler)
   ├── Parallelization
   │   ├── Sectioning (divide task, run parallel, combine)
   │   └── Voting (multiple perspectives, synthesize)
   ├── Reflection (generate → critique → improve → loop)
   └── Orchestrator-Worker (manager → assigns → specialists → combine)

✅ Tools
   ├── Tool Calling (LLM requests, code executes)
   ├── Tool Formatting (JSON schema for LLM)
   ├── Tool Execution (the complete loop)
   └── MCP (universal tool protocol standard)

PART 2:
━━━━━━━
✅ Multi-Step Agents
   ├── Planning Autonomy (reactive → fixed → dynamic)
   ├── ReACT (Thought → Action → Observation → loop)
   ├── Reflexion (ReACT + memory of past mistakes)
   ├── ReWOO (Plan once → Execute all → Solve once)
   └── Tree of Thoughts (explore multiple paths, pick best)

✅ Multi-Agent Systems
   ├── Challenges (communication, conflicts, errors, loops, cost, safety)
   ├── Use Cases (research, coding, finance, customer service)
   └── A2A Protocol (Agent Cards, Tasks, Artifacts, JSON-RPC)

✅ Agent Evaluation
   ├── Why it's hard (multiple steps, variable paths, no single answer)
   ├── What to evaluate (quality, efficiency, tools, reasoning, safety)
   ├── Evaluation methods (human, LLM judge, reference-based, trajectory)
   └── Complete evaluation system with code

✅ Complete Project Build
   ├── Full architecture diagram
   ├── Complete agent.py with ReACT + tool calling
   ├── Streaming support
   ├── Streamlit UI (app.py)
   ├── Project setup and file structure
   └── Portfolio README template
```

---

## 🗺️ Interview Questions Master List:

---

### On Agents:

```
Q1: "What's the difference between an LLM and an AI agent?"
A: An LLM is a text in/text out model — it responds once and stops.
   An agent adds tools, memory, and the ability to loop — it can
   perceive, think, act, observe results, and repeat until a goal
   is achieved. An agent is an LLM plus capability to take actions.

Q2: "What is the ReACT framework?"
A: ReACT stands for Reasoning and Acting. Instead of directly
   answering, the agent writes out its Thought (why it's doing
   something), takes an Action (uses a tool), and observes the
   Observation (result). This loop repeats until it has a Final
   Answer. The key benefit is explicit reasoning before acting,
   which improves accuracy and makes the agent's behavior
   interpretable and debuggable.

Q3: "When would you use Reflexion vs ReWOO?"
A: Use Reflexion when accuracy is critical and you can afford
   multiple attempts — it learns from failures across trials.
   Use ReWOO when speed and cost matter — it plans all steps
   upfront and uses only 2 LLM calls regardless of complexity.
   ReWOO is better when the task structure is predictable;
   Reflexion is better for complex tasks where first attempts
   often fail.

Q4: "What are the challenges of multi-agent systems?"
A: Six key challenges:
   1. Communication overhead (agents waste time talking)
   2. Coordination conflicts (agents disagree or duplicate work)
   3. Error propagation (early mistakes cascade)
   4. Infinite loops (circular dependencies, deadlocks)
   5. Cost explosion (many agents = many API calls)
   6. Trust and safety (who authorizes which actions?)

Q5: "How do you evaluate an AI agent?"
A: Evaluation has multiple dimensions:
   - Task completion rate (did it finish?)
   - Answer quality (accuracy, completeness, clarity)
   - Efficiency (steps, tokens, time, cost)
   - Tool usage accuracy (right tools, right time)
   - Safety (hallucination rate, harmful content)
   Common methods: LLM-as-judge for scalable evaluation,
   trajectory evaluation for process quality, human evaluation
   for final validation.
```

---

## 🏆 Final Engineer Mindset Checklist:

```
Before building an agent, ask yourself:

□ Do I actually need an agent, or will a simple LLM call work?
□ What is the minimum agency level needed?
□ Which framework fits: ReACT, ReWOO, Reflexion, or ToT?
□ What tools does this agent need?
□ How will I handle tool failures and errors?
□ How will I prevent infinite loops?
□ What is the cost per user question?
□ How will I evaluate agent quality?
□ Where does human oversight fit in?
□ What are the safety risks of this agent's tools?
□ How will I monitor the agent in production?
□ What happens when the agent makes a mistake?
```

---

## 🚀 How to Run Your Project:

```bash
# Step 1: Clone or create project folder
mkdir ask-the-web-agent
cd ask-the-web-agent

# Step 2: Install dependencies
pip install openai tavily-python streamlit python-dotenv pytz

# Step 3: Set up API keys in .env file
echo "OPENAI_API_KEY=your-key" > .env
echo "TAVILY_API_KEY=your-key" >> .env

# Step 4: Copy the code
# Save agent.py with the agent code
# Save app.py with the streamlit code

# Step 5: Run the app!
streamlit run app.py

# Step 6: Open browser at http://localhost:8501
# Ask any question and watch the agent work! 🎉
```

---