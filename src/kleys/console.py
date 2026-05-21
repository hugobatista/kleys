import typer


def info(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.CYAN)


def success(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.GREEN)


def warn(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.YELLOW)


def error(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)


def cmd(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.CYAN, bold=True)
