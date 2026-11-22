import atexit
import os
import signal
import sys
import tempfile

_FILE_PATH: str | None = None


def parse_env(content: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines into a mapping.

    Surrounding whitespace is stripped from keys and values. Blank lines,
    ``#`` comments and lines without ``=`` are skipped. Duplicate keys
    keep the last value.
    """
    env: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            env[key] = value
    return env


def _cleanup() -> None:
    global _FILE_PATH
    if _FILE_PATH is not None:
        if os.path.exists(_FILE_PATH):
            try:
                os.remove(_FILE_PATH)
            except OSError:
                pass
        _FILE_PATH = None


def _signal_handler(signum: int, frame: object) -> None:
    _cleanup()
    sys.exit(128 + signum)


def setup_cleanup() -> None:
    atexit.register(_cleanup)
    signal.signal(signal.SIGINT, _signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _signal_handler)


def create_temp_env(content: str, path: str | None = None) -> str:
    global _FILE_PATH
    if path is None:
        fd, path = tempfile.mkstemp(suffix=".env", prefix="kleys-")
        os.close(fd)
    with open(path, "w") as f:
        f.write(content)
    if sys.platform != "win32":
        os.chmod(path, 0o600)
    _FILE_PATH = path
    return path


def get_temp_path() -> str | None:
    return _FILE_PATH


def reset_cleanup_state() -> None:
    global _FILE_PATH
    _FILE_PATH = None
