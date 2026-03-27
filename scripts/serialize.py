"""
serialize.py — Vertex Spatial Serializer

Extracts spatial data (name, location, rotation, scale) from all
objects in the current Blender scene and writes it to data/spatial.json.

Each run saves a versioned snapshot in data/history/.
Supports user attribution: --user <name> to tag who made changes.

Run inside Blender:
    blender --background yourfile.blend --python scripts/serialize.py
    blender --background yourfile.blend --python scripts/serialize.py -- --user sanyam
"""

import bpy
import json
import os
import sys
import shutil
import glob
from datetime import datetime


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
    i = 0
    while i < len(script_args):
        if script_args[i] == "--user" and i + 1 < len(script_args):
            user = script_args[i + 1]
            i += 2
        else:
            i += 1
    return user


# ───────────────────────────────────
# 🔹 Load previous state for attribution
# ───────────────────────────────────
def load_previous(filepath):
    """Load previous spatial.json to preserve attribution for unchanged objects."""
    if not os.path.isfile(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {entry["name"]: entry for entry in data}


def transforms_changed(prev, loc, rot, scale):
    """Check if transforms differ from previous entry."""
    if prev["loc"] != loc or prev["rot"] != rot or prev["scale"] != scale:
        return True
    return False


# ───────────────────────────────────
# 🔹 Collect spatial data
# ───────────────────────────────────
def collect_spatial_data(user, previous):
    """Iterate over all scene objects and extract spatial transforms.

    - Tags each object with modified_by and modified_at
    - Preserves previous attribution if object hasn't changed
    """
    seen_names = set()
    entries = []
    now = datetime.now().isoformat(timespec="seconds")

    for obj in bpy.data.objects:
        name = obj.name

        if name in seen_names:
            raise ValueError(
                f"Duplicate object name detected: '{name}'. "
                "Rename the object in Blender before serializing."
            )
        seen_names.add(name)

        loc = [round(v, 6) for v in obj.location]
        rot = [round(v, 6) for v in obj.rotation_euler]
        scale = [round(v, 6) for v in obj.scale]

        # Check if this object existed before and hasn't changed
        prev = previous.get(name)
        if prev and not transforms_changed(prev, loc, rot, scale):
            # Preserve old attribution
            modified_by = prev.get("modified_by", user)
            modified_at = prev.get("modified_at", now)
        else:
            # New or changed — tag with current user
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


def main():
    user = parse_args()

    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    output_path = os.path.join(base_dir, "data", "spatial.json")
    history_dir = os.path.join(base_dir, "data", "history")

    # Load previous state for attribution tracking
    previous = load_previous(output_path)

    # Save current spatial.json as versioned snapshot before overwriting
    if os.path.isfile(output_path):
        version = get_next_version(history_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_name = f"v{version:03d}_{timestamp}.json"
        snapshot_path = os.path.join(history_dir, snapshot_name)

        os.makedirs(history_dir, exist_ok=True)
        shutil.copy2(output_path, snapshot_path)
        print(f"[Vertex] 📸 Saved snapshot: {snapshot_name}")

    # Collect and write current state
    spatial_data = collect_spatial_data(user, previous)
    write_json(spatial_data, output_path)

    # Also save a copy named after the blend file (for easy merging)
    blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0] if bpy.data.filepath else None
    if blend_name:
        named_copy = os.path.join(base_dir, "data", f"{blend_name}.json")
        write_json(spatial_data, named_copy)
        print(f"[Vertex] Serialized {len(spatial_data)} object(s) → {output_path}")
        print(f"[Vertex] 📄 Blend copy → data/{blend_name}.json")
    else:
        print(f"[Vertex] Serialized {len(spatial_data)} object(s) → {output_path}")

    print(f"[Vertex] 👤 User: {user}")


if __name__ == "__main__":
    main()
