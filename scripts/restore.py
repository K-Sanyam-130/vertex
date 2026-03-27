"""
restore.py — Vertex Spatial Restorer

Reconstructs a Blender scene from data/spatial.json.
Missing objects are created as empty meshes; existing objects
have their transforms updated in place. No duplicates are created.

Run inside Blender:
    blender --background --python scripts/restore.py
Or from Blender's Script Editor / Python console.
"""

import bpy
import json
import os


def load_json(filepath):
    """Read and parse a JSON file. Raises FileNotFoundError if missing."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Spatial data not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_or_create_object(name):
    """Return the scene object with the given name, creating it if missing.

    New objects are created as empty meshes so they act as lightweight
    placeholders that still carry full spatial transforms.
    """
    obj = bpy.data.objects.get(name)
    if obj is not None:
        return obj

    # Create a new empty mesh and link it to the active scene
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def apply_transforms(obj, entry):
    """Set location, rotation, and scale on a Blender object from a dict."""
    obj.location = entry["loc"]
    obj.rotation_euler = entry["rot"]
    obj.scale = entry["scale"]


def main():
    """Entry point — load spatial.json and rebuild the scene."""
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    input_path = os.path.join(base_dir, "data", "spatial.json")

    spatial_data = load_json(input_path)

    created = 0
    updated = 0

    for entry in spatial_data:
        name = entry["name"]
        already_exists = name in bpy.data.objects

        obj = get_or_create_object(name)
        apply_transforms(obj, entry)

        if already_exists:
            updated += 1
        else:
            created += 1

    print(
        f"[Vertex] Restored {len(spatial_data)} object(s) "
        f"({created} created, {updated} updated) ← {input_path}"
    )


if __name__ == "__main__":
    main()
