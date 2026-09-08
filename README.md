# Locdex 🧠🛡️

> **A local-first, autonomous AI coding agent with a fail-closed security sandbox.**

Locdex is an intelligent coding assistant that lives in your terminal. It leverages local LLMs (via Ollama) to generate code and dynamically falls back to top-tier cloud models (DeepSeek, Qwen, Llama) when needed. 

What makes Locdex different? **It is architected for security and economics.** It parses your workspace into a lightweight AST skeleton, sandboxes generated code to prevent malicious execution, auto-heals its own errors, and calculates exactly how much money you save by running locally.

## ✨ Features

- **AST Security Linter:** Statically analyzes generated code to block arbitrary code execution (`import os`, `eval()`) before it can ever touch your host machine.
- **Auto-Healing Loop:** If a test or syntax check fails, Locdex captures the `stderr` traceback and autonomously instructs the LLM to fix the bug (up to 3 retries).
- **Intelligent Cloud Fallback:** Gracefully handles `429 Rate Limit` and `404` errors by seamlessly cycling through a failover chain of top OpenRouter models (DeepSeek-R1, Qwen 2.5 Coder, Llama 3.3).
- **Cost & Budget Planner:** Intercepts generations to calculate token usage and reports exact API cost savings locally.
- **Dynamic Git & PR Automation:** Automatically extracts your `remote.origin.url`, cuts a branch, commits passing code, and opens a GitHub Pull Request.

## 🚀 Installation

Locdex requires Python 3.10+ and Git.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/giddy-0x/Locdex.git](https://github.com/giddy-0x/Locdex.git)
   cd Locdex