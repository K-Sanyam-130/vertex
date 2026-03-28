"""
merge.py — Vertex Spatial Merge (Blender entry point)

Merges two JSON files and applies the result to the scene.

Two modes:

  "union"  (default) — additive merge. The scene gets ALL objects from
                        both files. Same-named objects with different
                        transforms are both kept, renamed "Name_A" / "Name_B".

  "3way"             — Git-style merge using spatial.json as the common
                        ancestor. Conflicts resolve to one winner via
                        --strategy ("ours" | "theirs").

Usage:
    # Union merge (default):
    blender --background file.blend --python scripts/merge.py -- data/fileA.json data/fileB.json

    # 3-way merge:
    blender --background file.blend --python scripts/merge.py -- data/fileA.json data/fileB.json --mode 3way

    # 3-way merge with "ours" strategy:
    blender --background file.blend --python scripts/merge.py -- data/fileA.json data/fileB.json --mode 3way --strategy ours
"""

import bpy
import json
import os
import sys
import shutil
import glob
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
# Parse CLI args
# ══════════════════════════════════════════════════════════════════════════════

def parse_args():
    argv = sys.argv
    if "--" in argv:
        script_args = argv[argv.index("--") + 1:]
    else:
        script_args = []

    files = []
    mode = "union"
    strategy = "theirs"

    i = 0
    while i < len(script_args):
        if script_args[i] == "--mode" and i + 1 < len(script_args):
            mode = script_args[i + 1]
            i += 2
        elif script_args[i] == "--strategy" and i + 1 < len(script_args):
            strategy = script_args[i + 1]
            i += 2
        elif not script_args[i].startswith("--"):
            files.append(script_args[i])
            i += 1
        else:
            i += 1

    return files, mode, strategy


# ══════════════════════════════════════════════════════════════════════════════
# Spatial comparison helpers
# ══════════════════════════════════════════════════════════════════════════════

def get_spatial_key(obj):
    """Extract only the spatial fields (loc/rot/scale) for comparison.
    This ignores attribution fields (modified_by, modified_at) so
    objects that differ only in metadata are treated as identical.
    """
    return (
        tuple(obj.get("loc", [])),
        tuple(obj.get("rot", [])),
        tuple(obj.get("scale", [])),
    )


def spatial_equal(a, b):
    """Return True if two entries have the same spatial transforms."""
    return get_spatial_key(a) == get_spatial_key(b)


def stamp_entry(entry, source_label):
    """Add/update attribution metadata on an entry after merge."""
    now = datetime.now().isoformat(timespec="seconds")
    entry = dict(entry)  # shallow copy
    entry.setdefault("modified_by", "merge")
    entry.setdefault("modified_at", now)
    entry["merged_from"] = source_label
    return entry


# ══════════════════════════════════════════════════════════════════════════════
# Merge logic (pure Python — no bpy)
# ══════════════════════════════════════════════════════════════════════════════

def merge_spatial_union(a, b, label_a="A", label_b="B"):
    """
    Additive union merge — result contains ALL objects from A and B.

    Rules
    -----
    • Only in A              → keep as-is
    • Only in B              → keep as-is
    • Same name, same spatial → keep once (de-duplicated)
    • Same name, diff spatial → keep BOTH, renamed with suffixes
    """
    a_dict = {o["name"]: o for o in a}
    b_dict = {o["name"]: o for o in b}

    merged    = []
    conflicts = []
    suffix_a  = f"_{label_a}"
    suffix_b  = f"_{label_b}"

    for name in sorted(set(a_dict) | set(b_dict)):
        a_obj = a_dict.get(name)
        b_obj = b_dict.get(name)

        if a_obj is None:
            merged.append(stamp_entry(b_obj, label_b))
        elif b_obj is None:
            merged.append(stamp_entry(a_obj, label_a))
        elif spatial_equal(a_obj, b_obj):
            # Same spatial data — keep one, preserve best attribution
            kept = dict(a_obj)
            # Prefer the entry that has real attribution over "unknown"
            if a_obj.get("modified_by") in (None, "unknown") and b_obj.get("modified_by") not in (None, "unknown"):
                kept["modified_by"] = b_obj["modified_by"]
                kept["modified_at"] = b_obj.get("modified_at", kept.get("modified_at"))
            merged.append(kept)
        else:
            conflicts.append({"name": name, "A": a_obj, "B": b_obj})
            merged.append(stamp_entry({**a_obj, "name": name + suffix_a}, label_a))
            merged.append(stamp_entry({**b_obj, "name": name + suffix_b}, label_b))

    return merged, conflicts


