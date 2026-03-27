"""
restore.py — Vertex Spatial Restorer (Multi-Version)

Reverts the Blender scene to a previously serialized version.

- If only 1 snapshot exists  → restores it directly
- If multiple snapshots exist → lists them and asks user to pick
- Creates correct object types (camera, light, cone, etc.)
- Preserves attribution metadata (modified_by, modified_at)

Run inside Blender:
    blender --background file.blend --python scripts/restore.py
"""

import bpy
import json
import os
import glob
import shutil


# ══════════════════════════════════════════════════════════════════════════════
# JSON I/O
# ══════════════════════════════════════════════════════════════════════════════

def load_json(filepath):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Spatial data not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# Scene helpers (matching merge.py primitives)
# ══════════════════════════════════════════════════════════════════════════════

_PRIMITIVE_KEYWORDS = [
    ("cylinder",  "mesh.primitive_cylinder_add"),
    ("sphere",    "mesh.primitive_uv_sphere_add"),
    ("ico",       "mesh.primitive_ico_sphere_add"),
    ("plane",     "mesh.primitive_plane_add"),
    ("cone",      "mesh.primitive_cone_add"),
    ("torus",     "mesh.primitive_torus_add"),
    ("circle",    "mesh.primitive_circle_add"),
    ("grid",      "mesh.primitive_grid_add"),
    ("monkey",    "mesh.primitive_monkey_add"),
    ("cube",      "mesh.primitive_cube_add"),
]


def _add_primitive(name):
    """Add correct object type based on the name."""
    key = name.lower()

    # Camera
    if "camera" in key:
        cam_data = bpy.data.cameras.new(name + "_data")
        obj = bpy.data.objects.new(name, cam_data)
        bpy.context.collection.objects.link(obj)
        return obj

    # Light
    if "light" in key:
        light_data = bpy.data.lights.new(name + "_data", type="POINT")
        obj = bpy.data.objects.new(name, light_data)
        bpy.context.collection.objects.link(obj)
        return obj

    # Mesh primitives
    op_path = "mesh.primitive_cube_add"
    for keyword, path in _PRIMITIVE_KEYWORDS:
        if keyword in key:
            op_path = path
            break

    module, op_name = op_path.split(".")
    getattr(getattr(bpy.ops, module), op_name)()
    obj = bpy.context.active_object
    obj.name = name
    if obj.data:
        obj.data.name = name + "_mesh"
    return obj


def get_or_create_object(name):
    """Return existing object or create correct primitive type."""
    obj = bpy.data.objects.get(name)
    if obj is not None:
        return obj, False
    obj = _add_primitive(name)
    return obj, True


def apply_transforms(obj, entry):
    obj.location       = entry["loc"]
    obj.rotation_euler = entry["rot"]
    obj.scale          = entry["scale"]


def cleanup_scene(valid_names):
    """Remove objects not present in JSON data."""
    for obj in list(bpy.data.objects):
        if obj.name not in valid_names:
            bpy.data.objects.remove(obj, do_unlink=True)


# ══════════════════════════════════════════════════════════════════════════════
# Version discovery (matching serialize.py / merge.py format)
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# Restore logic
# ══════════════════════════════════════════════════════════════════════════════

def restore_from(snapshot_path, current_path):
    """Apply a snapshot to the scene and save."""
    spatial_data = load_json(snapshot_path)
    json_names = {entry["name"] for entry in spatial_data}

    cleanup_scene(json_names)

    created = 0
    updated = 0

    for entry in spatial_data:
        name = entry["name"]
        obj, was_created = get_or_create_object(name)
        apply_transforms(obj, entry)
        if was_created:
            created += 1
        else:
            updated += 1

    # Sync spatial.json with restored state
    shutil.copy2(snapshot_path, current_path)

    # Save .blend file
    bpy.ops.wm.save_mainfile()

    # Show attribution info if available
    users = set()
    for entry in spatial_data:
        user = entry.get("modified_by")
        if user and user != "unknown":
            users.add(user)

    print(
        f"\n[Vertex] ✅ Restored {len(spatial_data)} object(s) from {os.path.basename(snapshot_path)} "
        f"({created} created, {updated} updated)"
    )
    if users:
        print(f"         👤 Contributors: {', '.join(sorted(users))}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", type=int, help="Version number to restore")
    
    # In blender, args after '--' are for the script
    import sys
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        argv = []
        
    args, _ = parser.parse_known_args(argv)

    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    history_dir = os.path.join(base_dir, "data", "history")
    current_path = os.path.join(base_dir, "data", "spatial.json")

    versions = get_versions(history_dir)

    if not versions:
        print("[Vertex] ❌ No version history found.")
        print("         Run serialize.py at least twice to build history.")
        return

    # --- Only 1 version: restore it directly ---
    if len(versions) == 1 and not args.version:
        ver_num, timestamp, is_merge, filepath = versions[0]
        tag = " [MERGE]" if is_merge else ""
        print(f"[Vertex] Only one snapshot available (v{ver_num}{tag} — {timestamp}), restoring...")
        restore_from(filepath, current_path)
        return

    if args.version:
        chosen_ver = args.version
    else:
        # --- Multiple versions: let user pick (Interactive) ---
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
            print("[Vertex] ❌ Invalid input or non-interactive environment. Aborting.")
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