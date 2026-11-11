# CodeGuardian AI

> AI-Powered Autonomous Code Intelligence Platform

**Analyze • Predict • Explain • Repair • Verify**

---

## 🚀 Vision

CodeGuardian AI is an AI-powered software engineering platform designed to understand entire software repositories before attempting to predict, explain, repair, and verify code issues.

Unlike traditional AI coding assistants that primarily generate code from prompts, CodeGuardian AI is being built around **repository-level program understanding**.

The platform combines compiler-inspired static analysis, program graphs, data-flow analysis, machine learning, explainable AI, and autonomous agents to create a complete software-analysis and repair pipeline.

The long-term goal is:

```text
Repository
    ↓
Program Understanding
    ↓
Risk Prediction
    ↓
Explainable Analysis
    ↓
AI Patch Generation
    ↓
Sandbox Validation
    ↓
Verified Repair
```

---

## 🔄 How It Works

1. **Submit a repository.** The user provides a repository URL.
2. **Analyze the whole repo.** Static analysis and program-graph features are extracted for every file and function.
3. **Predict risk.** Static risk and GNN-based risk are combined into a final risk percentage per file and function.
4. **Explain.** An explainer agent shows which part of the code is risky and why.
5. **Repair on request.** A correction agent generates a patch for the selected issue.
6. **Verify in a sandbox.** The patch runs inside an isolated Docker sandbox. If it fails, the system fixes it again.
7. **Return the verified fix.** Only the validated, corrected code is returned to the user.

---

## ✅ Current Status

| Component | Status |
|---|---|
| Repository analysis, static + graph (GNN) risk scoring | Implemented (under active improvement) |
| Custom synthetic security dataset (`custom_security` schema) | Implemented, being expanded |
| Explainer agent | Implemented |
| AI reviewer | Implemented |
| Correction agent + `/correction/fix-verified` endpoint | Implemented |
| Docker sandbox validation (`code-guardian-sandbox` image) | Implemented |
| AI provider fallback: Gemini → Groq → DeepSeek | Implemented |
| React frontend: AI Corrections, Patch Verification, Patch History | Implemented |
| Per-repository sandbox image built from the repo's own dependencies | In progress |
| Public deployment for multi-user access | Planned |

---

## ✨ Key Features

- **Repository-level understanding** instead of single-file or prompt-only analysis
- **Hybrid risk prediction** combining static analysis with a graph neural network
- **Explainable results** that point to the risky code and give the reason
- **AI patch generation** through a dedicated correction agent
- **Sandbox-verified repairs** so a fix is returned only after it has been executed and checked
- **Resilient AI layer** that falls back across Gemini, Groq and DeepSeek if a provider fails
- **Enterprise-style dashboard** with reusable React components

---

## 🧱 Architecture

```text
frontend/        React + Vite dashboard (AI Corrections, Patch Verification, Patch History)
backend/         Python backend: analysis, risk scoring, agents, correction API
  └── services/ai/   AI provider fallback (Gemini → Groq → DeepSeek)
docker/          Dockerfile.sandbox for the code-guardian-sandbox:latest image
```

---

## 🛠️ Tech Stack

- **Backend:** Python
- **Frontend:** React, Vite
- **ML / Analysis:** static analysis, program graphs, GNN, data-flow-inspired features
- **AI Agents:** explainer agent, AI reviewer, correction agent
- **LLM Providers:** Gemini, Groq, DeepSeek (with automatic fallback)
- **Sandbox:** Docker

---

## ⚙️ Getting Started

### Prerequisites

- Python 3.13
- Node.js (for the frontend)
- Docker (must be running, since the sandbox depends on it)
- API keys for the LLM providers you want to use

### Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Build the sandbox image
docker build -t code-guardian-sandbox:latest -f docker/Dockerfile.sandbox .

# 4. Configure environment variables (API keys) in your .env file

# 5. Start the backend (use your project's run command)

# 6. Start the frontend
cd frontend
npm install
npm run dev
```

---

## 🗺️ Roadmap

- [x] Risk prediction with explanations
- [x] AI patch generation with Docker sandbox verification
- [x] Multi-provider AI fallback
- [x] Dashboard pages for corrections, verification and patch history
- [ ] Automatic sandbox image built from each analyzed repository's dependencies
- [ ] Larger and more realistic training data for the risk model
- [ ] Deployment so other users can analyze their own repositories

---

## ⚠️ Notes

- The risk model is trained on a custom synthetic dataset, so scores should be treated as guidance, not a guarantee.
- Generated patches are only returned after passing sandbox validation, but they should still be reviewed before merging.

---

## 📄 License

Add your license here.