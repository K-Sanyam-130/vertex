"""
diff.py — Vertex Visual Diff ("Ghosts")

Compares the live Blender scene against the last saved data/spatial.json.
Changed or removed objects are visualized as semi-transparent green
wireframe "ghosts" so artists can see exactly what moved.

Run inside Blender:
    blender yourfile.blend --python scripts/diff.py
Or from Blender's Script Editor / Python console.
"""

import bpy
import json
import os
import math

# Visual style for ghost overlays
GHOST_PREFIX = "_ghost_"
GHOST_COLOR = (0, 1, 0, 0.5)          # green, 50 % opacity
GHOST_DISPLAY = "WIRE"
POSITION_TOLERANCE = 1e-4              # ignore floating-point noise


# ── Helpers ──────────────────────────────────────────────────────────────

def _load_previous_state(filepath):
    """Load the last serialized spatial.json."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"No previous state found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return {entry["name"]: entry for entry in json.load(f)}


def _vectors_differ(a, b):
    """Return True if two 3-component lists differ beyond tolerance."""
    return any(abs(x - y) > POSITION_TOLERANCE for x, y in zip(a, b))


def _has_changed(obj, prev):
    """Compare a live object's transforms against its previous JSON entry."""
    if _vectors_differ(list(obj.location), prev["loc"]):
        return True
    if _vectors_differ(list(obj.rotation_euler), prev["rot"]):
        return True
    if _vectors_differ(list(obj.scale), prev["scale"]):
        return True
    return False


# ── Ghost management ────────────────────────────────────────────────────

def clear_ghosts():
    """Remove all existing ghost overlays from the scene."""
    ghosts = [obj for obj in bpy.data.objects if obj.name.startswith(GHOST_PREFIX)]
    for ghost in ghosts:
        bpy.data.objects.remove(ghost, do_unlink=True)


def _create_ghost(name, entry):
    """Create a wireframe ghost at the *previous* position of an object."""
    mesh = bpy.data.meshes.new(GHOST_PREFIX + name + "_mesh")
    ghost = bpy.data.objects.new(GHOST_PREFIX + name, mesh)
    bpy.context.collection.objects.link(ghost)

    # Place ghost at the old transforms
    ghost.location = entry["loc"]
    ghost.rotation_euler = entry["rot"]
    ghost.scale = entry["scale"]

    # Visual style — wireframe + color
    ghost.display_type = GHOST_DISPLAY
    ghost.color = GHOST_COLOR
    ghost.show_wire = True

    # Prevent accidental selection / editing
    ghost.hide_select = True

    return ghost


# ── Main ────────────────────────────────────────────────────────────────

def main():
    """Entry point — diff current scene against spatial.json."""
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    json_path = os.path.join(base_dir, "data", "spatial.json")

    previous = _load_previous_state(json_path)

    # Clean up any ghosts from a previous diff
    clear_ghosts()

    changed = []
    removed = []

    # Detect changed objects
    for obj in bpy.data.objects:
        if obj.name.startswith(GHOST_PREFIX):
            continue
        prev = previous.get(obj.name)
        if prev and _has_changed(obj, prev):
            _create_ghost(obj.name, prev)
            changed.append(obj.name)

    # Detect removed objects (in JSON but no longer in scene)
    scene_names = {obj.name for obj in bpy.data.objects if not obj.name.startswith(GHOST_PREFIX)}
    for name, entry in previous.items():
        if name not in scene_names:
            _create_ghost(name, entry)
            removed.append(name)

    # Summary
    total = len(changed) + len(removed)
    if total == 0:
        print("[Vertex] Diff — no spatial changes detected.")
    else:
        print(f"[Vertex] Diff — {total} change(s) found:")
        for n in changed:
            print(f"  ✎ modified: {n}")
        for n in removed:
            print(f"  ✖ removed:  {n}")


if __name__ == "__main__":
    main()
