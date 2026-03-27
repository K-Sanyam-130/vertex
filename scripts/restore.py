"""
restore.py — Vertex Spatial Restorer (Improved)

Reconstructs a Blender scene from data/spatial.json.

Features:
✔ Deletes objects not present in JSON
✔ Creates visible objects (cube placeholder)
✔ Updates existing objects safely
✔ Deterministic behavior for demo
"""

import bpy
import json
import os


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

    # Create visible placeholder (cube)
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
# 🔹 Main
# -------------------------------
def main():
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    input_path = os.path.join(base_dir, "data", "spatial.json")

    spatial_data = load_json(input_path)

    json_names = {entry["name"] for entry in spatial_data}

    # 🔥 Step 1: Clean scene
    cleanup_scene(json_names)

    created = 0
    updated = 0

    # 🔥 Step 2: Restore objects
    for entry in spatial_data:
        name = entry["name"]

        obj_exists = name in bpy.data.objects
        obj = get_or_create_object(name)

        apply_transforms(obj, entry)

        if obj_exists:
            updated += 1
        else:
            created += 1

    print(
        f"[Vertex] Restored {len(spatial_data)} object(s) "
        f"({created} created, {updated} updated) ← {input_path}"
    )


if __name__ == "__main__":
    main()