def merge_spatial_3way(base, a, b, strategy="theirs"):
    """
    Git-style 3-way merge relative to a common ancestor (base).

    Cases
    -----
    1  Unchanged in both      → keep BASE
    2  Changed in A only      → take A
    3  Changed in B only      → take B
    4  Changed identically    → take A (same as B)
    5  Changed differently    → CONFLICT → resolve via strategy
    """
    base_dict = {o["name"]: o for o in base}
    a_dict    = {o["name"]: o for o in a}
    b_dict    = {o["name"]: o for o in b}

    merged    = []
    conflicts = []

    for name in sorted(set(base_dict) | set(a_dict) | set(b_dict)):
        base_obj = base_dict.get(name)
        a_obj    = a_dict.get(name)
        b_obj    = b_dict.get(name)

        a_same = spatial_equal(a_obj, base_obj) if (a_obj and base_obj) else (a_obj is None and base_obj is None)
        b_same = spatial_equal(b_obj, base_obj) if (b_obj and base_obj) else (b_obj is None and base_obj is None)

        if a_same and b_same:
            # Unchanged in both → keep base
            if base_obj is not None:
                merged.append(base_obj)
        elif not a_same and b_same:
            # Changed in A only → take A
            if a_obj is not None:
                merged.append(a_obj)
        elif not b_same and a_same:
            # Changed in B only → take B
            if b_obj is not None:
                merged.append(b_obj)
        elif a_obj and b_obj and spatial_equal(a_obj, b_obj):
            # Changed identically → take A
            merged.append(a_obj)
        else:
            # True conflict
            resolved = b_obj if strategy == "theirs" else a_obj
            conflicts.append({
                "name": name, "base": base_obj,
                "A": a_obj, "B": b_obj,
                "resolved": resolved, "strategy": strategy,
            })
            if resolved is not None:
                merged.append(resolved)

    return merged, conflicts


# ══════════════════════════════════════════════════════════════════════════════
# JSON I/O
# ══════════════════════════════════════════════════════════════════════════════

def load_json(filepath):
    if not os.path.isfile(filepath):
        print(f"[Vertex] ❌ Not found: {filepath}")
        sys.exit(1)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        print(f"[Vertex] ❌ Encoding error: '{os.path.basename(filepath)}' contains binary data.")
        print("         Did you pass a .blend file? Please pass .json files created by the Serialize tool.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[Vertex] ❌ Invalid JSON in '{os.path.basename(filepath)}': {e}")
        sys.exit(1)


def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# Version history (shared logic with serialize.py)
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# Blender scene helpers (shared with restore.py)
# ══════════════════════════════════════════════════════════════════════════════

