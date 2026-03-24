"""
Remote Control Dashboard — the command center for The Agent Factory.

Commands:
  submit <description>           Submit a project; agents run it autonomously
  status                         Show all projects
  watch  <project_id>            Inspect a project's task breakdown
  logs   <project_id>            View full agent output for a project
  steer  <project_id> <message>  Inject a new direction into a project
  cleanup [project_id]           Run the entropy cleanup agent
  list                           Alias for status
  help                           Show this help
"""
import asyncio
import sys
import uuid
from datetime import datetime
from typing import Callable

import anthropic
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from ..tasks.queue import list_projects, load_project, save_project
from ..tasks.models import ProjectStatus, TaskStatus
from .dispatcher import run_project
from ..agents.cleaner import run_entropy_cleanup

console = Console()

_STATUS_COLORS = {
    "pending":     "yellow",
    "decomposing": "cyan",
    "running":     "blue",
    "completed":   "green",
    "failed":      "red",
    "steered":     "orange1",
}

_TASK_ICONS = {
    "pending":   "⏳",
    "running":   "🔄",
    "completed": "✅",
    "failed":    "❌",
    "skipped":   "⏭",
}


def _sc(status: str) -> str:
    return _STATUS_COLORS.get(status, "white")


class RemoteControl:
    """CLI remote control for The Agent Factory."""

    # ------------------------------------------------------------------ banner
    def _banner(self):
        console.print(Panel(
            Text("THE AGENT FACTORY", justify="center", style="bold white on black"),
            subtitle="[dim]Harness Engineering  ·  Fully Autonomous Coding System[/dim]",
            style="bold cyan",
            box=box.DOUBLE,
        ))

    # ------------------------------------------------------------------ submit
    async def cmd_submit(self, args: list[str]):
        if not args:
            console.print("[red]Usage: submit <project description>[/red]")
            return

        description = " ".join(args)
        project_id = str(uuid.uuid4())[:8]

        console.print(Panel(
            f"[bold]Description:[/bold] {description}\n[bold]Project ID:[/bold]  {project_id}",
            title="[cyan]Submitting to The Agent Factory[/cyan]",
            style="cyan",
        ))

        def stream(text: str):
            console.print(text, end="", highlight=False)

        await run_project(project_id, description, stream_callback=stream)

    # ------------------------------------------------------------------ status
    async def cmd_status(self, args: list[str]):
        projects = list_projects()
        if not projects:
            console.print("[yellow]No projects yet. Run: python main.py submit \"your project\"[/yellow]")
            return

        table = Table(
            title="The Agent Factory — Projects",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("ID",          style="cyan",  width=10)
        table.add_column("Description", style="white", max_width=52)
        table.add_column("Status",      width=14)
        table.add_column("Tasks",       justify="center", width=9)
        table.add_column("Created",     style="dim",   width=20)

        for p in projects:
            done  = len(p.completed_tasks())
            total = len(p.tasks)
            color = _sc(p.status)
            desc  = p.description
            if len(desc) > 50:
                desc = desc[:49] + "…"
            table.add_row(
                p.id,
                desc,
                f"[{color}]{p.status}[/{color}]",
                f"{done}/{total}",
                p.created_at[:19].replace("T", " "),
            )

        console.print(table)

    # ------------------------------------------------------------------ watch
    async def cmd_watch(self, args: list[str]):
        if not args:
            console.print("[red]Usage: watch <project_id>[/red]")
            return

        project = load_project(args[0])
        if not project:
            console.print(f"[red]Project '{args[0]}' not found.[/red]")
            return

        color = _sc(project.status)
        console.print(Panel(
            f"[bold]{project.description}[/bold]\n"
            f"Status: [{color}]{project.status}[/{color}]",
            title=f"[cyan]Project {project.id}[/cyan]",
        ))

        if not project.tasks:
            console.print("[yellow]No tasks yet.[/yellow]")
            return

        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("Task",   style="cyan",   width=10)
        table.add_column("Type",   width=8)
        table.add_column("Layer",  width=8)
        table.add_column("Status", width=14)
        table.add_column("Score",  width=7)
        table.add_column("Description", max_width=48)

        for t in project.tasks:
            icon  = _TASK_ICONS.get(t.status, "•")
            score = str(t.review.get("score", "")) if t.review else ""
            table.add_row(
                t.id, t.type, t.layer,
                f"{icon} {t.status}",
                score,
                t.description[:46],
            )

        console.print(table)

    # ------------------------------------------------------------------ logs
    async def cmd_logs(self, args: list[str]):
        if not args:
            console.print("[red]Usage: logs <project_id>[/red]")
            return

        project = load_project(args[0])
        if not project:
            console.print(f"[red]Project '{args[0]}' not found.[/red]")
            return

        console.print(Panel(
            f"[bold]{project.description}[/bold]",
            title=f"[cyan]Logs: {project.id}[/cyan]",
        ))

        for task in project.tasks:
            if task.output:
                verdict = ""
                if task.review:
                    v = task.review.get("verdict", "")
                    s = task.review.get("score", "")
                    verdict = f"  [dim]review: {v} {s}/10[/dim]"
                console.print(Panel(
                    task.output,
                    title=f"[cyan]{task.id}[/cyan] — {task.description[:50]}{verdict}",
                    subtitle=f"[{_sc(task.status)}]{task.status}[/{_sc(task.status)}]",
                ))

    # ------------------------------------------------------------------ steer
    async def cmd_steer(self, args: list[str]):
        if len(args) < 2:
            console.print("[red]Usage: steer <project_id> <new direction>[/red]")
            return

        project = load_project(args[0])
        if not project:
            console.print(f"[red]Project '{args[0]}' not found.[/red]")
            return

        direction = " ".join(args[1:])
        project.steering_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "direction": direction,
        })
        project.status = ProjectStatus.STEERED.value
        save_project(project)

        console.print(Panel(
            f"[bold]New direction:[/bold] {direction}\n\n"
            f"[dim]Steering recorded. Pending tasks will pick up this context on next run.[/dim]",
            title=f"[orange1]Steering {args[0]}[/orange1]",
        ))

    # ------------------------------------------------------------------ cleanup
    async def cmd_cleanup(self, args: list[str]):
        project_id = args[0] if args else None
        label = f"project {project_id}" if project_id else "all projects"
        console.print(f"\n[cyan]Running entropy cleanup on {label}...[/cyan]\n")

        client = anthropic.AsyncAnthropic()

        def stream(text: str):
            console.print(text, end="", highlight=False)

        report = await run_entropy_cleanup(client, project_id=project_id, stream_callback=stream)

        score = report.get("entropy_score", 0)
        color = "green" if score < 4 else "yellow" if score < 7 else "red"
        devs  = report.get("deviations", [])

        console.print(Panel(
            f"[bold]Entropy Score:[/bold] [{color}]{score}/10[/{color}]\n"
            f"[bold]Deviations:[/bold]    {len(devs)}\n\n"
            f"{report.get('summary', '')}",
            title="[cyan]Entropy Report[/cyan]",
        ))

        if devs:
            table = Table(box=box.SIMPLE, title="Deviations")
            table.add_column("Principle", style="yellow", max_width=26)
            table.add_column("Location",  style="dim",    max_width=20)
            table.add_column("Violation",                 max_width=40)
            for d in devs[:12]:
                table.add_row(
                    d.get("principle", ""),
                    d.get("location", ""),
                    d.get("violation", "")[:38],
                )
            console.print(table)

    # ------------------------------------------------------------------ help
    async def cmd_help(self, _args: list[str]):
        console.print(Panel(
            (
                "[bold cyan]submit[/bold cyan]  [dim]<description>[/dim]          "
                "Submit a project — agents run it fully autonomously\n"
                "[bold cyan]status[/bold cyan]                           "
                "Show all projects and their status\n"
                "[bold cyan]watch[/bold cyan]   [dim]<project_id>[/dim]           "
                "Inspect a project's task breakdown\n"
                "[bold cyan]logs[/bold cyan]    [dim]<project_id>[/dim]           "
                "View full agent output\n"
                "[bold cyan]steer[/bold cyan]   [dim]<project_id> <message>[/dim] "
                "Inject new direction into a project\n"
                "[bold cyan]cleanup[/bold cyan] [dim][project_id][/dim]           "
                "Run entropy cleanup agent\n"
                "[bold cyan]list[/bold cyan]                             "
                "Alias for status\n"
                "[bold cyan]help[/bold cyan]                             "
                "Show this help"
            ),
            title="[cyan]Remote Control[/cyan]",
            subtitle="[dim]Agent = Model + Harness[/dim]",
        ))

    # ------------------------------------------------------------------ router
    async def run(self, argv: list[str]):
        self._banner()

        if not argv:
            await self.cmd_help([])
            return

        commands = {
            "submit":  self.cmd_submit,
            "status":  self.cmd_status,
            "list":    self.cmd_status,
            "watch":   self.cmd_watch,
            "logs":    self.cmd_logs,
            "steer":   self.cmd_steer,
            "cleanup": self.cmd_cleanup,
            "help":    self.cmd_help,
        }

        cmd = argv[0].lower()
        if cmd not in commands:
            console.print(f"[red]Unknown command: {cmd}[/red]\n")
            await self.cmd_help([])
            return

        await commands[cmd](argv[1:])
