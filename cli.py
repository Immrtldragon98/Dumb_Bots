from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from agents.architect import ImplementationPlan, create_plan
from agents.builder import BuildProposal, propose_build, propose_repair
from agents.deployer import (
    DeploymentAnswers,
    create_deployment_plan,
    parse_environment_variable_names,
)
from agents.lead import Ticket, create_ticket
from agents.qa import QaReport, evaluate_qa
from agents.reviewer import ReviewDecision, review_ticket
from core.deployment import push_deployment_files, write_deployment_files
from core.file_changes import create_new_files, replace_existing_files
from core.model import DEFAULT_MODEL, ask_model, available_models
from core.project_setup import initialize_new_python_project
from core.publishing import publish_project
from core.run_reports import write_run_report
from core.workspace import CheckResult, SafetyError, SafeWorkspace

app = typer.Typer(
    name="DumbBots",
    help="A local, review-driven AI engineering team.",
    no_args_is_help=True,
)
console = Console()


def get_project_path(project: str) -> Path:
    if not project or Path(project).name != project:
        raise SafetyError("Project name must be a single folder name.")

    return Path("projects") / project


def get_workspace(project: str) -> SafeWorkspace:
    return SafeWorkspace(get_project_path(project))


def collect_source_files(workspace: SafeWorkspace) -> dict[str, str]:
    return {
        file_name: workspace.read_file(file_name)
        for file_name in workspace.list_files()
        if file_name.endswith(".py") and not file_name.endswith("__init__.py")
    }


def run_checks(workspace: SafeWorkspace) -> list[CheckResult]:
    return [workspace.run_check("pytest"), workspace.run_check("ruff")]


def show_plan(ticket: Ticket, implementation_plan: ImplementationPlan) -> None:
    table = Table(title="Architect Bot plan")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Ticket", ticket.title)
    table.add_row(
        "Target files",
        "\n".join(f"• {item}" for item in implementation_plan.target_files),
    )
    table.add_row(
        "Steps",
        "\n".join(f"• {item}" for item in implementation_plan.steps),
    )
    table.add_row(
        "Tests to add",
        "\n".join(f"• {item}" for item in implementation_plan.tests_to_add),
    )
    table.add_row(
        "Risks",
        "\n".join(f"• {item}" for item in implementation_plan.risks)
        or "None identified",
    )
    console.print(table)


@app.command()
def health() -> None:
    """Show available local models."""
    models = available_models()
    table = Table(title="DumbBots model health")
    table.add_column("Model")

    for model in models:
        table.add_row(model)

    console.print(table)
    status = (
        "[green]Ready:[/green]"
        if DEFAULT_MODEL in models
        else "[red]Missing:[/red]"
    )
    console.print(f"{status} {DEFAULT_MODEL}")


@app.command()
def ping() -> None:
    """Verify that DumbBots can call the local model."""
    reply = ask_model("Reply with exactly: DUMBBOTS_ONLINE")
    console.print(f"[cyan]Model reply:[/cyan] {reply}")


@app.command()
def inspect(project: str) -> None:
    """List files in one assigned project without modifying it."""
    try:
        files = get_workspace(project).list_files()
    except SafetyError as error:
        console.print(f"[red]Blocked:[/red] {error}")
        raise typer.Exit(code=1) from error

    table = Table(title=f"Project: {project}")
    table.add_column("Files")
    for file_name in files:
        table.add_row(file_name)
    console.print(table)


