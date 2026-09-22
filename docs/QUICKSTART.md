# DumbBots Quick Start

DumbBots turns one product idea at a time into a reviewed local Python project.
It plans before writing, runs automated checks, asks QA and Reviewer Bots for a
decision, and can prepare an accepted web product for deployment.

## 1. Install once

The supported setup is Windows 11 with WSL Ubuntu. Install Git, Python, GitHub
CLI, and Ollama first, then run:

```bash
cd ~/projects
git clone https://github.com/Immrtldragon98/Dumb_Bots.git dumbbots
cd dumbbots
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5-coder:3b
ruff check .
pytest -q
python cli.py health
```

If `python cli.py health` cannot reach Ollama, open another terminal and run
`ollama serve`. The "address already in use" message means Ollama is already
running and is not an error.

## 2. Start a work session

```bash
cd ~/projects/dumbbots
source .venv/bin/activate
git pull
python cli.py health
```

Copy commands only. Do not copy terminal prompts or previous command output.

## 3. Build an idea

Use a short folder name and put the complete idea inside quotes:

```bash
python cli.py run inventory-api \
  "Build an inventory API with create, list, update and delete operations. Reject negative stock, include GET /health, and write tests." \
  --profile fastapi
```

This first command only shows the ticket and plan. Read its acceptance criteria,
target files, tests, and risks. It does not create the application yet.

Approve by repeating the same command with `--approve`:

```bash
python cli.py run inventory-api \
  "Build an inventory API with create, list, update and delete operations. Reject negative stock, include GET /health, and write tests." \
  --profile fastapi --approve
```

Each idea is isolated under `projects/<name>/`. Starting another idea never
replaces the earlier product.

## 4. Read the result

- `Workflow ACCEPTED` means tests, QA, and Reviewer all accepted the build.
- `Workflow REJECTED` means keep the evidence and use the repair command.
- `runs/<timestamp>.json` contains the full machine-readable run report.
- Generated source, tests, dependencies, and configuration are inside the
  product folder.

## 5. Repair a rejected build

```bash
python cli.py repair inventory-api \
  "Fix every failed check and satisfy the original acceptance criteria without changing scope." \
  --approve
```

Then request a final review using the original product request:

```bash
python cli.py review inventory-api \
  "Build an inventory API with create, list, update and delete operations. Reject negative stock, include GET /health, and write tests."
```

Repeat repair only when an approved check fails. Never delete tests merely to
make a rejection disappear.

## 6. Run the completed app locally

```bash
cd ~/projects/dumbbots/projects/inventory-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ruff check .
pytest -q
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for the interactive API screen and
`http://localhost:8000/health` for its health response. Stop the server with
Ctrl+C.

To test from a phone, connect it to the same network and open
`http://<PC-IP>:8000/docs`. Windows Firewall may need to allow port 8000.

## 7. Publish and deploy an accepted app

Return to the main DumbBots environment:

```bash
cd ~/projects/dumbbots
source .venv/bin/activate
gh auth login
python cli.py publish inventory-api --approve
python cli.py deploy-chat inventory-api
```

Publishing creates a separate GitHub repository for the product. Deployment Bot
asks about audience, database, environment-variable names, and region. It never
asks for secret values; enter those only in the hosting dashboard.

## 8. Start the next idea

```bash
python cli.py run maintenance-planner \
  "Build a maintenance planning API for equipment, PM activities, due dates, status and completion history. Include validation, GET /health, and tests." \
  --profile fastapi
```

Use `--profile fastapi` for web APIs. Omit it for a small Python library.

## Command card

| Goal | Command |
| --- | --- |
| Check Ollama | `python cli.py health` |
| Inspect files | `python cli.py inspect PROJECT` |
| Plan | `python cli.py run PROJECT "IDEA" --profile fastapi` |
| Build | Add `--approve` to the plan command |
| Repair | `python cli.py repair PROJECT "FIX REQUEST" --approve` |
| Review | `python cli.py review PROJECT "ORIGINAL IDEA"` |
| Run tests | `python cli.py check PROJECT pytest` |
| Run Ruff | `python cli.py check PROJECT ruff` |
| Publish | `python cli.py publish PROJECT --approve` |
| Deploy | `python cli.py deploy-chat PROJECT` |

## Common problems

- `command not found`: activate `.venv` and run the command from the DumbBots
  repository.
- `address already in use` from Ollama: it is already running.
- `Refusing to overwrite existing file`: use a new project name or use the
  bounded repair workflow for an existing build.
- GitHub rejects a password: run `gh auth login` and `gh auth setup-git`; GitHub
  does not accept account passwords for Git pushes.
- Import errors inside a generated project: run commands from that project's
  root and keep its `pytest.ini` file.

## Safety boundary

DumbBots is a local development assistant, not an unattended production
operator. Review generated code and dependency choices before exposing an app
to real users. Authentication, authorization, rate limits, backups, migrations,
monitoring, privacy, and security testing must match the product being built.