# Maps name keywords → the bpy.ops primitive that creates a visible mesh.
_PRIMITIVE_KEYWORDS = [
    ("camera",    None),  # skip — cameras are special
    ("light",     None),  # skip — lights are special
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
    """Add a visible mesh primitive based on the object name."""
    key = name.lower()
    op_path = "mesh.primitive_cube_add"   # default fallback
    for keyword, path in _PRIMITIVE_KEYWORDS:
        if path is None:
            continue  # skip camera/light — handled separately
        if keyword in key:
            op_path = path
            break

    # Check for camera/light keywords first
    if "camera" in key:
        cam_data = bpy.data.cameras.new(name + "_data")
        obj = bpy.data.objects.new(name, cam_data)
        bpy.context.collection.objects.link(obj)
        return obj
    elif "light" in key:
        light_data = bpy.data.lights.new(name + "_data", type="POINT")
        obj = bpy.data.objects.new(name, light_data)
        bpy.context.collection.objects.link(obj)
        return obj

    module, op_name = op_path.split(".")
    getattr(getattr(bpy.ops, module), op_name)()
    obj = bpy.context.active_object
    obj.name = name
    if obj.data:
        obj.data.name = name + "_mesh"
    return obj


def get_or_create_object(name):
    """Return an existing scene object or create a visible primitive for it."""
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
    """Remove objects not in the merged result."""
    for obj in list(bpy.data.objects):
        if obj.name not in valid_names:
            bpy.data.objects.remove(obj, do_unlink=True)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    files, mode, strategy = parse_args()

    if len(files) < 2:
        print("[Vertex] ❌ Provide at least 2 JSON files to merge.")
        print("         Usage: blender --background file.blend --python scripts/merge.py -- fileA.json fileB.json")
        print("         Flags: --mode union|3way  --strategy ours|theirs")
        return

    base_dir = (
        os.path.dirname(bpy.data.filepath)
        if bpy.data.filepath else os.getcwd()
    )
    data_dir    = os.path.join(base_dir, "data")
    history_dir = os.path.join(data_dir, "history")
    output_path = os.path.join(data_dir, "spatial.json")

    # Resolve file paths relative to base_dir
    import subprocess
    resolved_files = []
    for f in files:
        f_path = f if os.path.isabs(f) else os.path.join(base_dir, f)
        
        # Auto-serialize .blend files on the fly
        if f_path.lower().endswith(".blend"):
            print(f"[Vertex] ⚙ Auto-serializing {os.path.basename(f_path)}...")
            script_path = os.path.join(base_dir, "scripts", "serialize.py")
            cmd = [
                bpy.app.binary_path, 
                "--background", 
                "--factory-startup", 
                f_path, 
                "--python", 
                script_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"[Vertex] ❌ Failed to auto-serialize {os.path.basename(f_path)}")
                print(res.stdout)
                print(res.stderr)
                sys.exit(1)
            
            # Use the generated JSON file instead
            blend_name = os.path.splitext(os.path.basename(f_path))[0]
            f_path = os.path.join(data_dir, f"{blend_name}.json")
            
        resolved_files.append(f_path)

    # Derive labels from filenames for attribution
    label_a = os.path.splitext(os.path.basename(resolved_files[0]))[0]
    label_b = os.path.splitext(os.path.basename(resolved_files[1]))[0]

    # ── Pre-merge snapshot ──
    if os.path.isfile(output_path):
        version = get_next_version(history_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_name = f"v{version:03d}_merge_{timestamp}.json"
        snapshot_path = os.path.join(history_dir, snapshot_name)
        os.makedirs(history_dir, exist_ok=True)
        shutil.copy2(output_path, snapshot_path)
        print(f"[Vertex] 📸 Pre-merge snapshot: {snapshot_name}")

        # Enforce history limit
        pattern = os.path.join(history_dir, f"v*_merge_*.json")
        existing_files = sorted(glob.glob(pattern))

        if len(existing_files) > 10:
            excess = len(existing_files) - 10
            for i in range(excess):
                try:
                    os.remove(existing_files[i])
                    print(f"[Vertex] 🗑 Cleaned up old merge snapshot: {os.path.basename(existing_files[i])}")
                except OSError:
                    pass

    print(f"[Vertex] Mode: {mode.upper()}")
    print(f"[Vertex] Files: {label_a} + {label_b}")

    a = load_json(resolved_files[0])
    b = load_json(resolved_files[1])

    if mode == "union":
        merged, conflicts = merge_spatial_union(a, b, label_a, label_b)
        if conflicts:
            print(f"[Vertex] ℹ  {len(conflicts)} object(s) renamed (same name, different data):")
            for c in conflicts:
                print(f"         • '{c['name']}' → '{c['name']}_{label_a}'  +  '{c['name']}_{label_b}'")
        else:
            print("[Vertex] ✔ All objects merged without renaming.")

    elif mode == "3way":
        base = load_json(output_path)
        merged, conflicts = merge_spatial_3way(base, a, b, strategy=strategy)
        if conflicts:
            print(f"[Vertex] ⚠  {len(conflicts)} conflict(s) resolved via '{strategy}':")
            for c in conflicts:
                print(f"         • '{c['name']}'")
            save_json(conflicts, os.path.join(data_dir, "conflicts.json"))
            print("[Vertex] Conflict details → data/conflicts.json")
        else:
            print("[Vertex] ✔ No conflicts.")
    else:
        print(f"[Vertex] ❌ Unknown mode: {mode}. Use 'union' or '3way'.")
        return

    # ── Apply merged result to scene ──
    json_names = {entry["name"] for entry in merged}
    cleanup_scene(json_names)

    created = updated = 0
    for entry in merged:
        obj, was_created = get_or_create_object(entry["name"])
        apply_transforms(obj, entry)
        if was_created:
            created += 1
        else:
            updated += 1

    # ── Save everything ──
    save_json(merged, output_path)
    bpy.ops.wm.save_mainfile()

    print(
        f"\n[Vertex] ✅ Merged {len(merged)} object(s) "
        f"({created} created, {updated} updated)"
    )
    print(f"         Output → {output_path}\n")


if __name__ == "__main__":
    main()
