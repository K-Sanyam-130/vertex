"""
serialize.py — Vertex Spatial Serializer

Extracts spatial data (name, location, rotation, scale) from all
objects in the current Blender scene and writes it to data/spatial.json.

Each run also saves a versioned snapshot in data/history/ so any
previous state can be restored later.

Run inside Blender:
    blender --background yourfile.blend --python scripts/serialize.py
Or from Blender's Script Editor / Python console.
"""

import bpy
import json
import os
import shutil
import glob
from datetime import datetime


def collect_spatial_data():
    """Iterate over all scene objects and extract spatial transforms.

    Returns a list of dicts, each containing:
        name  — object name (guaranteed unique)
        loc   — [x, y, z] world location
        rot   — [x, y, z] Euler rotation in radians
        scale — [x, y, z] scale factors

    Raises ValueError if duplicate object names are detected.
    """
    seen_names = set()
    entries = []

    for obj in bpy.data.objects:
        name = obj.name

        # --- Duplicate-name guard ---
        if name in seen_names:
            raise ValueError(
                f"Duplicate object name detected: '{name}'. "
                "Rename the object in Blender before serializing."
            )
        seen_names.add(name)

        entries.append({
            "name": name,
            "loc": [round(v, 6) for v in obj.location],
            "rot": [round(v, 6) for v in obj.rotation_euler],
            "scale": [round(v, 6) for v in obj.scale],
        })

    return entries


def write_json(data, filepath):
    """Write data to a JSON file, creating parent directories if needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_next_version(history_dir):
    """Determine the next version number from existing history files."""
    os.makedirs(history_dir, exist_ok=True)
    existing = glob.glob(os.path.join(history_dir, "v*.json"))
    if not existing:
        return 1
    # Extract version numbers from filenames like v001_2026-03-27_22-50.json
    versions = []
    for f in existing:
        basename = os.path.basename(f)
        try:
            num = int(basename.split("_")[0][1:])  # "v001_..." -> 1
            versions.append(num)
        except (ValueError, IndexError):
            continue
    return max(versions, default=0) + 1


def main():
    """Entry point — serialize spatial data and save to disk."""
    # Resolve paths relative to the .blend file (or cwd as fallback)
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    output_path = os.path.join(base_dir, "data", "spatial.json")
    history_dir = os.path.join(base_dir, "data", "history")

    # Save current spatial.json as a versioned snapshot before overwriting
    if os.path.isfile(output_path):
        version = get_next_version(history_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_name = f"v{version:03d}_{timestamp}.json"
        snapshot_path = os.path.join(history_dir, snapshot_name)

        os.makedirs(history_dir, exist_ok=True)
        shutil.copy2(output_path, snapshot_path)
        print(f"[Vertex] 📸 Saved snapshot: {snapshot_name}")

    # Collect and write current state
    spatial_data = collect_spatial_data()
    write_json(spatial_data, output_path)

    print(f"[Vertex] Serialized {len(spatial_data)} object(s) → {output_path}")


if __name__ == "__main__":
    main()
