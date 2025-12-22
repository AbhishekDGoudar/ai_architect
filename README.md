# AI Architect Studio

Welcome to AI Architect Studio. This project is an autonomous design system that converts simple requirements into enterprise grade architecture documents. We bridge the gap between abstract ideas and concrete implementation plans using a team of AI agents.

**Live Demo:** [https://your-project-link-here.com](https://your-project-link-here.com)

## What It Does
Building software architecture is complex. You need to think about business goals, data models, security compliance, and operational readiness all at once. This tool handles that cognitive load for you.

You provide a simple prompt, like "Build a ride sharing app," and our system orchestrates a team of specialized AI agents to generate a comprehensive 22 point design document.

## The Agent Team
We use a multi agent workflow to ensure quality and depth.

* **Engineering Manager**: Drafts the High Level Design (HLD) and creates structural diagrams.
* **Security Specialist**: Intervenes to harden authentication, authorization, and compliance strategies.
* **Team Lead**: Translates the high level strategy into a Low Level Design (LLD), focusing on APIs and schemas.
* **Architecture Judge**: The quality control layer. This agent reviews the work of others, verifies diagram syntax, and rejects the design if it fails to meet standards.

## Tech Stack
We prioritized tools that offer reliability and type safety.

* **LangGraph**: For orchestrating the stateful, cyclic workflow between agents.
* **Streamlit**: For the interactive frontend and visualization.
* **Pydantic**: For strict schema validation, ensuring our AI outputs structured data rather than free text.
* **Mermaid.js**: For rendering dynamic architecture diagrams as code.
* **LLM Backend**: Configurable support for Gemini, OpenAI, and Claude.

## How to Run Locally
You can get this system running on your own machine in just a few minutes.

**1. Clone and Setup**
First, clone the repository to your local machine and navigate into the folder.

**2. Install Dependencies**
Ensure you have Python 3.11 or higher installed. We recommend using `uv` for lightning fast installations, but standard `pip` works perfectly as well.

* Using pip:
`pip install .`

* Using uv:
`uv sync`

**3. Configure Environment**
You need to set up your environment variables to allow the agents to talk to the LLMs. Create a file named `.env` in the root directory and add your API keys.

`OPENAI_API_KEY=sk-...`
`GOOGLE_API_KEY=AIza...`

**4. Launch the App**
Start the application interface with a single command.

`streamlit run app.py`

## Accomplishments
* **LLM as Judge Evaluation**: We implemented a rigorous strict critic agent (The Judge) that evaluates every design against architectural principles. It is not just a rubber stamp; it forces the other agents to retry and fix their mistakes if the logic or diagrams are flawed.
* **Self Healing Workflows**: If the Judge agent detects a broken diagram or a missing security requirement, it sends the work back to the Manager with specific feedback for correction.
* **Structured Output**: Unlike chat interfaces that give you walls of text, our system outputs strictly typed JSON objects that map to real world architectural artifacts.

## Phase 2 and Roadmap
We are actively working on expanding the capabilities of the studio. Here are the things we intend to do next:

* **Automated Code Generation**: Moving beyond design documents to generating the actual boilerplate code for the services defined in the LLD.
* **Infrastructure as Code**: Automatically generating Terraform or Pulumi scripts to deploy the architecture to AWS or Google Cloud.
* **IDE Integration**: Building a VS Code extension so developers can generate designs directly within their editor.
* **Jira Export**: Converting the implementation plan into actionable tickets in your project management tool.

## Frequently Asked Questions

**How much does a run cost?**
The cost depends on the model provider you choose. A full run typically consumes about 10k tokens due to the depth of the 22 point framework. We provide a cost estimator in the UI before you run.

**Can I save my designs?**
Yes. The application includes a snapshot system that allows you to save, load, and delete architecture runs locally.

**Why did you choose Pydantic over standard JSON?**
Pydantic allows us to enforce architectural standards at the code level. If an agent tries to skip a required field like "Disaster Recovery," the validation layer catches it before it even reaches the user.

**Is the code production ready?**
The LLD provides a solid blueprint, including API specs and database schemas. While it is not copy paste executable code yet (see Phase 2), it provides the exact specifications a senior engineer would need to start coding immediately.