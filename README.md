# DumbBots

DumbBots is a local, review-driven AI engineering workflow powered by Ollama.
It separates planning, building, QA, review, repair, publishing, and deployment.

## The simple way

Install DumbBots once. For every product idea, repeat this loop:

```text
Idea -> Plan -> Approve -> Test -> Run locally -> Publish -> Deploy
```

```bash
# 1. Start DumbBots
cd ~/projects/dumbbots
source .venv/bin/activate

# 2. Ask for a plan
python cli.py run my-app "Describe the product clearly" --profile fastapi

# 3. Approve the build
python cli.py run my-app "Describe the product clearly" --profile fastapi --approve

# 4. If QA rejects it
python cli.py repair my-app "Fix every failed check without changing scope" --approve
```

Your product is saved in `projects/my-app/`. See
[docs/QUICKSTART.md](docs/QUICKSTART.md) for setup, local running, publishing,
deployment, and troubleshooting. A printable guide is available at
[docs/DumbBots_Quick_Start.pdf](docs/DumbBots_Quick_Start.pdf).

## Workflow

```text
Lead → Architect → Builder → QA → Reviewer → Deployment Bot
```

Generated projects are stored under `projects/<project-name>/`. Run reports are
stored under `runs/` and are required before publishing or deployment.

## Core commands

```bash
python cli.py run PROJECT "REQUEST"
python cli.py run PROJECT "REQUEST" --approve
python cli.py repair PROJECT "REQUEST" --approve
python cli.py review PROJECT "REQUEST"
python cli.py publish PROJECT --approve
python cli.py deploy-chat PROJECT
```

## Build a web product

Use the FastAPI profile when the result should be an HTTP product that can run
locally and be handed to Deployment Bot:

```bash
python cli.py run inventory-api "Build an inventory API" --profile fastapi
python cli.py run inventory-api "Build an inventory API" --profile fastapi --approve
```

The profile creates a Python 3.12 project manifest, approved runtime
dependencies, a fixed `src.main:app` entrypoint, a `/health` requirement, and
API tests. After review and publish, run `python cli.py deploy-chat inventory-api`.

## Deployment Bot

`deploy-chat` is an interactive Render deployment assistant for accepted Python
web applications. It asks about the audience, PostgreSQL, environment-variable
names, and region. It then shows a plan before changing files.

The bot never asks for secret values. Secrets are represented in `render.yaml`
with `sync: false` and must be entered directly in the Render dashboard.

Deployment requires:

- an accepted Reviewer report with passing checks;
- a real ASGI or WSGI web application;
- a separately published GitHub repository;
- explicit confirmation before files are created or pushed.

The first supported online profile is a free Render Python web service. Static,
Node.js, worker, cron, and multi-service profiles can be added later without
loosening the command allowlist.
