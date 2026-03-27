"""
sync.py — Vertex Auto-Sync

One-command workflow: serialize → git add → commit → push.
Combines all steps into a single operation for quick collaboration.

Usage:
    # Basic sync:
    blender --background file.blend --python scripts/sync.py

    # With user and commit message:
    blender --background file.blend --python scripts/sync.py -- --user sanyam -m "updated lighting"

    # Pull latest changes before syncing:
    blender --background file.blend --python scripts/sync.py -- --pull
"""

import bpy
import json
import os
import sys
import subprocess
import shutil
import glob
from datetime import datetime


# ───────────────────────────────────
# 🔹 Git helpers
# ───────────────────────────────────
def git(args, cwd=None):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ───────────────────────────────────
# 🔹 Parse args
# ───────────────────────────────────
def parse_args():
    argv = sys.argv
    if "--" in argv:
        script_args = argv[argv.index("--") + 1:]
    else:
        script_args = []

    user = "unknown"
    message = None
    pull = False

    i = 0
    while i < len(script_args):
        if script_args[i] == "--user" and i + 1 < len(script_args):
            user = script_args[i + 1]
            i += 2
        elif script_args[i] == "-m" and i + 1 < len(script_args):
            message = script_args[i + 1]
            i += 2
        elif script_args[i] == "--pull":
            pull = True
            i += 1
        else:
            i += 1

    return user, message, pull


# ───────────────────────────────────
# 🔹 Serialize (inline, no import needed)
# ───────────────────────────────────
def load_previous(filepath):
    if not os.path.isfile(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {entry["name"]: entry for entry in data}


def transforms_changed(prev, loc, rot, scale):
    return prev["loc"] != loc or prev["rot"] != rot or prev["scale"] != scale


def collect_spatial_data(user, previous):
    seen_names = set()
    entries = []
    now = datetime.now().isoformat(timespec="seconds")

    for obj in bpy.data.objects:
        name = obj.name
        if name in seen_names:
            raise ValueError(f"Duplicate object name: '{name}'")
        seen_names.add(name)

        loc = [round(v, 6) for v in obj.location]
        rot = [round(v, 6) for v in obj.rotation_euler]
        scale = [round(v, 6) for v in obj.scale]

        prev = previous.get(name)
        if prev and not transforms_changed(prev, loc, rot, scale):
            modified_by = prev.get("modified_by", user)
            modified_at = prev.get("modified_at", now)
        else:
            modified_by = user
            modified_at = now

        entries.append({
            "name": name,
            "loc": loc,
            "rot": rot,
            "scale": scale,
            "modified_by": modified_by,
            "modified_at": modified_at,
        })

    return entries


def write_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_next_version(history_dir):
    os.makedirs(history_dir, exist_ok=True)
    existing = glob.glob(os.path.join(history_dir, "v*.json"))
    if not existing:
        return 1
    versions = []
    for f in existing:
        basename = os.path.basename(f)
        try:
            num = int(basename.split("_")[0][1:])
            versions.append(num)
        except (ValueError, IndexError):
            continue
    return max(versions, default=0) + 1


# ───────────────────────────────────
# 🔹 Main
# ───────────────────────────────────
def main():
    user, message, pull_first = parse_args()
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    output_path = os.path.join(base_dir, "data", "spatial.json")
    history_dir = os.path.join(base_dir, "data", "history")

    print(f"\n[Vertex] 🔄 Sync started — user: {user}\n")

    # ── Step 0: Pull first (if requested) ──
    if pull_first:
        print("[Vertex] ⬇️  Pulling latest changes...")
        stdout, stderr, code = git(["pull", "--rebase"], cwd=base_dir)
        if code == 0:
            print(f"[Vertex] ✅ Pull complete")
            # Reload blend file after pull
            blend_path = bpy.data.filepath
            if blend_path and os.path.isfile(blend_path):
                bpy.ops.wm.open_mainfile(filepath=blend_path)
                print(f"[Vertex] 🔄 Reloaded .blend after pull")
        else:
            print(f"[Vertex] ⚠️  Pull issue: {stderr}")
            print("[Vertex] Continuing with sync...")

    # ── Step 1: Serialize ──
    print("[Vertex] 📦 Step 1/4 — Serializing scene...")
    previous = load_previous(output_path)

    # Save snapshot
    if os.path.isfile(output_path):
        version = get_next_version(history_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_name = f"v{version:03d}_{timestamp}.json"
        snapshot_path = os.path.join(history_dir, snapshot_name)
        os.makedirs(history_dir, exist_ok=True)
        shutil.copy2(output_path, snapshot_path)
        print(f"         📸 Snapshot: {snapshot_name}")

    spatial_data = collect_spatial_data(user, previous)
    write_json(spatial_data, output_path)
    print(f"         Serialized {len(spatial_data)} object(s)")

    # ── Step 2: Git add ──
    print("[Vertex] 📋 Step 2/4 — Staging changes...")
    stdout, stderr, code = git(["add", "."], cwd=base_dir)
    if code == 0:
        print("         All changes staged")
    else:
        print(f"         ⚠️  Stage issue: {stderr}")

    # ── Step 3: Commit ──
    if message is None:
        message = f"vertex sync by {user} at {datetime.now().strftime('%H:%M:%S')}"

    print(f"[Vertex] 💾 Step 3/4 — Committing: \"{message}\"")
    stdout, stderr, code = git(["commit", "-m", message], cwd=base_dir)
    if code == 0:
        print("         Committed successfully")
    elif "nothing to commit" in stdout or "nothing to commit" in stderr:
        print("         Nothing to commit (no changes)")
    else:
        print(f"         ⚠️  Commit issue: {stderr}")

    # ── Step 4: Push ──
    print("[Vertex] ⬆️  Step 4/4 — Pushing to remote...")
    stdout, stderr, code = git(["push"], cwd=base_dir)
    if code == 0:
        print("         Pushed successfully")
    else:
        # Try push with upstream
        stdout, stderr, code = git(["push", "--set-upstream", "origin", "HEAD"], cwd=base_dir)
        if code == 0:
            print("         Pushed successfully (set upstream)")
        else:
            print(f"         ⚠️  Push issue: {stderr}")
            print("         You may need to pull first: use --pull flag")

    print(f"\n[Vertex] ✅ Sync complete!\n")


if __name__ == "__main__":
    main()
