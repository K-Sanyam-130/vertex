"""
diff.py — Vertex Visual Diff with Time-Travel ("Ghost Blocks")

Compares the live Blender scene against a previous state and creates
semi-transparent wireframe "ghosts" at old positions.

Usage:
    # Compare against latest spatial.json:
    blender yourfile.blend --python scripts/diff.py

    # Compare against a specific version:
    blender yourfile.blend --python scripts/diff.py -- --version 3

    # Compare against state from ~N minutes ago:
    blender yourfile.blend --python scripts/diff.py -- --ago 10

    # Clear all ghost overlays:
    blender yourfile.blend --python scripts/diff.py -- --clear
"""

import bpy
import json
import os
import sys
import glob
from datetime import datetime, timedelta

# ── Visual style ──────────────────────────────────────────────────────
GHOST_PREFIX = "_ghost_"
COLOR_MOVED   = (0, 1, 0, 0.4)        # green  — object moved
COLOR_REMOVED = (1, 0, 0, 0.4)        # red    — object was removed
COLOR_ADDED   = (1, 1, 0, 0.4)        # yellow — object was added since
POSITION_TOLERANCE = 1e-4


# ── Parse args ────────────────────────────────────────────────────────
def parse_args():
    argv = sys.argv
    if "--" in argv:
        script_args = argv[argv.index("--") + 1:]
    else:
        script_args = []

    version = None
    ago = None
    clear = False

    i = 0
    while i < len(script_args):
        if script_args[i] == "--version" and i + 1 < len(script_args):
            version = int(script_args[i + 1])
            i += 2
        elif script_args[i] == "--ago" and i + 1 < len(script_args):
            ago = int(script_args[i + 1])
            i += 2
        elif script_args[i] == "--clear":
            clear = True
            i += 1
        else:
            i += 1

    return version, ago, clear


# ── Helpers ───────────────────────────────────────────────────────────
def load_json(filepath):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"No data found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def vectors_differ(a, b):
    return any(abs(x - y) > POSITION_TOLERANCE for x, y in zip(a, b))


def has_changed(obj, prev):
    if vectors_differ(list(obj.location), prev["loc"]):
        return True
    if vectors_differ(list(obj.rotation_euler), prev["rot"]):
        return True
    if vectors_differ(list(obj.scale), prev["scale"]):
        return True
    return False


# ── Version discovery ─────────────────────────────────────────────────
def get_versions(history_dir):
    """Return sorted list of (ver_num, timestamp_str, datetime_obj, filepath)."""
    files = sorted(glob.glob(os.path.join(history_dir, "v*.json")))
    entries = []
    for f in files:
        basename = os.path.basename(f)
        try:
            parts = basename.replace(".json", "").split("_", 1)
            ver_num = int(parts[0][1:])
            rest = parts[1] if len(parts) > 1 else ""
            # Strip merge_ prefix for timestamp parsing
            ts_str = rest.replace("merge_", "")
            # Parse timestamp: "2026-03-27_23-15-03" → datetime
            dt = datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
            entries.append((ver_num, rest, dt, f))
        except (ValueError, IndexError):
            continue
    return entries


def find_version_file(history_dir, version):
    """Find history file by version number."""
    for ver_num, _, _, filepath in get_versions(history_dir):
        if ver_num == version:
            return filepath
    return None


