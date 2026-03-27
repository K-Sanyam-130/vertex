"""
restore.py — Vertex Spatial Restorer (Multi-Version)

Reverts the Blender scene to a previously serialized version.

- If only 1 snapshot exists  → restores it directly
- If multiple snapshots exist → lists them and asks user to pick

Run inside Blender:
    blender --background file.blend --python scripts/restore.py
"""

import bpy
import json
import os
import glob
import shutil


# -------------------------------
# 🔹 Load JSON
# -------------------------------
def load_json(filepath):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Spatial data not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------
# 🔹 Delete extra objects
# -------------------------------
def cleanup_scene(valid_names):
    """Remove objects not present in JSON data."""
    for obj in list(bpy.data.objects):
        if obj.name not in valid_names:
            bpy.data.objects.remove(obj, do_unlink=True)


# -------------------------------
# 🔹 Get or create object
# -------------------------------
def get_or_create_object(name):
    obj = bpy.data.objects.get(name)
    if obj:
        return obj
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    obj.name = name
    return obj


# -------------------------------
# 🔹 Apply transforms
# -------------------------------
def apply_transforms(obj, entry):
    obj.location = entry["loc"]
    obj.rotation_euler = entry["rot"]
    obj.scale = entry["scale"]


# -------------------------------
# 🔹 Get sorted version entries
# -------------------------------
def get_versions(history_dir):
    """Return list of (version_num, timestamp, is_merge, filepath) sorted by version."""
    files = sorted(glob.glob(os.path.join(history_dir, "v*.json")))
    entries = []
    for f in files:
        basename = os.path.basename(f)
        try:
            parts = basename.replace(".json", "").split("_", 1)
            ver_num = int(parts[0][1:])
            rest = parts[1] if len(parts) > 1 else "unknown"
            is_merge = rest.startswith("merge_")
            timestamp = rest.replace("merge_", "").replace("_", " ") if is_merge else rest.replace("_", " ")
            entries.append((ver_num, timestamp, is_merge, f))
        except (ValueError, IndexError):
            continue
    return entries


# -------------------------------
# 🔹 Restore from a snapshot
# -------------------------------
def restore_from(snapshot_path, current_path):
    """Apply a snapshot to the scene and save."""
    spatial_data = load_json(snapshot_path)
    json_names = {entry["name"] for entry in spatial_data}

    cleanup_scene(json_names)

    created = 0
    updated = 0

    for entry in spatial_data:
        name = entry["name"]
        obj_exists = name in bpy.data.objects
        obj = get_or_create_object(name)
        apply_transforms(obj, entry)
        if obj_exists:
            updated += 1
        else:
            created += 1

    # Sync spatial.json with restored state
    shutil.copy2(snapshot_path, current_path)

    # Save .blend file
    bpy.ops.wm.save_mainfile()

    print(
        f"\n[Vertex] ✅ Restored {len(spatial_data)} object(s) from {os.path.basename(snapshot_path)} "
        f"({created} created, {updated} updated)\n"
    )


# -------------------------------
# 🔹 Main
# -------------------------------
def main():
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    history_dir = os.path.join(base_dir, "data", "history")
    current_path = os.path.join(base_dir, "data", "spatial.json")

    versions = get_versions(history_dir)

    if not versions:
        print("[Vertex] ❌ No version history found.")
        print("         Run serialize.py at least twice to build history.")
        return

    # --- Only 1 version: restore it directly ---
    if len(versions) == 1:
        ver_num, timestamp, is_merge, filepath = versions[0]
        tag = " [MERGE]" if is_merge else ""
        print(f"[Vertex] Only one snapshot available (v{ver_num}{tag} — {timestamp}), restoring...")
        restore_from(filepath, current_path)
        return

    # --- Multiple versions: let user pick ---
    print(f"\n[Vertex] 📋 Available versions ({len(versions)} snapshots):\n")
    print(f"  {'#':<6} {'Type':<10} {'Timestamp':<25}")
    print(f"  {'---':<6} {'---':<10} {'---':<25}")

    for ver_num, timestamp, is_merge, _ in versions:
        tag = "[MERGE]" if is_merge else ""
        print(f"  v{ver_num:<5} {tag:<10} {timestamp}")

    print()
    try:
        choice = input("[Vertex] Enter version number to restore (e.g. 1): ").strip()
        chosen_ver = int(choice)
    except (ValueError, EOFError):
        print("[Vertex] ❌ Invalid input. Aborting.")
        return

    # Find the chosen version
    match = None
    for ver_num, timestamp, is_merge, filepath in versions:
        if ver_num == chosen_ver:
            match = filepath
            break

    if not match:
        print(f"[Vertex] ❌ Version {chosen_ver} not found.")
        return

    restore_from(match, current_path)


if __name__ == "__main__":
    main()