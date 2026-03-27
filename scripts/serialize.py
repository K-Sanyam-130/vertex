"""
serialize.py — Vertex Full Scene Serializer

Extracts scene data from the current Blender file and writes domain-specific
JSON files to data/:

    spatial.json    — object transforms (name, location, rotation, scale)
    lighting.json   — light datablocks (type, energy, color, shadow, spot)
    materials.json  — Principled BSDF properties + texture paths
    modifiers.json  — per-object modifier stacks with type-specific settings

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


# ══════════════════════════════════════════════════════════════════════════════
# CLI Argument Parsing
# ══════════════════════════════════════════════════════════════════════════════

def parse_args():
    """Extract --user flag from Blender CLI arguments."""
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


# ══════════════════════════════════════════════════════════════════════════════
# Shared Utilities
# ══════════════════════════════════════════════════════════════════════════════

def write_json(data, filepath):
    """Write data to JSON with 4-space indentation and deterministic key order."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, sort_keys=True, ensure_ascii=False)


def round_color(color, decimals=6):
    """Round and clamp an RGB(A) color to [0, 1] range.

    Args:
        color: Iterable of float values (RGB or RGBA).
        decimals: Number of decimal places to round to.

    Returns:
        List of 3 floats (RGB only, alpha stripped if present).
    """
    return [round(max(0.0, min(1.0, c)), decimals) for c in color[:3]]


def round_vector(vec, decimals=6):
    """Round a numeric vector (e.g. location, offset) to N decimals."""
    return [round(v, decimals) for v in vec]


def get_next_version(history_dir):
    """Return the next available version number for snapshot files."""
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
# Attribution Helpers
# ══════════════════════════════════════════════════════════════════════════════

