# SocialPilot AI

SocialPilot AI turns software projects into clear, evidence-aware professional content. Import a public GitHub repository or paste project notes, analyze the material, create LinkedIn drafts and case studies, review the claims against their source files, then edit and export the result.

The repository contains a React frontend and a Python API. The API handles project ingestion, retrieval-augmented generation (RAG), claim evidence, SQLite persistence, and exports. The frontend provides the project workspace and editing flow.

> **Project status:** This repository currently implements the project-to-content workflow described below. Authentication, multi-user workspaces, direct social publishing, and the other features mentioned in earlier planning material are not part of the current implementation.

## Contents

- [Features](#features)
- [Blockchain and creator payments](#blockchain-and-creator-payments)
- [How it works](#how-it-works)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Using the application](#using-the-application)
- [HTTP API](#http-api)
- [Testing and quality checks](#testing-and-quality-checks)
- [Data, privacy, and security](#data-privacy-and-security)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

### Project import

- Import a **public GitHub repository** by URL.
- Alternatively, paste Markdown project notes or a README.
- Store imported project documents in a local SQLite database.
- For GitHub imports, select a bounded set of relevant source files rather than cloning or executing the repository.

### Project analysis

Generate a structured project profile containing information such as:

- project summary and problem
- target users and technologies
- architecture and engineering decisions
- challenges, results, limitations, and unknowns

### Retrieval and evidence

- Split source documents into line-aware chunks.
- Search source material with BM25 retrieval.
- Optionally combine sparse search with Ollama embeddings and Reciprocal Rank Fusion.
- Attach source references and excerpts to generated claims.
- Mark claims as `supported`, `needs_review`, or `unsupported`.

Evidence checks are intended to assist review; they are not a guarantee that a statement is objectively true.

### Content generation and editing

- Generate LinkedIn drafts for three angles: technical lesson, engineering decision, and personal reflection.
- Generate a structured case study.
- Supply optional user context to guide generation.
- Edit and save artifacts while keeping the generated version separate from the edited version.

### Export

- Export case studies as Markdown.
- Export case studies as PDF when the Typst CLI is installed and available on `PATH`.

## Blockchain and creator payments

Blockchain is a **proposed product direction** for SocialPilot AI, focused on helping developers receive direct support for their work. The landing page includes an illustrative payment concept; it is not a live wallet or payment integration.

### Intended use cases

- **Creator tips:** A supporter could send a voluntary payment directly to a developer's wallet.
- **Developer work purchases:** A buyer could pay for a creator's software, plugin, library, or service.
- **Public transaction records:** Once confirmed, a transfer could be inspected on its network using the transaction reference.

### Proposed user flow

```text
Supporter chooses a tip or listed item
                 |
                 v
       Review recipient and amount
                 |
                 v
   Approve transfer with a compatible wallet
                 |
                 v
      Network confirms the transaction
                 |
                 v
 Creator receives payment / buyer follows delivery details
```

The product concept emphasizes creator-controlled keys: a user's wallet would approve transactions, rather than SocialPilot collecting the creator's private key. Wallet choice, supported network, transaction fees, payment handling, and purchase fulfillment would need to be defined and implemented before this flow could be used.

### What blockchain can and cannot establish

A public chain can provide a record that a wallet address submitted a transaction and that the network confirmed it. By itself, it does **not** establish a person's real-world identity, prove who authored a project, verify a product's quality, guarantee delivery, or validate technical claims. Those responsibilities require separate product processes and user review.

### Implementation status

There is currently **no blockchain integration in the runnable application**: no wallet connection, smart contract, transaction submission, network configuration, or on-chain marketplace. The landing-page payment panel is a visual concept only. Do not use it to send funds or treat its sample products and amounts as real offers.

## How it works

```text
Public GitHub URL or pasted Markdown
                 |
                 v
       Ingest source documents
                 |
                 v
     Chunk and retrieve evidence
                 |
                 v
       Analyze project profile
                 |
                 v
 Generate LinkedIn draft / case study
                 |
                 v
      Check claims against sources
                 |
                 v
         Edit, save, and export
```

The backend is organized into a small HTTP layer (`Backend/api/`), service and domain modules (`Backend/core/`), prompt templates (`Backend/prompts/`), and SQLite persistence. The frontend is a Vite-powered React application, with the main workspace composed from reusable pages and components.

## Technology stack

| Area | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Lucide |
| Backend API | Python, FastAPI, Pydantic, Uvicorn |
| Persistence | SQLite |
| Language models | Ollama or an OpenAI-compatible chat completions API |
| Retrieval | Line-aware chunking, BM25, optional Ollama embeddings |
| PDF generation | Typst (optional) |
| Tests | pytest, ESLint, TypeScript, Vite build |

## Repository layout

```text
project_social_pilot/
├── Backend/
│   ├── api/
│   │   └── main.py               # FastAPI routes
│   ├── core/
│   │   ├── analysis.py           # Project profile generation
│   │   ├── evidence.py           # Claim and source evidence checks
│   │   ├── export.py             # Markdown and PDF exports
│   │   ├── generation.py         # LinkedIn and case-study generation
│   │   ├── ingestion.py          # GitHub and pasted Markdown import
│   │   ├── pipeline.py           # Application workflow orchestration
│   │   ├── rag/                  # Chunking and retrieval
│   │   ├── schemas.py            # Pydantic data models
│   │   └── storage.py            # SQLite persistence
│   ├── data/                     # Local SQLite database directory
│   ├── prompts/                  # LLM prompt templates
│   ├── templates/                # Typst PDF template
│   ├── tests/                    # Backend tests
│   ├── .env.example              # Backend configuration template
│   ├── config.py
│   └── requirements.txt
├── Frontend/
│   └── socilaPilot/              # Vite application (directory name as checked in)
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   ├── services/api.ts   # Frontend API client
│       │   └── types.ts
│       ├── package.json
│       └── vite.config.ts
├── LICENSE
└── Readme.md
```

## Requirements

- Python 3.10 or later is recommended.
- Node.js and npm versions compatible with the Vite version in `Frontend/socilaPilot/package.json`.
- An LLM service:
  - Ollama running locally or at a configured host; or
  - an OpenAI-compatible API endpoint and API key.
- Typst is optional and required only for PDF export.

## Getting started

Open two PowerShell terminals from the repository root: one for the API and one for the frontend.

### 1. Configure and run the backend

```powershell
Set-Location Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The default backend configuration uses Ollama and the `llama3.1:8b` model. Install and start Ollama, then download the configured model:

```powershell
ollama pull llama3.1:8b
```

If you use a different model or provider, update `Backend/.env` as described in [Configuration](#configuration). Start the API:

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Check that the service is responding:

```text
http://localhost:8000/health
```

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

### 2. Install and run the frontend

In a second PowerShell terminal, from the repository root:

```powershell
Set-Location Frontend\socilaPilot
npm install
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`). The development server proxies `/projects`, `/export`, and `/health` requests to `http://localhost:8000`.

The frontend API client also accepts `VITE_API_URL`. Set it only when your deployment serves the frontend and API through a compatible same-origin arrangement (for example, a reverse proxy):

```dotenv
VITE_API_URL=http://localhost:8000
```

Vite environment variables are included in browser code. Do not put API keys, passwords, or other secrets in variables beginning with `VITE_`.

### 3. Optional: enable PDF export

Install Typst using its official installation instructions and ensure the `typst` executable is on `PATH`. If Typst is not available, Markdown export remains available and the PDF endpoint returns an explanatory error.

## Configuration

Backend settings are loaded from `Backend/.env`. The checked-in template is [`Backend/.env.example`](./Backend/.env.example).

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | Provider selection: `ollama` or `openai_compatible`. |
| `LLM_MODEL` | `llama3.1:8b` | Model name passed to the configured provider. |
| `LLM_TIMEOUT_S` | `120` | Model request timeout in seconds. |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL. |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Base URL for an OpenAI-compatible API. |
| `OPENAI_API_KEY` | empty | API key for the OpenAI-compatible provider. |
| `USE_EMBEDDINGS` | `0` | Set to `1` to enable optional dense retrieval alongside BM25. |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model used when dense retrieval is enabled. |
| `GITHUB_TOKEN` | empty | Optional token for GitHub API access/rate limits; do not commit it. |
| `DB_PATH` | `data/socialpilot.db` | SQLite database file path, relative to the backend working directory unless absolute. |

For the OpenAI-compatible provider, set at minimum:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_MODEL=your-model-name
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-key
```

Use a provider and model that support the structured JSON responses required by analysis and generation.

## Using the application

1. Open SocialPilot and enter the project workspace.
2. Import a public GitHub repository or paste Markdown notes.
3. Review the imported sources and run project analysis.
4. Generate a LinkedIn draft by selecting an angle, or create a case study.
5. Review each claim and its evidence status and source references.
6. Edit the generated content, save the edited artifact, and export the case study if needed.

Supported LinkedIn angles:

| Angle | Intended focus |
| --- | --- |
| `technical_lesson` | Explain a technical lesson learned from the project. |
| `engineering_decision` | Describe an engineering choice and its trade-offs. |
| `personal_reflection` | Draft a reflective narrative; the model may request additional personal context. |

## HTTP API

The API is served by `Backend/api/main.py`. JSON request and response schemas are documented interactively at `/docs`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check API availability. |
| `GET` | `/projects` | List stored projects. |
| `POST` | `/projects/import` | Import a GitHub repository or pasted Markdown. |
| `GET` | `/projects/{project_id}` | Retrieve project, source documents, profile, and saved artifacts. |
| `POST` | `/projects/{project_id}/analyze` | Analyze project sources and save the profile. |
| `POST` | `/projects/{project_id}/linkedin/{angle}` | Generate a LinkedIn draft for a supported angle. |
| `POST` | `/projects/{project_id}/case-study` | Generate a case study. |
| `PUT` | `/projects/{project_id}/artifacts/{artifact_type}` | Save an edited artifact. |
| `POST` | `/export/markdown` | Return a case study as Markdown. |
| `POST` | `/export/pdf` | Return a case study as PDF (requires Typst). |

Example import request using pasted Markdown:

```json
{
  "pasted_readme": "# Project name\n\nDescribe the project, its architecture, and what you learned."
}
```

Example generation request:

```json
{
  "user_context": "I worked on the API and learned how to structure retrieval."
}
```

For GitHub import, the request uses a `repo_url` field. For a complete and current contract, consult the generated OpenAPI page rather than relying on an outdated endpoint example.

## Testing and quality checks

### Backend

From the `Backend` directory, with the virtual environment active:

```powershell
pytest -q
```

The tests cover ingestion, RAG retrieval, evidence checks, storage, and exports.

### Frontend

From `Frontend\socilaPilot`:

```powershell
npm run lint
npm run build
```

The production build runs TypeScript project checks before building the Vite assets.

## Data, privacy, and security

- The backend stores imported source content, project profiles, and generated/edited artifacts in SQLite. By default, the database is `Backend/data/socialpilot.db` when the API is started from the `Backend` directory.
- GitHub imports are limited to public GitHub repositories. The importer selects a limited set of text/configuration files and filters common generated/dependency directories and secret-like filenames; this is a safeguard, not a guarantee that all sensitive data will be excluded.
- Pasted Markdown and imported repository content are treated as input data, not code to execute.
- Model calls send relevant project content to the selected LLM provider. Review that provider's data handling terms before using private or sensitive project material.
- The current API does not implement user authentication or per-user project ownership. Do not expose it to an untrusted network as-is.
- Keep `.env` files and provider credentials private. Do not commit secrets to source control.
- Use HTTPS and appropriate access controls when deploying beyond local development.

## Known limitations

- GitHub import supports public repositories only; private repository authorization is not implemented.
- HTTP import supports GitHub URLs and pasted Markdown. Local directory import is not exposed by the API.
- Repository ingestion is intentionally bounded (up to 25 candidate files, 60 KB per file, and 400 KB total by default in `Backend/config.py`).
- Project profile and content quality depend on source coverage, model capability, and user-provided context.
- Evidence matching is heuristic. A `supported` label is a review aid, not an independent verification or publication approval.
- PDF export depends on the external Typst executable.
- The current app is a single-user project workspace; social accounts, publishing integrations, and marketplace workflows are outside this checkout's implemented scope.

## Troubleshooting

### The frontend cannot reach the API

- Confirm Uvicorn is running at `http://localhost:8000`.
- Open `http://localhost:8000/health` directly.
- Run the frontend through Vite so its configured development proxy is active. For deployments, serve the API and frontend through the same origin or configure a reverse proxy; this API does not currently enable cross-origin requests.

### Model requests fail

- Confirm the model service is running at the configured host.
- Confirm `LLM_PROVIDER` and `LLM_MODEL` match the provider and installed model.
- For Ollama, pull the model named by `LLM_MODEL`.
- For a hosted provider, check `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and provider compatibility.

### GitHub reports a rate limit or no usable files

- Set `GITHUB_TOKEN` in `Backend/.env` to raise the GitHub API rate limit.
- Ensure the repository is public and includes supported text/source files.
- Paste the project's README or notes as an alternative.

### PDF export is unavailable

- Install Typst and restart the API process so its executable is available on `PATH`.
- Use Markdown export if Typst is not available.

## Contributing

Contributions are welcome. Before submitting a change:

1. Keep API schemas and frontend types aligned.
2. Add or update focused tests for backend behavior.
3. Run `pytest -q` for backend changes.
4. Run `npm run lint` and `npm run build` for frontend changes.
5. Never commit credentials, local environment files, or private project data.

## License

This project is distributed under the Apache License 2.0. See [`LICENSE`](./LICENSE) for the full license text.
