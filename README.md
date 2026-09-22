# AI Career Interview Assistant

A Streamlit course project integrating resume analysis, retrieval-assisted interview preparation, mock interviews, job matching, and natural-language access to career statistics.

## Overview

Built for the AI application development practical course at Zhongnan University of Economics and Law. The engineering objective is to connect common graduate job-preparation tasks in one usable application, including an offline fallback. This is an application prototype, not a new foundation model or a validated hiring assessment system.

## Objectives

- Connect resume parsing, interview preparation, feedback, and learning suggestions.
- Show retrieved reference material alongside interview answers.
- Query a small, source-labelled career statistics database through natural language.
- Keep core demonstrations usable when cloud model credentials are unavailable.

## Method

- Streamlit interface with Plotly charts and session-based workflows.
- Text, PDF and Word resume parsing; keyword-based profiles with optional model assistance.
- ChromaDB retrieval, provider embeddings when configured, and local fallback retrieval.
- DashScope or Volcengine model calls, with explicit offline notices.
- Mock interview questions and heuristic scoring; optional model-assisted feedback.
- Rule/template-based natural-language-to-SQL routing over SQLite. This is not unrestricted LLM-generated SQL.
- Skill overlap for job matching and industry wage references for illustrative salary ranges.

The implementation contribution is workflow integration, fallback handling, presentation, and regression tests. No novel learning algorithm or state-of-the-art claim is made.

## Data

See [data/README.md](data/README.md). Database seeds live in `career_assistant/database.py`; databases and vector indexes are generated locally and are not committed. No personal resumes, raw recruitment datasets, or third-party model weights are included. There is no model training or train/validation/test split in this project.

## Repository Structure

```text
app.py                    Streamlit entry point
career_assistant/         Resume, interview, RAG, model, SQL and UI modules
data/interview_bank.md    Adapted interview preparation material
data/README.md            Sources and data limitations
tests/                    Unit and Streamlit AppTest checks
docs/usage-zh.md           Chinese usage guide from the course project
docs/release-audit.md      Packaging, verification and publication notes
requirements.txt          Direct project dependencies
.env.example              Placeholder configuration reference
```

## Installation

From the repository root, using Python 3.10 or later (local interpreter inspected: 3.10.11):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux/macOS activate with `source .venv/bin/activate`. A fresh isolated dependency installation has not yet been verified. No CUDA or PyTorch training setup is required.

## Reproduction

```powershell
python -m streamlit run app.py
python -m pytest tests -q
```

Open the URL printed by Streamlit (normally http://localhost:8501). Startup initializes the SQLite data and retrieval index. Use the sample resume, query the question bank, complete a mock interview, and inspect job and statistics views.

For optional cloud generation, set your own credentials before launching:

```powershell
$env:DASHSCOPE_API_KEY="your_api_key_here"
python -m streamlit run app.py
```

The code defaults to `qwen3.7-plus` for DashScope; availability depends on the provider/account and is not established by offline tests. Volcengine is also supported via `VOLCENGINE_API_KEY` and `VOLCENGINE_MODEL`, and takes precedence when configured. `.env.example` documents names only; `.env` is not automatically loaded. Windows persisted environment settings may also be read by the application.

## Main Results

No controlled research benchmark, held-out accuracy result, ablation, or validated salary prediction is available. Functional test outcomes are recorded separately in [the release audit](docs/release-audit.md); they do not establish model quality or hiring validity.

## Limitations

- Scores and match percentages are heuristics, not calibrated measures of employability.
- Industry wage averages are not graduate starting salaries; role mappings and ranges are application assumptions.
- Employment coverage is historical and narrow. Missing years must not be interpreted as measured trends.
- Interview material is adapted preparation content, not an official employer question bank; coverage is incomplete.
- Local hash-based embeddings can vary across Python processes. There is no multi-seed robustness evaluation.
- Cloud calls, credential failure behavior, and provider model availability require separate live verification.
- Optional third-party prompt Skill bundles are omitted pending licensing review. The existing loader tolerates missing files, but cloud prompts may differ from the original local setup.
- Historical Chinese documentation may describe older screen labels; executable code is authoritative.

## Reproducibility

No trained checkpoints are provided or needed. Dependencies retain the project's declared lower bounds rather than a full environment freeze. No fixed global random seed is configured. The offline functional suite and local environment are documented in the release audit. Data transcription and third-party content rights should be reviewed before changing this private repository to public.

## Citation

This repository contains an undergraduate research/course project by Haoming Luo. No associated peer-reviewed publication is claimed.

## Author

Haoming Luo  
Zhongnan University of Economics and Law  
B.Eng. in Artificial Intelligence & B.Mgt. in Accounting

No repository-wide license has been selected; third-party materials retain their respective rights.
