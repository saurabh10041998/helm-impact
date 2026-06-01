import platform
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

PROG = "helm-impact"
_COMPLETION_DIR = Path.home() / ".helm-impact"


def generate_completion(console: Optional[Console] = None) -> None:
    """
    Generate a shell completion script for the current platform and print
    prettified instructions on how to enable it.

    Linux -> bash, macOS -> zsh. Other platforms are reported as unsupported.
    """
    console = console or Console()
    system = platform.system()

    if system == "Linux":
        _install("bash", _bash_script(), "~/.bashrc", console)
    elif system == "Darwin":
        _install("zsh", _zsh_script(), "~/.zshrc", console)
    else:
        console.print(
            Panel(
                f"Shell completion is not supported on "
                f"{system or 'this platform'}.",
                title="Unsupported platform",
                border_style="red",
            )
        )


def _install(shell: str, script: str, rc_file: str, console: Console) -> None:
    path = _COMPLETION_DIR / f"{PROG}-completion.{shell}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script)

    body = (
        f"[bold]{shell}[/bold] completion script written to:\n"
        f"  [cyan]{path}[/cyan]\n\n"
        f"Add the line below to your [bold]{rc_file}[/bold], then reload your "
        f"shell (or run [cyan]source {rc_file}[/cyan])."
    )
    console.print(
        Panel(
            body,
            title=f":sparkles: {PROG} {shell} completion",
            border_style="green",
        )
    )
    console.print(Syntax(f"source {path}", "bash", theme="ansi_dark"))


def _bash_script() -> str:
    return """\
# bash completion for helm-impact
_helm_impact_completion() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local commands="completion"
    local opts="--from --to --resource --hide-resource --help"

    case "$prev" in
        --from|--to)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
            ;;
    esac

    COMPREPLY=( $(compgen -W "${opts} ${commands}" -- "$cur") )
}
complete -F _helm_impact_completion helm-impact
"""


def _zsh_script() -> str:
    return """\
#compdef helm-impact

_helm_impact() {
    _arguments \\
        '--from[Path to the current (from) chart .tgz]:file:_files' \\
        '--to[Path to the upgraded (to) chart .tgz]:file:_files' \\
        '--resource[Only show impact for these resources]:resource:' \\
        '--hide-resource[Hide impact for these resources]:resource:' \\
        '--help[Show help]' \\
        '1:command:(completion)'
}

compdef _helm_impact helm-impact
"""
