# DumbBots

DumbBots is a local, review-driven AI engineering workflow powered by Ollama.
It separates planning, building, QA, review, repair, publishing, and deployment.

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
