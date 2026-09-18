"""
Shell completion support for oci-lock.
Supports bash, zsh, fish, and argcomplete.
"""

import os
import shlex
import sys
from pathlib import Path

from oci_lock.lockfile import LOCK_FILENAME, load_lockfile, resolve_lock_path

SUBCOMMANDS = ["add", "completion", "remove", "rm", "update"]
GLOBAL_FLAGS = ["-f", "--file", "-l", "--lockfile", "-h", "--help"]
SHELLS = ["bash", "zsh", "fish"]


def get_lockfile_keys(lockfile_path: str | Path | None = None) -> list[str]:
    """Retrieve existing image entry keys from the lockfile or oci.log."""
    path = resolve_lock_path(lockfile_path)
    try:
        if not path.exists():
            return []
        data = load_lockfile(path)
        if isinstance(data, dict):
            return sorted(data.keys())
    except Exception:
        return []
    return []


def extract_context(line: str, point: int) -> tuple[list[str], str]:
    """
    Extract the parsed words and the current word being completed
    given the command line and cursor position.
    """
    prefix = line[:point]
    ends_with_space = len(prefix) > 0 and prefix[-1].isspace()
    try:
        raw_words = shlex.split(prefix)
    except ValueError:
        raw_words = prefix.split()

    if ends_with_space:
        cur = ""
        words = raw_words
    else:
        cur = raw_words[-1] if raw_words else ""
        words = raw_words[:-1]

    # Strip the program invocation if present
    if words:
        w0 = os.path.basename(words[0])
        if w0 in ("oci-lock", "oci_lock.py") or w0.startswith("oci-lock"):
            words = words[1:]
        elif w0 in ("python", "python3") and len(words) > 1 and "oci_lock" in words[1]:
            words = words[2:]

    return words, cur


def get_completions(words: list[str], cur: str) -> list[str]:
    """Compute completion candidates based on parsed words and current prefix."""
    # If immediately preceding word is a file flag, complete matching files
    if words and words[-1] in ("-f", "--file", "-l", "--lockfile"):
        try:
            p = Path(cur)
            if cur and cur.endswith(os.sep):
                search_dir = p
                prefix = ""
            elif p.parent != Path("."):
                search_dir = p.parent
                prefix = p.name
            else:
                search_dir = Path(".")
                prefix = cur

            candidates = []
            if search_dir.is_dir():
                for entry in search_dir.iterdir():
                    if entry.name.startswith(prefix):
                        candidates.append(str(entry))
            return sorted(candidates)
        except Exception:
            return []

    # Parse options and command
    lockfile_path = None
    subcmd = None
    subcmd_args = []

    i = 0
    while i < len(words):
        w = words[i]
        if w in ("-f", "--file", "-l", "--lockfile"):
            if i + 1 < len(words):
                lockfile_path = words[i + 1]
                i += 2
                continue
        elif w.startswith(("-f=", "--file=", "-l=", "--lockfile=")):
            lockfile_path = w.split("=", 1)[1]
        elif not w.startswith("-"):
            if subcmd is None:
                subcmd = w
            else:
                subcmd_args.append(w)
        i += 1

    # No subcommand entered yet: complete keywords and flags
    if subcmd is None:
        if cur.startswith("-"):
            return [opt for opt in GLOBAL_FLAGS if opt.startswith(cur)]
        return [cmd for cmd in SUBCOMMANDS if cmd.startswith(cur)] + [
            opt for opt in GLOBAL_FLAGS if opt.startswith(cur)
        ]

    # Flags can be provided after subcommands as well
    if cur.startswith("-"):
        return [opt for opt in GLOBAL_FLAGS if opt.startswith(cur)]

    # Subcommand rm / remove
    if subcmd in ("rm", "remove"):
        if len(subcmd_args) >= 1:
            return []
        keys = get_lockfile_keys(lockfile_path)
        return [k for k in keys if k.startswith(cur)]

    # Subcommand update
    if subcmd == "update":
        if len(subcmd_args) >= 1:
            return []
        keys = get_lockfile_keys(lockfile_path)
        return [k for k in keys if k.startswith(cur)]

    # Subcommand completion
    if subcmd == "completion":
        if len(subcmd_args) == 0:
            return [s for s in SHELLS if s.startswith(cur)]
        return []

    return []