def find_closest_ago(history_dir, minutes_ago):
    """Find the snapshot closest to N minutes ago."""
    target_time = datetime.now() - timedelta(minutes=minutes_ago)
    versions = get_versions(history_dir)
    if not versions:
        return None

    best = None
    best_diff = None
    for ver_num, ts_str, dt, filepath in versions:
        diff = abs((dt - target_time).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best = (ver_num, ts_str, filepath)

    return best


# ── Ghost management ──────────────────────────────────────────────────
def clear_ghosts():
    """Remove all existing ghost overlays from the scene."""
    ghosts = [obj for obj in bpy.data.objects if obj.name.startswith(GHOST_PREFIX)]
    for ghost in ghosts:
        bpy.data.objects.remove(ghost, do_unlink=True)
    return len(ghosts)


def embed_tracker(count=2):
    """Embed an auto-run text block to track openings and clean up ghosts."""
    bpy.context.scene["ghost_remaining_opens"] = count

    text_name = "vertex_ghost_tracker.py"
    if text_name in bpy.data.texts:
        text_block = bpy.data.texts[text_name]
        text_block.clear()
    else:
        text_block = bpy.data.texts.new(name=text_name)

    # Must be enabled for auto-run on load
    text_block.use_module = True

    script_content = """import bpy

def cleanup_ghosts():
    scene = bpy.context.scene
    remaining = scene.get('ghost_remaining_opens', 0)
    
    new_remaining = remaining - 1
    scene['ghost_remaining_opens'] = new_remaining
    
    if new_remaining <= 0:
        ghosts = [obj for obj in bpy.data.objects if obj.name.startswith("_ghost_")]
        for g in ghosts:
            bpy.data.objects.remove(g, do_unlink=True)
            
        text_name = 'vertex_ghost_tracker.py'
        if text_name in bpy.data.texts:
            bpy.data.texts.remove(bpy.data.texts[text_name])
            
        try:
            bpy.ops.wm.save_mainfile()
        except:
            pass
    else:
        try:
            bpy.ops.wm.save_mainfile()
        except:
            pass

    return None

@bpy.app.handlers.persistent
def check_ghosts_on_load(dummy):
    if not bpy.app.background:
        bpy.app.timers.register(cleanup_ghosts, first_interval=0.5)

bpy.app.handlers.load_post = [h for h in bpy.app.handlers.load_post if h.__name__ != 'check_ghosts_on_load']
bpy.app.handlers.load_post.append(check_ghosts_on_load)
"""
    text_block.write(script_content)


def save_blend():
    """Save the current blend file if the filepath is set."""
    if bpy.data.filepath:
        try:
            bpy.ops.wm.save_mainfile()
        except:
            pass


def create_ghost(name, entry, color, label=""):
    """Create a wireframe ghost at a previous position."""
    # Use a cube mesh as the ghost shape
    bpy.ops.mesh.primitive_cube_add()
    ghost = bpy.context.active_object
    ghost.name = GHOST_PREFIX + name

    # Place at old transforms
    ghost.location = entry["loc"]
    ghost.rotation_euler = entry["rot"]
    ghost.scale = entry["scale"]

    # Visual style
    ghost.display_type = "WIRE"
    ghost.color = color
    ghost.show_wire = True
    ghost.hide_select = True

    # Add label as custom property (visible in properties panel)
    ghost["ghost_type"] = label
    if "modified_by" in entry:
        ghost["last_modified_by"] = entry["modified_by"]
    if "modified_at" in entry:
        ghost["last_modified_at"] = entry["modified_at"]

    return ghost


# ── Main ──────────────────────────────────────────────────────────────
def main():
    version, ago, clear_flag = parse_args()
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    json_path = os.path.join(base_dir, "data", "spatial.json")
    history_dir = os.path.join(base_dir, "data", "history")

    # Clear mode
    if clear_flag:
        count = clear_ghosts()
        if "vertex_ghost_tracker.py" in bpy.data.texts:
            bpy.data.texts.remove(bpy.data.texts["vertex_ghost_tracker.py"])
        save_blend()
        print(f"[Vertex] 🧹 Removed {count} ghost(s)")
        return

    # Always clear old ghosts first
    clear_ghosts()

    # ── Determine which snapshot to compare against ──
    compare_path = None
    compare_label = ""

    if ago is not None:
        result = find_closest_ago(history_dir, ago)
        if result:
            ver_num, ts_str, filepath = result
            compare_path = filepath
            compare_label = f"~{ago}min ago (v{ver_num})"
            print(f"[Vertex] 👻 Comparing against v{ver_num} ({ts_str}) — ~{ago} minutes ago")
        else:
            print(f"[Vertex] ❌ No snapshots found in history")
            return
    elif version is not None:
        compare_path = find_version_file(history_dir, version)
        if compare_path:
            compare_label = f"v{version}"
            print(f"[Vertex] 👻 Comparing against version {version}")
        else:
            print(f"[Vertex] ❌ Version {version} not found")
            return
    else:
        compare_path = json_path
        compare_label = "last saved"
        print(f"[Vertex] 👻 Comparing against last saved state")

    # ── Load previous state ──
    previous_data = load_json(compare_path)
    previous = {entry["name"]: entry for entry in previous_data}

    changed = []
    removed = []
    added = []

    # Detect changed objects (in scene and in previous)
    for obj in bpy.data.objects:
        if obj.name.startswith(GHOST_PREFIX):
            continue
        prev = previous.get(obj.name)
        if prev and has_changed(obj, prev):
            create_ghost(obj.name, prev, COLOR_MOVED, f"moved since {compare_label}")
            changed.append(obj.name)

    # Detect removed objects (in previous but not in scene)
    scene_names = {obj.name for obj in bpy.data.objects if not obj.name.startswith(GHOST_PREFIX)}
    for name, entry in previous.items():
        if name not in scene_names:
            create_ghost(name, entry, COLOR_REMOVED, f"removed since {compare_label}")
            removed.append(name)

    # Detect added objects (in scene but not in previous)
    for obj in bpy.data.objects:
        if obj.name.startswith(GHOST_PREFIX):
            continue
        if obj.name not in previous:
            added.append(obj.name)

    # ── Summary ──
    total = len(changed) + len(removed) + len(added)
    if total == 0:
        if "vertex_ghost_tracker.py" in bpy.data.texts:
            bpy.data.texts.remove(bpy.data.texts["vertex_ghost_tracker.py"])
        save_blend()
        print(f"[Vertex] ✔ No changes detected since {compare_label}")
    else:
        embed_tracker(count=2)
        save_blend()
        print(f"\n[Vertex] 📊 Diff against {compare_label} — {total} change(s):\n")
        for n in changed:
            user_info = ""
            prev = previous.get(n)
            if prev and "modified_by" in prev:
                user_info = f" (was by {prev['modified_by']})"
            print(f"  🟢 moved:   {n}{user_info}")
        for n in removed:
            user_info = ""
            prev = previous.get(n)
            if prev and "modified_by" in prev:
                user_info = f" (by {prev['modified_by']})"
            print(f"  🔴 removed: {n}{user_info}")
        for n in added:
            print(f"  🟡 added:   {n}")
        print()


if __name__ == "__main__":
    main()
