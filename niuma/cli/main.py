"""CLI interface for Niuma using Typer."""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from niuma import __version__
from niuma.config import Settings, get_settings, reset_settings
from niuma.core.agent import AgentRole, AgentRuntime
from niuma.core.task import Task, TaskResult
from niuma.llm.client import LLMClient
from niuma.utils.logging import get_logger, setup_logging

app = typer.Typer(
    name="niuma",
    help="Niuma - A cognitive multi-agent AI system",
    no_args_is_help=True,
)
console = Console()
logger = get_logger("niuma.cli")


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"Niuma version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
    config: Annotated[  # noqa: ARG001
        Path | None,
        typer.Option("--config", "-c", help="Path to config file"),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug mode"),
    ] = False,
) -> None:
    """Niuma CLI."""
    settings = get_settings()

    if debug:
        settings.debug = True
        settings.log_level = "DEBUG"

    # Initialize logging
    setup_logging(
        level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
        file_format=settings.log_file_format,
    )
    logger.debug("Niuma CLI initialized")


def print_banner() -> None:
    """Print welcome banner."""
    banner = Panel(
        Text.assemble(
            ("Niuma", "bold cyan"),
            (" v", "dim"),
            (__version__, "cyan"),
            "\n",
            ("A cognitive multi-agent AI system", "dim"),
        ),
        border_style="cyan",
    )
    console.print(banner)


def check_config() -> bool:
    """Check if required configuration is present."""
    settings = get_settings()

    has_openai = settings.llm.openai_api_key is not None
    has_anthropic = settings.llm.anthropic_api_key is not None

    if not (has_openai or has_anthropic):
        console.print(
            "[red]Error: No API key configured.[/red]\n"
            "Set one of the following environment variables:\n"
            "  - OPENAI_API_KEY\n"
            "  - ANTHROPIC_API_KEY"
        )
        return False

    return True


@app.command()
def run(
    prompt: Annotated[
        str | None,
        typer.Argument(help="Task to execute"),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Interactive mode"),
    ] = False,
) -> None:
    """Run a task with Niuma."""
    print_banner()

    if not check_config():
        sys.exit(1)

    if interactive or prompt is None:
        # Interactive mode
        asyncio.run(_interactive_mode())
    else:
        # Single task mode
        result = asyncio.run(_run_task(prompt))
        if result.success:
            console.print("\n[green]Task completed successfully![/green]")
            if result.output:
                console.print(Panel(str(result.output), title="Result"))
        else:
            console.print(f"\n[red]Task failed:[/red] {result.error}")
            sys.exit(1)


async def _run_task(prompt: str) -> TaskResult:
    """Run a single task."""
    with console.status("[cyan]Initializing...") as status:
        try:
            settings = get_settings()
            llm = LLMClient()

            status.update("[cyan]Creating agent...")
            role = AgentRole(
                name="assistant",
                description="General purpose assistant",
            )
            agent = AgentRuntime(
                role=role,
                llm_client=llm,
            )

            await agent.initialize({})

            status.update("[cyan]Executing task...")
            task = Task(
                description=prompt,
                goal=prompt,
                timeout=settings.agent.default_timeout,
            )

            result = await agent.run(task)

            await agent.terminate()
            await llm.close()

            return result

        except Exception as e:
            return TaskResult(
                success=False,
                error=str(e),
            )


async def _interactive_mode() -> None:
    """Run interactive chat mode."""
    console.print("\n[dim]Enter your tasks below. Type 'exit' or 'quit' to exit.[/dim]\n")

    settings = get_settings()
    llm = LLMClient()

    role = AgentRole(
        name="assistant",
        description="Interactive assistant",
    )
    agent = AgentRuntime(
        role=role,
        llm_client=llm,
    )

    await agent.initialize({})

    try:
        while True:
            user_input = console.input("[cyan]You:[/cyan] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "bye"):
                console.print("[dim]Goodbye![/dim]")
                break

            with console.status("[cyan]Thinking..."):
                task = Task(
                    description=user_input,
                    goal=user_input,
                    timeout=settings.agent.default_timeout,
                )

                result = await agent.run(task)

            if result.success:
                console.print(f"[green]Niuma:[/green] {result.output}")
            else:
                console.print(f"[red]Error:[/red] {result.error}")

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted. Goodbye![/dim]")

    finally:
        await agent.terminate()
        await llm.close()


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option("--show", help="Show current configuration"),
    ] = False,
) -> None:
    """Manage Niuma configuration."""
    settings = get_settings()

    if show:
        console.print("[bold]Current Configuration:[/bold]\n")

        # LLM Settings
        console.print("[cyan]LLM Settings:[/cyan]")
        console.print(f"  Provider: {settings.llm.provider}")
        console.print(f"  OpenAI Model: {settings.llm.openai_model}")
        console.print(f"  Anthropic Model: {settings.llm.anthropic_model}")
        console.print(f"  Temperature: {settings.llm.temperature}")
        console.print()

        # Agent Settings
        console.print("[cyan]Agent Settings:[/cyan]")
        console.print(f"  Max Concurrency: {settings.agent.max_concurrency}")
        console.print(f"  Default Timeout: {settings.agent.default_timeout}s")
        console.print(f"  Max Retries: {settings.agent.max_retries}")
        console.print()

        # Memory Settings
        console.print("[cyan]Memory Settings:[/cyan]")
        console.print(f"  Vector Store: {settings.memory.vector_store_path}")
        console.print(f"  SQLite DB: {settings.memory.sqlite_path}")
        console.print()

        # Check API keys
        has_openai = settings.llm.openai_api_key is not None
        has_anthropic = settings.llm.anthropic_api_key is not None

        console.print("[cyan]API Keys:[/cyan]")
        console.print(
            f"  OpenAI: {'[green]configured[/green]' if has_openai else '[red]not set[/red]'}"
        )
        console.print(
            f"  Anthropic: {'[green]configured[/green]' if has_anthropic else '[red]not set[/red]'}"
        )
    else:
        console.print("Use --show to display configuration")
        console.print("\n[dim]Configuration sources:[/dim]")
        console.print("  1. Environment variables (e.g., OPENAI_API_KEY)")
        console.print("  2. .env file in current directory")
        console.print("  3. Default values")


if __name__ == "__main__":
    app()
