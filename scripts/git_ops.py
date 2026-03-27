"""
git_ops.py — Vertex Git Middleware

Wraps Git CLI commands for the Vertex version-control workflow:
    • snapshot  — stage all changes (git add .)
    • commit   — commit staged changes with a message
    • restore  — checkout a specific commit

All commands use subprocess for safety and proper error handling.
"""

import subprocess


def _run(args, cwd=None):
    """Execute a git command and return stdout.

    Raises subprocess.CalledProcessError on non-zero exit codes.
    """
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def snapshot(cwd=None):
    """Stage all changes in the working tree (git add .).

    Returns:
        str: Git stdout output.
    """
    output = _run(["add", "."], cwd=cwd)
    print("[Vertex] Snapshot — all changes staged.")
    return output


def commit(message="vertex snapshot", cwd=None):
    """Commit staged changes with the given message.

    Args:
        message: Commit message (default: 'vertex snapshot').
        cwd: Working directory for the git command.

    Returns:
        str: Git stdout output.
    """
    output = _run(["commit", "-m", message], cwd=cwd)
    print(f"[Vertex] Committed: \"{message}\"")
    return output


def restore(commit_hash, cwd=None):
    """Checkout a specific commit to restore a previous state.

    Args:
        commit_hash: The SHA hash of the commit to restore.
        cwd: Working directory for the git command.

    Returns:
        str: Git stdout output.
    """
    output = _run(["checkout", commit_hash], cwd=cwd)
    print(f"[Vertex] Restored to commit: {commit_hash}")
    return output


if __name__ == "__main__":
    # Quick manual test — run from the repo root
    snapshot()
    commit()
