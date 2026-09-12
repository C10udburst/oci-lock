import os
import sys

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def col(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def green(text: str) -> str:
    return col(text, "32")


def yellow(text: str) -> str:
    return col(text, "33")


def cyan(text: str) -> str:
    return col(text, "36")


def bold(text: str) -> str:
    return col(text, "1")


def dim(text: str) -> str:
    return col(text, "2")


def red(text: str) -> str:
    return col(text, "31")