def load_previous(filepath):
    """Load previous JSON state to preserve attribution for unchanged entries.

    Returns a dict keyed by the entry's primary identifier (name/object_name/
    material_name depending on domain).
    """
    if not os.path.isfile(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
    # Auto-detect the key field
    result = {}
    for entry in data:
        for key_field in ("name", "object_name", "material_name"):
            if key_field in entry:
                result[entry[key_field]] = entry
                break
    return result


def transforms_changed(prev, loc, rot, scale):
    """Check if spatial transforms differ from previous entry."""
    if prev["loc"] != loc or prev["rot"] != rot or prev["scale"] != scale:
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 1: Spatial Serialization (Original)
# ══════════════════════════════════════════════════════════════════════════════

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

        loc = round_vector(obj.location)
        rot = round_vector(obj.rotation_euler)
        scale = round_vector(obj.scale)

        # Check if this object existed before and hasn't changed
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


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 2: Lighting Serialization
# ══════════════════════════════════════════════════════════════════════════════

def serialize_lights():
    """Serialize all light datablocks from bpy.data.lights.

    Extracts light properties (NOT object transforms — those live in spatial.json).
    Spot-specific fields are only included for SPOT lights.

    Returns:
        list[dict]: Serialized light entries.
    """
    entries = []

    for light in bpy.data.lights:
        entry = {
            "name": light.name,
            "type": light.type,
            "energy": round(light.energy, 6),
            "color": round_color(light.color),
            "shadow": {
                "use_shadow": light.use_shadow,
                "softness": round(light.shadow_soft_size, 6),
            },
        }

        # Spot-specific properties — only include for SPOT type
        if light.type == "SPOT":
            entry["spot"] = {
                "size": round(light.spot_size, 6),
                "blend": round(light.spot_blend, 6),
            }

        entries.append(entry)

    # Sort by name for deterministic output
    entries.sort(key=lambda e: e["name"])
    return entries


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 3: Material Serialization (Principled BSDF)
# ══════════════════════════════════════════════════════════════════════════════

def _find_principled_bsdf(node_tree):
    """Locate the Principled BSDF node in a material's node tree.

    Args:
        node_tree: A bpy.types.ShaderNodeTree.

    Returns:
        The Principled BSDF node, or None if not found.
    """
    if node_tree is None:
        return None
    for node in node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def _get_input_value(bsdf_node, input_name, default=None):
    """Safely extract a default_value from a Principled BSDF input socket.

    Args:
        bsdf_node: The Principled BSDF node.
        input_name: Name of the input socket (e.g. "Base Color").
        default: Fallback value if the input doesn't exist.

    Returns:
        The socket's default_value, or the fallback.
    """
    inp = bsdf_node.inputs.get(input_name)
    if inp is None:
        return default
    try:
        return inp.default_value
    except Exception:
        return default


def _collect_texture_paths(node_tree):
    """Find all image texture file paths connected in a material's node tree.

    Args:
        node_tree: A bpy.types.ShaderNodeTree.

    Returns:
        list[str]: List of texture file paths (deduplicated, sorted).
    """
    paths = set()
    if node_tree is None:
        return []
    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image:
            filepath = node.image.filepath
            if filepath:
                # Normalize path separators
                paths.add(filepath.replace("\\", "/"))
    return sorted(paths)


def _extract_emission(bsdf_node):
    """Extract emission color and strength from a Principled BSDF node.

    Handles both Blender 3.x (separate Emission / Emission Strength sockets)
    and Blender 4.x (where "Emission Color" replaced "Emission").

    Returns:
        dict: {"color": [r, g, b], "strength": float}
    """
    # Try Blender 4.x name first, fall back to 3.x
    emission_color = _get_input_value(bsdf_node, "Emission Color")
    if emission_color is None:
        emission_color = _get_input_value(bsdf_node, "Emission")

    emission_strength = _get_input_value(bsdf_node, "Emission Strength")

    color = round_color(emission_color) if emission_color else [0.0, 0.0, 0.0]
    strength = round(float(emission_strength), 6) if emission_strength is not None else 0.0

    return {
        "color": color,
        "strength": strength,
    }


def serialize_materials():
    """Serialize materials from all mesh objects that have an active material.

    Traverses each object's active material node tree to locate the
    Principled BSDF node and extract its input values.

    Returns:
        list[dict]: Serialized material entries.
    """
    entries = []
    seen_materials = set()

    for obj in bpy.data.objects:
        # Only process mesh objects with materials
        if obj.type != "MESH":
            continue
        mat = obj.active_material
        if mat is None:
            continue
        # Avoid duplicating the same material
        if mat.name in seen_materials:
            continue
        seen_materials.add(mat.name)

        # Must have a node tree with nodes
        if not mat.use_nodes or mat.node_tree is None:
            print(f"[Vertex] ⚠ Material '{mat.name}' has no node tree, skipping.")
            continue

        bsdf = _find_principled_bsdf(mat.node_tree)
        if bsdf is None:
            print(f"[Vertex] ⚠ Material '{mat.name}' has no Principled BSDF node, skipping.")
            continue

        # Extract base color (RGBA → RGB)
        base_color_raw = _get_input_value(bsdf, "Base Color")
        base_color = round_color(base_color_raw) if base_color_raw else [0.8, 0.8, 0.8]

        # Extract scalar inputs with safe fallbacks
        metallic = _get_input_value(bsdf, "Metallic")
        roughness = _get_input_value(bsdf, "Roughness")
        # Blender 4.x removed "Specular" in favor of "Specular IOR Level"
        specular = _get_input_value(bsdf, "Specular IOR Level")
        if specular is None:
            specular = _get_input_value(bsdf, "Specular")
        ior = _get_input_value(bsdf, "IOR")
        alpha = _get_input_value(bsdf, "Alpha")

        entry = {
            "material_name": mat.name,
            "base_color": base_color,
            "metallic": round(float(metallic), 6) if metallic is not None else 0.0,
            "roughness": round(float(roughness), 6) if roughness is not None else 0.5,
            "specular": round(float(specular), 6) if specular is not None else 0.5,
            "ior": round(float(ior), 6) if ior is not None else 1.45,
            "emission": _extract_emission(bsdf),
            "alpha": round(float(alpha), 6) if alpha is not None else 1.0,
            "textures": _collect_texture_paths(mat.node_tree),
        }

        entries.append(entry)

    # Sort by material name for deterministic output
    entries.sort(key=lambda e: e["material_name"])
    return entries


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 4: Modifier Serialization
# ══════════════════════════════════════════════════════════════════════════════

# Map of modifier types to their attribute extractors.
# Each entry is (modifier_type_string, extraction_function).
# The extraction function receives the modifier and returns a dict of settings.

def _extract_subsurf(mod):
    """Extract Subdivision Surface modifier settings."""
    return {
        "type": "SUBSURF",
        "levels_viewport": mod.levels,
        "levels_render": mod.render_levels,
    }


def _extract_array(mod):
    """Extract Array modifier settings."""
    offset = [0.0, 0.0, 0.0]
    if mod.use_relative_offset:
        offset = round_vector(mod.relative_offset_displace)
    return {
        "type": "ARRAY",
        "count": mod.count,
        "relative_offset": offset,
    }


def _extract_boolean(mod):
    """Extract Boolean modifier settings."""
    target_name = mod.object.name if mod.object else None
    return {
        "type": "BOOLEAN",
        "operation": mod.operation,
        "target": target_name,
    }


def _extract_mirror(mod):
    """Extract Mirror modifier settings."""
    return {
        "type": "MIRROR",
        "use_axis": [mod.use_axis[0], mod.use_axis[1], mod.use_axis[2]],
        "use_bisect_axis": [
            mod.use_bisect_axis[0],
            mod.use_bisect_axis[1],
            mod.use_bisect_axis[2],
        ],
        "mirror_object": mod.mirror_object.name if mod.mirror_object else None,
    }


def _extract_solidify(mod):
    """Extract Solidify modifier settings."""
    return {
        "type": "SOLIDIFY",
        "thickness": round(mod.thickness, 6),
        "offset": round(mod.offset, 6),
        "use_even_offset": mod.use_even_offset,
    }


def _extract_bevel(mod):
    """Extract Bevel modifier settings."""
    return {
        "type": "BEVEL",
        "width": round(mod.width, 6),
        "segments": mod.segments,
        "limit_method": mod.limit_method,
    }


def _extract_edge_split(mod):
    """Extract Edge Split modifier settings."""
    return {
        "type": "EDGE_SPLIT",
        "split_angle": round(mod.split_angle, 6),
        "use_edge_angle": mod.use_edge_angle,
        "use_edge_sharp": mod.use_edge_sharp,
    }


def _extract_decimate(mod):
    """Extract Decimate modifier settings."""
    entry = {
        "type": "DECIMATE",
        "decimate_type": mod.decimate_type,
    }
    if mod.decimate_type == "COLLAPSE":
        entry["ratio"] = round(mod.ratio, 6)
    elif mod.decimate_type == "UN_SUBDIVIDE":
        entry["iterations"] = mod.iterations
    elif mod.decimate_type == "DISSOLVE":
        entry["angle_limit"] = round(mod.angle_limit, 6)
    return entry


def _extract_wireframe(mod):
    """Extract Wireframe modifier settings."""
    return {
        "type": "WIREFRAME",
        "thickness": round(mod.thickness, 6),
        "use_even_offset": mod.use_even_offset,
        "use_replace": mod.use_replace,
    }


def _extract_screw(mod):
    """Extract Screw modifier settings."""
    return {
        "type": "SCREW",
        "angle": round(mod.angle, 6),
        "steps": mod.steps,
        "render_steps": mod.render_steps,
        "screw_offset": round(mod.screw_offset, 6),
        "axis": mod.axis,
    }


# Registry of supported modifier extractors
_MODIFIER_EXTRACTORS = {
    "SUBSURF": _extract_subsurf,
    "ARRAY": _extract_array,
    "BOOLEAN": _extract_boolean,
    "MIRROR": _extract_mirror,
    "SOLIDIFY": _extract_solidify,
    "BEVEL": _extract_bevel,
    "EDGE_SPLIT": _extract_edge_split,
    "DECIMATE": _extract_decimate,
    "WIREFRAME": _extract_wireframe,
    "SCREW": _extract_screw,
}


def _serialize_single_modifier(mod):
    """Serialize a single modifier using the registered extractor.

    Args:
        mod: A bpy.types.Modifier.

    Returns:
        dict or None: Serialized modifier data, or None if unsupported.
    """
    extractor = _MODIFIER_EXTRACTORS.get(mod.type)
    if extractor is None:
        print(f"[Vertex] ⚠ Unsupported modifier type '{mod.type}' on '{mod.name}', skipping.")
        return None
    try:
        return extractor(mod)
    except Exception as e:
        print(f"[Vertex] ⚠ Error serializing modifier '{mod.name}' ({mod.type}): {e}")
        return None


def serialize_modifiers():
    """Serialize modifier stacks for all mesh objects.

    Modifier order is preserved (first in list = first applied).
    Unsupported modifier types are skipped with a warning.

    Returns:
        list[dict]: Per-object modifier stack entries.
    """
    entries = []

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if len(obj.modifiers) == 0:
            continue

        mod_list = []
        for mod in obj.modifiers:
            serialized = _serialize_single_modifier(mod)
            if serialized is not None:
                mod_list.append(serialized)

        if mod_list:
            entries.append({
                "object_name": obj.name,
                "modifiers": mod_list,
            })

    # Sort by object name for deterministic output
    entries.sort(key=lambda e: e["object_name"])
    return entries


# ══════════════════════════════════════════════════════════════════════════════
# Snapshot & Version Management
# ══════════════════════════════════════════════════════════════════════════════

def save_snapshot(output_path, history_dir, domain_prefix="spatial"):
    """Save the current state file as a versioned snapshot before overwriting.

    Args:
        output_path: Path to the current domain JSON file.
        history_dir: Directory for versioned snapshots.
        domain_prefix: Prefix for the snapshot filename (e.g. "spatial", "lighting").
    """
    if not os.path.isfile(output_path):
        return

    version = get_next_version(history_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_name = f"v{version:03d}_{domain_prefix}_{timestamp}.json"
    snapshot_path = os.path.join(history_dir, snapshot_name)

    os.makedirs(history_dir, exist_ok=True)
    shutil.copy2(output_path, snapshot_path)
    print(f"[Vertex] 📸 Saved {domain_prefix} snapshot: {snapshot_name}")


# ══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    user = parse_args()

    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    data_dir = os.path.join(base_dir, "data")
    history_dir = os.path.join(data_dir, "history")

    # ── Spatial serialization ──────────────────────────────────────────
    spatial_path = os.path.join(data_dir, "spatial.json")
    previous_spatial = load_previous(spatial_path)
    save_snapshot(spatial_path, history_dir, "spatial")

    spatial_data = collect_spatial_data(user, previous_spatial)
    write_json(spatial_data, spatial_path)
    print(f"[Vertex] ✅ Serialized {len(spatial_data)} object(s) → spatial.json")

    # Also save a copy named after the blend file (for merging)
    blend_name = (
        os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        if bpy.data.filepath else None
    )
    if blend_name:
        named_copy = os.path.join(data_dir, f"{blend_name}.json")
        write_json(spatial_data, named_copy)
        print(f"[Vertex] 📄 Blend copy → data/{blend_name}.json")

    # ── Lighting serialization ─────────────────────────────────────────
    lighting_path = os.path.join(data_dir, "lighting.json")
    save_snapshot(lighting_path, history_dir, "lighting")

    lighting_data = serialize_lights()
    write_json(lighting_data, lighting_path)
    print(f"[Vertex] ✅ Serialized {len(lighting_data)} light(s) → lighting.json")

    # ── Material serialization ─────────────────────────────────────────
    materials_path = os.path.join(data_dir, "materials.json")
    save_snapshot(materials_path, history_dir, "materials")

    materials_data = serialize_materials()
    write_json(materials_data, materials_path)
    print(f"[Vertex] ✅ Serialized {len(materials_data)} material(s) → materials.json")

    # ── Modifier serialization ─────────────────────────────────────────
    modifiers_path = os.path.join(data_dir, "modifiers.json")
    save_snapshot(modifiers_path, history_dir, "modifiers")

    modifiers_data = serialize_modifiers()
    write_json(modifiers_data, modifiers_path)
    print(f"[Vertex] ✅ Serialized {len(modifiers_data)} modifier stack(s) → modifiers.json")

    # ── Summary ────────────────────────────────────────────────────────
    print(f"\n[Vertex] 👤 User: {user}")
    print(f"[Vertex] 🎯 Full scene serialization complete.")


if __name__ == "__main__":
    main()