def handle_completion(argv: list[str]):
    """Entrypoint for `oci-lock _complete ...`."""
    words = [a for a in argv if a != "--"]
    if "--line" in words:
        idx = words.index("--line")
        line = words[idx + 1] if idx + 1 < len(words) else ""
        point = len(line)
        if "--point" in words:
            pidx = words.index("--point")
            if pidx + 1 < len(words):
                try:
                    point = int(words[pidx + 1])
                except ValueError:
                    point = len(line)
        ctx_words, cur = extract_context(line, point)
    else:
        if words:
            cur = words[-1]
            ctx_words = words[:-1]
        else:
            cur = ""
            ctx_words = []

    candidates = get_completions(ctx_words, cur)
    for c in candidates:
        print(c)
    sys.exit(0)


def lockfile_completer(prefix, parsed_args=None, **kwargs):
    """Completer function for python-argcomplete integration."""
    lock_path = getattr(parsed_args, "lockfile", None) if parsed_args else None
    return [k for k in get_lockfile_keys(lock_path) if k.startswith(prefix)]


BASH_COMPLETION_SCRIPT = """# Bash completion for oci-lock
_oci_lock_completions() {
    local cur prev words cword
    if type _init_completion &>/dev/null; then
        _init_completion -n : || return
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
    fi

    # Complete filenames after file flags
    if [[ "$prev" == "-f" || "$prev" == "--file" || "$prev" == "-l" || "$prev" == "--lockfile" ]]; then
        COMPREPLY=( $(compgen -f -- "$cur") )
        return 0
    fi

    local line="${COMP_LINE:0:$COMP_POINT}"
    local full_cur="${line##* }"

    local cmd
    if [[ "${COMP_WORDS[0]}" =~ python[0-9.]* ]] && [[ "${COMP_WORDS[1]}" =~ \\.py$ ]]; then
        cmd=("${COMP_WORDS[0]}" "${COMP_WORDS[1]}")
    else
        cmd=("${COMP_WORDS[0]}")
    fi

    local candidates
    candidates=$("${cmd[@]}" _complete --line "$COMP_LINE" --point "$COMP_POINT" 2>/dev/null)
    if [[ $? -ne 0 || -z "$candidates" ]]; then
        return 0
    fi

    COMPREPLY=( $(compgen -W "$candidates" -- "$full_cur") )

    # Handle colon in COMP_WORDBREAKS
    if [[ "$full_cur" == *:* && "$COMP_WORDBREAKS" == *:* ]]; then
        local colon_prefix="${full_cur%${full_cur##*:}}"
        local i=${#COMPREPLY[*]}
        while [ $((--i)) -ge 0 ]; do
            COMPREPLY[$i]="${COMPREPLY[$i]#"$colon_prefix"}"
        done
    fi
}

complete -o default -F _oci_lock_completions oci-lock oci_lock.py
"""

ZSH_COMPLETION_SCRIPT = """#compdef oci-lock oci_lock.py

_oci_lock_completions() {
    local -a cmd
    if [[ "${words[1]}" =~ python[0-9.]* ]] && [[ "${words[2]}" =~ \\.py$ ]]; then
        cmd=("${words[1]}" "${words[2]}")
    else
        cmd=("${words[1]}")
    fi

    local -a candidates
    local output
    output=$("${cmd[@]}" _complete --line "$BUFFER" --point "$CURSOR" 2>/dev/null)
    if [[ -n "$output" ]]; then
        candidates=(${(f)output})
        compadd -Q -- "${candidates[@]}"
    fi
}

if [[ -n ${ZSH_VERSION-} ]]; then
    compdef _oci_lock_completions oci-lock oci_lock.py 2>/dev/null || true
fi
"""

FISH_COMPLETION_SCRIPT = """# Fish completion for oci-lock
function __fish_oci_lock_complete
    set -l line (commandline)
    set -l point (commandline -C)
    set -l prog (commandline -op)[1]
    $prog _complete --line "$line" --point "$point" 2>/dev/null
end

complete -c oci-lock -f -a '(__fish_oci_lock_complete)'
complete -c oci_lock.py -f -a '(__fish_oci_lock_complete)'
"""


def generate_completion_script(shell: str) -> str:
    """Return the completion script for the requested shell."""
    shell = shell.lower()
    if shell == "bash":
        return BASH_COMPLETION_SCRIPT
    elif shell == "zsh":
        return ZSH_COMPLETION_SCRIPT
    elif shell == "fish":
        return FISH_COMPLETION_SCRIPT
    else:
        raise ValueError(f"Unsupported shell: {shell}. Supported shells: bash, zsh, fish")
