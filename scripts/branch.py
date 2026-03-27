"""
branch.py — Vertex Branch Manager

Manage Git branches from within Blender for parallel workflows.

Usage:
    # List all branches:
    blender --background file.blend --python scripts/branch.py

    # Create and switch to a new branch:
    blender --background file.blend --python scripts/branch.py -- --create lighting-v2

    # Switch to an existing branch:
    blender --background file.blend --python scripts/branch.py -- --switch main

    # Delete a branch:
    blender --background file.blend --python scripts/branch.py -- --delete lighting-v2
"""

import bpy
import subprocess
import sys
import os


# ───────────────────────────────────
# 🔹 Git helpers
# ───────────────────────────────────
def git(args, cwd=None):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and result.stderr:
        error_msg = result.stderr.strip()
        if error_msg:
            print(f"[Vertex] ⚠️  Git: {error_msg}")
    return result.stdout.strip(), result.returncode


# ───────────────────────────────────
# 🔹 Parse args
# ───────────────────────────────────
def parse_args():
    argv = sys.argv
    if "--" in argv:
        script_args = argv[argv.index("--") + 1:]
    else:
        script_args = []

    create = None
    switch = None
    delete = None

    i = 0
    while i < len(script_args):
        if script_args[i] == "--create" and i + 1 < len(script_args):
            create = script_args[i + 1]
            i += 2
        elif script_args[i] == "--switch" and i + 1 < len(script_args):
            switch = script_args[i + 1]
            i += 2
        elif script_args[i] == "--delete" and i + 1 < len(script_args):
            delete = script_args[i + 1]
            i += 2
        else:
            i += 1

    return create, switch, delete


# ───────────────────────────────────
# 🔹 Branch operations
# ───────────────────────────────────
def list_branches(cwd):
    """List all branches, highlighting the current one."""
    output, _ = git(["branch", "-a"], cwd=cwd)
    if not output:
        print("[Vertex] ❌ No branches found. Is this a git repository?")
        return

    print(f"\n[Vertex] 🌿 Branches:\n")
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("* "):
            branch = line[2:]
            print(f"  ★ {branch} (current)")
        elif line.startswith("remotes/"):
            print(f"    {line}")
        else:
            print(f"    {line}")
    print()


def create_branch(name, cwd):
    """Create a new branch and switch to it."""
    print(f"[Vertex] Creating branch '{name}'...")

    # Create and switch
    output, code = git(["checkout", "-b", name], cwd=cwd)
    if code == 0:
        print(f"[Vertex] ✅ Created and switched to branch: {name}")
    else:
        print(f"[Vertex] ❌ Failed to create branch: {name}")


def switch_branch(name, cwd):
    """Switch to an existing branch."""
    print(f"[Vertex] Switching to branch '{name}'...")

    output, code = git(["checkout", name], cwd=cwd)
    if code == 0:
        print(f"[Vertex] ✅ Switched to branch: {name}")

        # Reload the blend file to reflect the branch's state
        blend_path = bpy.data.filepath
        if blend_path and os.path.isfile(blend_path):
            bpy.ops.wm.open_mainfile(filepath=blend_path)
            print(f"[Vertex] 🔄 Reloaded: {os.path.basename(blend_path)}")
    else:
        print(f"[Vertex] ❌ Failed to switch to branch: {name}")


def delete_branch(name, cwd):
    """Delete a branch (cannot delete current branch)."""
    # Check current branch
    current, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if current == name:
        print(f"[Vertex] ❌ Cannot delete the current branch. Switch first.")
        return

    print(f"[Vertex] Deleting branch '{name}'...")
    output, code = git(["branch", "-d", name], cwd=cwd)
    if code == 0:
        print(f"[Vertex] ✅ Deleted branch: {name}")
    else:
        # Try force delete
        try:
            choice = input("[Vertex] Branch not fully merged. Force delete? (y/n): ").strip().lower()
            if choice == "y":
                output, code = git(["branch", "-D", name], cwd=cwd)
                if code == 0:
                    print(f"[Vertex] ✅ Force deleted branch: {name}")
        except EOFError:
            print("[Vertex] ❌ Aborted.")


# ───────────────────────────────────
# 🔹 Main
# ───────────────────────────────────
def main():
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    create, switch, delete = parse_args()

    if create:
        create_branch(create, base_dir)
    elif switch:
        switch_branch(switch, base_dir)
    elif delete:
        delete_branch(delete, base_dir)
    else:
        list_branches(base_dir)


if __name__ == "__main__":
    main()
