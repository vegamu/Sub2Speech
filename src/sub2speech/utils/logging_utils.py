from datetime import datetime


def log_info(message: str) -> None:
    _log("INFO", message)


def log_error(message: str) -> None:
    _log("ERROR", message)


def _log(level: str, message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {message}", flush=True)