@app.command()
def check(project: str, name: str) -> None:
    """Run an approved check: pytest or ruff."""
    try:
        result = get_workspace(project).run_check(name)
    except SafetyError as error:
        console.print(f"[red]Blocked:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(result.output or "No output.")
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@app.command("create-ticket")
def create_ticket_command(request: str) -> None:
    """Ask Lead Bot to convert a request into one engineering ticket."""
    try:
        ticket = create_ticket(request)
    except Exception as error:
        console.print(f"[red]Lead Bot failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    table = Table(title="Lead Bot ticket")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Title", ticket.title)
    table.add_row("Summary", ticket.summary)
    table.add_row(
        "Acceptance criteria",
        "\n".join(f"• {item}" for item in ticket.acceptance_criteria),
    )
    table.add_row(
        "Out of scope",
        "\n".join(f"• {item}" for item in ticket.out_of_scope),
    )
    table.add_row("Suggested checks", ", ".join(ticket.suggested_checks))
    console.print(table)


@app.command()
def plan(project: str, request: str) -> None:
    """Use Lead and Architect Bots to create a read-only implementation plan."""
    try:
        workspace = get_workspace(project)
        ticket = create_ticket(request)
        implementation_plan = create_plan(ticket, workspace.list_files())
    except (SafetyError, ValueError) as error:
        console.print(f"[red]Planning failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    show_plan(ticket, implementation_plan)


@app.command()
def build(project: str, request: str, approve: bool = False) -> None:
    """Create only Architect-approved new files after explicit approval."""
    if not approve:
        console.print("[yellow]Blocked:[/yellow] rerun with --approve to create files.")
        raise typer.Exit(code=1)

    try:
        workspace = get_workspace(project)
        ticket = create_ticket(request)
        implementation_plan = create_plan(ticket, workspace.list_files())
        proposal: BuildProposal = propose_build(ticket, implementation_plan)
        written = create_new_files(workspace, proposal)
    except (SafetyError, ValueError) as error:
        console.print(f"[red]Build failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print("[green]Builder created:[/green]")
    for file_name in written:
        console.print(f"• {file_name}")


@app.command()
def qa(project: str, request: str) -> None:
    """Run independent read-only QA against one project and ticket."""
    try:
        workspace = get_workspace(project)
        ticket = create_ticket(request)
        checks = run_checks(workspace)
        report: QaReport = evaluate_qa(ticket, collect_source_files(workspace), checks)
    except (SafetyError, ValueError) as error:
        console.print(f"[red]QA failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    table = Table(title="QA Bot report")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Decision", report.decision.upper())
    table.add_row("Summary", report.summary)
    table.add_row("Findings", "\n".join(f"• {item}" for item in report.findings))
    console.print(table)

    if report.decision == "reject":
        raise typer.Exit(code=1)


@app.command()
def review(project: str, request: str) -> None:
    """Run QA, make a final review decision, and save a run report."""
    try:
        workspace = get_workspace(project)
        ticket = create_ticket(request)
        checks = run_checks(workspace)
        qa_report = evaluate_qa(ticket, collect_source_files(workspace), checks)
        decision: ReviewDecision = review_ticket(ticket, qa_report, checks)
        report_path = write_run_report(
            project,
            request,
            ticket,
            qa_report,
            decision,
            checks,
        )
    except (SafetyError, ValueError) as error:
        console.print(f"[red]Review failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    table = Table(title="Reviewer decision")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Decision", decision.decision.upper())
    table.add_row("Rationale", decision.rationale)
    table.add_row(
        "Follow-ups",
        "\n".join(f"• {item}" for item in decision.follow_ups) or "None",
    )
    table.add_row("Run report", str(report_path))
    console.print(table)

    if decision.decision == "reject":
        raise typer.Exit(code=1)


@app.command()
def run(
    project: str,
    request: str,
    approve: bool = False,
    profile: str = typer.Option("library", help="Project profile: library or fastapi."),
) -> None:
    """Run Lead → Architect → Builder → QA → Reviewer for one new feature."""
    try:
        profile = profile.lower()
        if profile not in {"library", "fastapi"}:
            raise ValueError("Profile must be 'library' or 'fastapi'.")

        project_path = get_project_path(project)
        is_new_project = not project_path.exists()
        ticket = create_ticket(request)

        if is_new_project and not approve:
            show_plan(ticket, create_plan(ticket, [], profile))
            console.print(
                "[yellow]Plan ready.[/yellow] Rerun with --approve to create it."
            )
            return

        workspace = (
            initialize_new_python_project(project_path, profile)
            if is_new_project
            else get_workspace(project)
        )
        implementation_plan = create_plan(ticket, workspace.list_files(), profile)

        if not approve:
            show_plan(ticket, implementation_plan)
            console.print("[yellow]Plan ready.[/yellow] Rerun with --approve to build.")
            return

        written = create_new_files(
            workspace,
            propose_build(ticket, implementation_plan, profile),
        )
        checks = run_checks(workspace)
        qa_report = evaluate_qa(ticket, collect_source_files(workspace), checks)
        decision = review_ticket(ticket, qa_report, checks)
        report_path = write_run_report(
            project,
            request,
            ticket,
            qa_report,
            decision,
            checks,
        )
    except (SafetyError, ValueError) as error:
        console.print(f"[red]Run failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    status = "ACCEPTED" if decision.decision == "accept" else "REJECTED"
    console.print(f"[green]Workflow {status}.[/green]")
    console.print(f"Created files: {', '.join(written)}")
    console.print(f"QA: {qa_report.decision.upper()}")
    console.print(f"Reviewer: {decision.decision.upper()}")
    console.print(f"Run report: {report_path}")

    if decision.decision == "reject":
        raise typer.Exit(code=1)


@app.command()
def repair(project: str, request: str, approve: bool = False) -> None:
    """Propose and apply a bounded repair only after a failed approved check."""
    if not approve:
        console.print("[yellow]Blocked:[/yellow] rerun with --approve to repair files.")
        raise typer.Exit(code=1)

    try:
        workspace = get_workspace(project)
        ticket = create_ticket(request)
        failed_checks = [
            check for check in run_checks(workspace) if check.returncode != 0
        ]
        if not failed_checks:
            raise SafetyError("Repair is blocked because all approved checks pass.")

        proposal = propose_repair(
            ticket,
            collect_source_files(workspace),
            failed_checks,
        )
        written = replace_existing_files(workspace, proposal)
        checks = run_checks(workspace)
        qa_report = evaluate_qa(ticket, collect_source_files(workspace), checks)
        decision = review_ticket(ticket, qa_report, checks)
        report_path = write_run_report(
            project,
            request,
            ticket,
            qa_report,
            decision,
            checks,
        )
    except (SafetyError, ValueError) as error:
        console.print(f"[red]Repair failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    status = "ACCEPTED" if decision.decision == "accept" else "REJECTED"
    console.print(f"[green]Repair {status}.[/green]")
    console.print(f"Updated files: {', '.join(written)}")
    console.print(f"QA: {qa_report.decision.upper()}")
    console.print(f"Reviewer: {decision.decision.upper()}")
    console.print(f"Run report: {report_path}")

    if decision.decision == "reject":
        raise typer.Exit(code=1)


@app.command()
def publish(
    project: str,
    approve: bool = False,
    public: bool = False,
) -> None:
    """Publish an accepted project to its own private GitHub repository."""
    if not approve:
        console.print(
            "[yellow]Blocked:[/yellow] rerun with --approve to publish."
        )
        raise typer.Exit(code=1)

    try:
        repository_url = publish_project(
            project,
            get_workspace(project),
            public=public,
        )
    except SafetyError as error:
        console.print(f"[red]Publish failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    visibility = "public" if public else "private"
    console.print(f"[green]Published {visibility} repository:[/green]")
    console.print(repository_url)


@app.command("deploy-chat")
def deploy_chat(project: str) -> None:
    """Interactively prepare and publish safe Render deployment configuration."""
    console.print("[bold cyan]Deployment Bot[/bold cyan]")
    console.print(
        "I will ask for configuration names only. Never paste passwords, tokens, "
        "API keys, or database credentials here."
    )

    try:
        workspace = get_workspace(project)
        audience = typer.prompt(
            "Who should be able to access the product? (public/private)",
            default="public",
        ).strip().lower()
        needs_database = typer.confirm(
            "Does the product need a PostgreSQL database?",
            default=False,
        )
        raw_environment_variables = typer.prompt(
            "Environment variable NAMES, comma-separated (leave blank for none)",
            default="",
            show_default=False,
        )
        region = typer.prompt(
            "Closest Render region",
            default="singapore",
        ).strip().lower()
        answers = DeploymentAnswers(
            audience=audience,
            needs_database=needs_database,
            environment_variables=parse_environment_variable_names(
                raw_environment_variables
            ),
            region=region,
        )
        source_files = collect_source_files(workspace)
        plan = create_deployment_plan(
            project,
            source_files,
            workspace.list_files(),
            answers,
        )
    except (SafetyError, ValueError) as error:
        console.print(f"[red]Deployment planning failed:[/red] {error}")
        raise typer.Exit(code=1) from error

    table = Table(title="Deployment Bot plan")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Provider", "Render")
    table.add_row("Service", plan.service_name)
    table.add_row("Runtime", plan.runtime)
    table.add_row("Region", plan.region)
    table.add_row("Build", plan.build_command)
    table.add_row("Start", plan.start_command)
    table.add_row("Health check", plan.health_path)
    table.add_row("PostgreSQL", "Yes" if plan.needs_database else "No")
    table.add_row(
        "Secret names",
        ", ".join(plan.environment_variables) or "None",
    )
    table.add_row(
        "Steps",
        "\n".join(f"• {item}" for item in plan.explanation),
    )
    console.print(table)

    if not typer.confirm("Create these deployment files?", default=False):
        console.print("[yellow]Deployment cancelled; no files were changed.[/yellow]")
        return

    try:
        written, deeplink = write_deployment_files(project, workspace, plan)
        console.print("[green]Deployment files created:[/green]")
        for file_name in written:
            console.print(f"• {file_name}")

        if typer.confirm(
            "Commit and push these two deployment files to GitHub?",
            default=False,
        ):
            push_deployment_files(workspace)
            console.print("[green]Deployment configuration pushed.[/green]")
            console.print("Open this link and enter secret values directly in Render:")
            console.print(deeplink)
        else:
            console.print(
                "[yellow]Not pushed.[/yellow] Render cannot deploy until the files "
                "are committed and pushed."
            )
    except SafetyError as error:
        console.print(f"[red]Deployment setup failed:[/red] {error}")
        raise typer.Exit(code=1) from error


if __name__ == "__main__":
    app()
