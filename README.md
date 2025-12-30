#  AI Architect Studio

**From Abstract Idea to Enterprise-Grade Specification — Autonomously.**\
**Live Demo:** [https://aiarchitect.streamlit.app/](https://aiarchitect.streamlit.app/)

AI Architect Studio is an **autonomous software architecture design system** that acts as your **virtual Architect**.  
It transforms vague ideas into **production-grade architecture artifacts** using a rigorously structured, multi-agent workflow.

Unlike standard chatbots that generate unverified text, AI Architect Studio **researches, critiques, validates, and iterates** on architecture decisions until they meet enterprise-quality standards.

---

## What Does It Do?

From a single prompt like:

> *“Build a scalable ride-sharing platform”*

AI Architect Studio generates:

- ✅ **22-point High-Level Design (HLD)**
- ✅ **Low-Level Design (LLD)** with APIs, schemas, and components
- ✅ **Self-healing Architecture Diagrams** (Mermaid.js)
- ✅ **Ready-to-run Code Scaffolding**
- ✅ **Docker + project structure**
- ✅ **Security & compliance review**

All done **autonomously** using a graph-based multi-agent system.

---

## Why AI Architect Studio?

Designing software is *cognitive heavy-lifting*:

- Scalability vs cost
- Security vs usability
- Compliance vs speed
- Data models vs APIs

Most AI tools fail because they lack **structure, validation, and feedback loops**.

AI Architect Studio solves this with **three core innovations**.

---

## Core Solutions

###  The “Judge” Loop (Adversarial Review)

A dedicated **Judge Agent** critiques every design artifact.

- Detects security gaps
- Flags architectural inconsistencies
- Rejects weak designs
- Forces regeneration until quality passes

> No silent hallucinations. Everything is reviewed.

---

###  Strict Schema Enforcement (Zero Fluff)

All agent outputs are validated using **Pydantic schemas**:

- APIs → valid JSON
- DB schemas → structured tables
- Components → typed contracts

This guarantees **machine-usable outputs**, not chatty prose.

---

###  Self-Healing Diagrams

Architecture diagrams are generated using **Mermaid.js**.

If a diagram fails to render:
- A **Fixer Agent** detects the error
- Captures Mermaid syntax issues
- Regenerates until it renders correctly

> Diagrams that *actually render*, every time.

---

## 🧠 The Agent Team

Agents collaborate using a **directed cyclic graph** (LangGraph).

| Agent | Role | Responsibility |
|-----|-----|---------------|
| Engineering Manager | Strategy | Drafts the High-Level Design (HLD) |
| Security Specialist | Compliance | Zero Trust, IAM, SOC2, GDPR |
| Team Lead | Implementation | Converts HLD → LLD |
| The Judge | Quality Control | Rejects flawed designs |
| Visual Architect | Diagrams | Mermaid architecture diagrams |
| Scaffolder | DevOps | Codebase & Docker generation |

---

## ✨ Key Features

###  RAG Knowledge Base
Upload your **company standards** (PDF/TXT):

- Engineering guidelines
- Security rules
- Architecture playbooks

Agents will **comply with your internal rules**.

---

### 💰 Cost & Token Transparency

Real-time tracking for:
- OpenAI (GPT-4o)
- Google Gemini
- Anthropic Claude

See **token usage & cost estimates** live.

---

###  Brainstorming Mode

A lightweight chat interface to:
- Clarify requirements
- Explore ideas
- Refine scope

Before triggering full architecture generation.

---

###  Project Snapshots

- Save architecture states
- Resume later
- Load or delete past designs

All stored locally.

---

## Installation & Setup

### Prerequisites
- Python **3.11+**
- At least one LLM API key:
  - OpenAI
  - Google Gemini
  - Anthropic

---

###  Clone the Repository

```bash
git clone https://github.com/yourusername/ai-architect-studio.git
cd ai-architect-studio
```

---

###  Install Dependencies

Using **pip**:
```bash
pip install .
```

Using **uv** (recommended):
```bash
uv sync
```

---

###  Configure Environment

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
```

(You can also enter keys directly in the UI.)

---

###  Run the Application

```bash
streamlit run app.py
```

---

## 📸 Usage Workflow

###  Define Requirements
- Use **Chat Assistant**
- Upload PDFs or type rough ideas
- Refine into a clear specification using brainstorming mode

---

###  Generate Architecture
- Open **Architect Studio**
- Click **Generate Architecture**
- Watch agents collaborate in real time
- Judge agent approves or rejects

---

###  Review Artifacts

- **HLD Tab** → 22-point strategic design
- **LLD Tab** → APIs, schemas, logic
- **Diagrams Tab** → Auto-generated visuals

---

###  Export Code

Click **Generate Code** to download:
- Project skeleton
- `requirements.txt`
- `docker-compose.yml`

---

## ❓ FAQ

### Is this just a ChatGPT wrapper?
**No.**  
This is a **graph-based autonomous system** where agents exchange **structured data objects**, not free text.

Includes:
- Validation loops
- Adversarial review
- Automated retries
- Diagram verification

---

### Can I use my own documentation?
Yes.  
Upload PDFs or TXT files in **Knowledge Studio**.  
Agents will reference them during design.

---

### How much does a run cost?

Typical full run (HLD + LLD + Diagrams):

| Model | Approx Cost |
|----|----|
| Gemini Flash | ~$0.01 |
| GPT-4o | ~$0.10 – $0.50 |
| Claude 3.5 | ~$0.50 – $1.00|

Costs shown live in the UI.

---

### Diagrams aren’t rendering. What now?
The **Self-Healing Diagram Loop** retries automatically.

If it persists:
- Click **Regenerate Diagrams**
- Visual Architect will retry from scratch

---

## Roadmap

- [ ] VS Code Extension
- [ ] Terraform / IaC Export
- [ ] Jira Ticket Generation
- [ ] Cloud Deployment Mode

---

## Built With

- LangChain
- LangGraph
- Streamlit
- Pydantic
- Mermaid.js

---

**AI Architect Studio — design software like a CTO, not a chatbot.**
