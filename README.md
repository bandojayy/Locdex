# Locdex: Local-First AI Coding Agent

Locdex is an enterprise-grade, local-first autonomous AI coding agent. It specializes in secure code generation, intelligent workspace context gathering, and automated GitHub Pull Request workflows. 

Designed with a strict "Defense-in-Depth" architecture, Locdex safely evaluates AI-generated code in an air-gapped environment before it ever touches your production repository.

## ✨ Features

* **Dynamic Model Routing:** Defaults to local Ollama models for absolute privacy and zero-latency generation. Fast-fails to a resilient OpenRouter cloud chain if local models are unavailable.
* **Auto-Healing Sandbox:** Validates generated code using a robust AST linter and executes tests inside an ephemeral Docker container. Feeds errors back to the LLM for automatic correction (up to 3 attempts).
* **Shift-Left Security:** Blocks path traversal, repository hijacking (`.git/`), command injection, and dynamic execution bypasses in-memory before disk I/O.
* **Cost & Context Optimization:** Extracts repository AST skeletons to maintain high context awareness without burning API tokens. Tracks token budgets automatically.
* **Git Automation:** Seamlessly branches, commits, and opens GitHub Pull Requests with a single `ship it` command.

## 🚀 Prerequisites

To run Locdex securely, you must have the following installed:
1. **Python 3.10+**
2. **Docker Desktop** (Required for the air-gapped execution sandbox)
3. **Git**
4. *(Optional but recommended)* **Ollama** with a coding model installed (e.g., `qwen2.5-coder`).

## 🛠️ Installation

Clone the repository and install it globally as an editable Python package:

```bash
git clone [https://github.com/giddy-0x/Locdex.git](https://github.com/giddy-0x/Locdex.git)
cd Locdex
pip install -e .