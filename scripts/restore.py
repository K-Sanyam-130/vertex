"""
restore.py — Vertex Full Scene Restorer (Phased Reconstruction)

Reverts the Blender scene to a previously serialized version using a
phased reconstruction pipeline:

    Phase 1: Materials   — Create materials + Principled BSDF first
    Phase 2: Spatial     — Recreate objects with correct transforms
    Phase 3: Lights      — Create/update light datablocks
    Phase 4: Modifiers   — Apply modifier stacks (after all objects exist)

This ordering ensures dependency satisfaction:
  - Materials exist before objects reference them
  - Objects exist before modifiers target them (e.g. Boolean targets)

Run inside Blender:
    blender --background file.blend --python scripts/restore.py
"""

import bpy
import json
import os
import glob
import shutil
import math


# ══════════════════════════════════════════════════════════════════════════════
# JSON I/O & Validation
# ══════════════════════════════════════════════════════════════════════════════

def load_json(filepath):
    """Load a JSON file safely with clear error reporting."""
    if not os.path.isfile(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[Vertex] ⚠ Failed to load {os.path.basename(filepath)}: {e}")
        return None
    if not isinstance(data, list):
        print(f"[Vertex] ⚠ Expected list in {os.path.basename(filepath)}, got {type(data).__name__}")
        return None
    return data


def _validate_spatial_entry(entry):
    """Validate that a spatial entry has required fields.

    Returns:
        bool: True if the entry is valid.
    """
    if not isinstance(entry, dict):
        return False
    if "name" not in entry:
        return False
    for field in ("loc", "rot", "scale"):
        val = entry.get(field)
        if not isinstance(val, (list, tuple)) or len(val) != 3:
            return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Scene Helpers (object creation)
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

    # Light — created as POINT by default; light restore phase will fix the type
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
    """Return existing object, or create a primitive ONLY for simple known types.

    Since spatial.json does NOT store mesh geometry, we must NEVER replace
    complex mesh objects with primitives. Only cameras and lights can be
    safely recreated because they have no custom geometry.

    Returns:
        (obj, was_created): The object and whether it was newly created.
        (None, False): If the object doesn't exist and can't be safely created.
    """
    obj = bpy.data.objects.get(name)
    if obj is not None:
        return obj, False

    key = name.lower()

    # Cameras and lights can be safely recreated (no custom mesh data)
    if "camera" in key:
        cam_data = bpy.data.cameras.new(name + "_data")
        obj = bpy.data.objects.new(name, cam_data)
        bpy.context.collection.objects.link(obj)
        return obj, True

    if "light" in key or "lamp" in key or "hemi" in key:
        light_data = bpy.data.lights.new(name + "_data", type="POINT")
        obj = bpy.data.objects.new(name, light_data)
        bpy.context.collection.objects.link(obj)
        return obj, True

    # For mesh objects: DO NOT create a primitive replacement.
    # The mesh geometry is in the .blend file, not in spatial.json.
    print(
        f"[Vertex] ⚠ Object '{name}' not found in scene. "
        f"Cannot recreate — mesh geometry is not stored in spatial.json. "
        f"Make sure the .blend file contains this object."
    )
    return None, False


def apply_transforms(obj, entry):
    """Set location, rotation, and scale from a spatial entry."""
    # Ensure correct rotation mode, otherwise euler assignment may act randomly 
    # or be completely ignored if the object was set to QUATERNION
    obj.rotation_mode = 'XYZ'
    
    obj.location = entry["loc"]
    obj.rotation_euler = entry["rot"]
    obj.scale = entry["scale"]


def cleanup_scene(valid_names):
    """Report objects in the scene that are not in the JSON data.

    NON-DESTRUCTIVE: This only logs warnings — it does NOT delete objects.
    Mesh geometry lives in the .blend file and cannot be recreated from JSON.
    """
    extra = []
    for obj in bpy.data.objects:
        if obj.name not in valid_names:
            extra.append(obj.name)
    if extra:
        print(
            f"[Vertex] ℹ {len(extra)} object(s) in scene not in snapshot: "
            f"{', '.join(sorted(extra))}"
        )
        print("         These objects were left untouched (not deleted).")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Material Reconstruction
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_nodes_enabled(mat):
    """Enable nodes on a material, handling Blender version differences.

    Blender 6.0+ removes Material.use_nodes (nodes always enabled).
    This helper silences the DeprecationWarning in Blender 4.x/5.x.
    """
    if hasattr(mat, "use_nodes"):
        try:
            mat.use_nodes = True
        except Exception:
            pass  # Blender 6.0+: nodes always enabled


def _get_or_create_material(mat_name):
    """Get existing material or create a new one with nodes enabled.

    Returns:
        bpy.types.Material: The material datablock.
    """
    mat = bpy.data.materials.get(mat_name)
    if mat is not None:
        # Clear existing nodes for idempotent rebuild
        _ensure_nodes_enabled(mat)
        mat.node_tree.nodes.clear()
        return mat

    mat = bpy.data.materials.new(name=mat_name)
    _ensure_nodes_enabled(mat)
    mat.node_tree.nodes.clear()
    return mat


def _build_principled_bsdf(mat, entry):
    """Construct a Principled BSDF node tree from serialized data.

    Args:
        mat: The material datablock.
        entry: dict with material properties from materials.json.
    """
    tree = mat.node_tree

    # Create output node
    output_node = tree.nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (300, 0)

    # Create Principled BSDF node
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)

    # Set base color (RGB → RGBA for Blender's 4-component input)
    base_color = entry.get("base_color", [0.8, 0.8, 0.8])
    bsdf.inputs["Base Color"].default_value = (
        base_color[0], base_color[1], base_color[2], 1.0
    )

    # Set scalar inputs safely
    _safe_set_input(bsdf, "Metallic", entry.get("metallic", 0.0))
    _safe_set_input(bsdf, "Roughness", entry.get("roughness", 0.5))

    # Handle Specular across Blender versions
    if "Specular IOR Level" in bsdf.inputs:
        _safe_set_input(bsdf, "Specular IOR Level", entry.get("specular", 0.5))
    else:
        _safe_set_input(bsdf, "Specular", entry.get("specular", 0.5))

    _safe_set_input(bsdf, "IOR", entry.get("ior", 1.45))
    _safe_set_input(bsdf, "Alpha", entry.get("alpha", 1.0))

    # Emission
    emission = entry.get("emission", {})
    emission_color = emission.get("color", [0.0, 0.0, 0.0])
    emission_strength = emission.get("strength", 0.0)

    # Try Blender 4.x name, fall back to 3.x
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (
            emission_color[0], emission_color[1], emission_color[2], 1.0
        )
    elif "Emission" in bsdf.inputs:
        bsdf.inputs["Emission"].default_value = (
            emission_color[0], emission_color[1], emission_color[2], 1.0
        )

    _safe_set_input(bsdf, "Emission Strength", emission_strength)

    # Connect BSDF → Output
    tree.links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])

    # Rebuild texture nodes
    textures = entry.get("textures", [])
    for i, tex_path in enumerate(textures):
        tex_node = tree.nodes.new("ShaderNodeTexImage")
        tex_node.location = (-400, -200 * i)

        if not tex_path:
            print(f"[Vertex] ⚠ Empty texture path in material '{mat.name}', skipping.")
            continue

        # Resolve relative paths against the blend file directory
        resolved = bpy.path.abspath(tex_path)
        if not os.path.isfile(resolved):
            print(
                f"[Vertex] ⚠ Texture file not found: '{tex_path}' "
                f"(resolved: '{resolved}'). Node created without image."
            )
            continue

        try:
            img = bpy.data.images.load(resolved, check_existing=True)
            tex_node.image = img
        except Exception as e:
            print(f"[Vertex] ⚠ Could not load texture '{tex_path}': {e}")


def _safe_set_input(bsdf, name, value):
    """Set a BSDF input value, silently skipping if the socket doesn't exist."""
    inp = bsdf.inputs.get(name)
    if inp is not None:
        try:
            inp.default_value = value
        except Exception:
            pass


def restore_materials(data_dir):
    """Restore all materials from materials.json.

    Phase 1 of reconstruction — must run before objects are assigned materials.

    Args:
        data_dir: Path to the data/ directory.

    Returns:
        dict: Map of material_name → bpy.types.Material for later assignment.
    """
    materials_path = os.path.join(data_dir, "materials.json")
    mat_data = load_json(materials_path)

    if not mat_data:
        print("[Vertex] ℹ No material data to restore.")
        return {}

    mat_map = {}
    restored = 0

    for entry in mat_data:
        mat_name = entry.get("material_name")
        if not mat_name:
            print("[Vertex] ⚠ Material entry missing 'material_name', skipping.")
            continue

        try:
            mat = _get_or_create_material(mat_name)
            _build_principled_bsdf(mat, entry)
            mat_map[mat_name] = mat
            restored += 1
        except Exception as e:
            print(f"[Vertex] ⚠ Failed to restore material '{mat_name}': {e}")

    print(f"[Vertex] ✅ Phase 1: Restored {restored} material(s)")
    return mat_map


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Lighting Reconstruction
# ══════════════════════════════════════════════════════════════════════════════

def _get_or_create_light(name, light_type):
    """Get or create a light datablock with the correct type.

    If the light exists but has a different type, recreate it.

    Args:
        name: Light datablock name.
        light_type: One of "POINT", "SUN", "SPOT", "AREA".

    Returns:
        bpy.types.Light: The light datablock.
    """
    light = bpy.data.lights.get(name)
    if light is not None:
        if light.type != light_type:
            # Type changed — must remove and recreate
            bpy.data.lights.remove(light)
            light = bpy.data.lights.new(name=name, type=light_type)
        return light

    return bpy.data.lights.new(name=name, type=light_type)


def restore_lights(data_dir):
    """Restore all light datablocks from lighting.json.

    Phase 2 of reconstruction. Updates energy, color, shadow, and spot
    settings on existing or newly created light datablocks.

    Note: This does NOT create light objects or set transforms — that's
    handled by the spatial restore. This only sets light DATA properties.

    Args:
        data_dir: Path to the data/ directory.
    """
    lighting_path = os.path.join(data_dir, "lighting.json")
    light_data = load_json(lighting_path)

    if not light_data:
        print("[Vertex] ℹ No lighting data to restore.")
        return

    restored = 0

    for entry in light_data:
        name = entry.get("name")
        light_type = entry.get("type", "POINT")

        if not name:
            print("[Vertex] ⚠ Light entry missing 'name', skipping.")
            continue

        try:
            light = _get_or_create_light(name, light_type)

            # Apply core properties
            light.energy = entry.get("energy", 1000.0)
            color = entry.get("color", [1.0, 1.0, 1.0])
            light.color = (color[0], color[1], color[2])

            # Shadow settings
            shadow = entry.get("shadow", {})
            light.use_shadow = shadow.get("use_shadow", True)
            light.shadow_soft_size = shadow.get("softness", 0.25)

            # Spot-specific settings
            if light_type == "SPOT" and "spot" in entry:
                spot = entry["spot"]
                light.spot_size = spot.get("size", math.radians(45))
                light.spot_blend = spot.get("blend", 0.15)

            # Link to scene if not already present
            _ensure_light_in_scene(name, light)

            restored += 1

        except Exception as e:
            print(f"[Vertex] ⚠ Failed to restore light '{name}': {e}")

    print(f"[Vertex] ✅ Phase 2: Restored {restored} light(s)")


def _ensure_light_in_scene(name, light_data):
    """Make sure a light object exists in the scene for this light datablock.

    If no object references this light data, create one and link it.

    Args:
        name: Object name to use.
        light_data: The bpy.types.Light datablock.
    """
    # Check if any object already uses this light data
    for obj in bpy.data.objects:
        if obj.type == "LIGHT" and obj.data == light_data:
            return  # Already linked

    # Check if an object with this name exists but has wrong data
    obj = bpy.data.objects.get(name)
    if obj is not None and obj.type == "LIGHT":
        obj.data = light_data
        return

    # Create new light object
    obj = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(obj)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Modifier Reconstruction
# ══════════════════════════════════════════════════════════════════════════════

def _apply_subsurf(obj, settings):
    """Add/update a Subdivision Surface modifier."""
    mod = obj.modifiers.new(name="Subdivision", type="SUBSURF")
    mod.levels = settings.get("levels_viewport", 1)
    mod.render_levels = settings.get("levels_render", 2)


def _apply_array(obj, settings):
    """Add/update an Array modifier."""
    mod = obj.modifiers.new(name="Array", type="ARRAY")
    mod.count = settings.get("count", 2)
    offset = settings.get("relative_offset", [1.0, 0.0, 0.0])
    mod.use_relative_offset = True
    mod.relative_offset_displace = offset


def _apply_boolean(obj, settings):
    """Add/update a Boolean modifier.

    The target object must already exist in the scene.
    """
    mod = obj.modifiers.new(name="Boolean", type="BOOLEAN")
    mod.operation = settings.get("operation", "DIFFERENCE")
    target_name = settings.get("target")
    if target_name:
        target_obj = bpy.data.objects.get(target_name)
        if target_obj:
            mod.object = target_obj
        else:
            print(
                f"[Vertex] ⚠ Boolean target '{target_name}' not found "
                f"for object '{obj.name}'. Modifier added without target."
            )


def _apply_mirror(obj, settings):
    """Add/update a Mirror modifier."""
    mod = obj.modifiers.new(name="Mirror", type="MIRROR")
    axes = settings.get("use_axis", [True, False, False])
    mod.use_axis[0] = axes[0]
    mod.use_axis[1] = axes[1]
    mod.use_axis[2] = axes[2]
    bisect = settings.get("use_bisect_axis", [False, False, False])
    mod.use_bisect_axis[0] = bisect[0]
    mod.use_bisect_axis[1] = bisect[1]
    mod.use_bisect_axis[2] = bisect[2]
    mirror_name = settings.get("mirror_object")
    if mirror_name:
        mirror_obj = bpy.data.objects.get(mirror_name)
        if mirror_obj:
            mod.mirror_object = mirror_obj


def _apply_solidify(obj, settings):
    """Add/update a Solidify modifier."""
    mod = obj.modifiers.new(name="Solidify", type="SOLIDIFY")
    mod.thickness = settings.get("thickness", 0.01)
    mod.offset = settings.get("offset", -1.0)
    mod.use_even_offset = settings.get("use_even_offset", False)


def _apply_bevel(obj, settings):
    """Add/update a Bevel modifier."""
    mod = obj.modifiers.new(name="Bevel", type="BEVEL")
    mod.width = settings.get("width", 0.02)
    mod.segments = settings.get("segments", 1)
    mod.limit_method = settings.get("limit_method", "ANGLE")


def _apply_edge_split(obj, settings):
    """Add/update an Edge Split modifier."""
    mod = obj.modifiers.new(name="EdgeSplit", type="EDGE_SPLIT")
    mod.split_angle = settings.get("split_angle", 0.523599)
    mod.use_edge_angle = settings.get("use_edge_angle", True)
    mod.use_edge_sharp = settings.get("use_edge_sharp", True)


def _apply_decimate(obj, settings):
    """Add/update a Decimate modifier."""
    mod = obj.modifiers.new(name="Decimate", type="DECIMATE")
    mod.decimate_type = settings.get("decimate_type", "COLLAPSE")
    if mod.decimate_type == "COLLAPSE":
        mod.ratio = settings.get("ratio", 1.0)
    elif mod.decimate_type == "UN_SUBDIVIDE":
        mod.iterations = settings.get("iterations", 0)
    elif mod.decimate_type == "DISSOLVE":
        mod.angle_limit = settings.get("angle_limit", 0.087266)


def _apply_wireframe(obj, settings):
    """Add/update a Wireframe modifier."""
    mod = obj.modifiers.new(name="Wireframe", type="WIREFRAME")
    mod.thickness = settings.get("thickness", 0.02)
    mod.use_even_offset = settings.get("use_even_offset", True)
    mod.use_replace = settings.get("use_replace", True)


def _apply_screw(obj, settings):
    """Add/update a Screw modifier."""
    mod = obj.modifiers.new(name="Screw", type="SCREW")
    mod.angle = settings.get("angle", math.radians(360))
    mod.steps = settings.get("steps", 16)
    mod.render_steps = settings.get("render_steps", 16)
    mod.screw_offset = settings.get("screw_offset", 0.0)
    mod.axis = settings.get("axis", "Z")


# Registry of modifier applicators
_MODIFIER_APPLICATORS = {
    "SUBSURF": _apply_subsurf,
    "ARRAY": _apply_array,
    "BOOLEAN": _apply_boolean,
    "MIRROR": _apply_mirror,
    "SOLIDIFY": _apply_solidify,
    "BEVEL": _apply_bevel,
    "EDGE_SPLIT": _apply_edge_split,
    "DECIMATE": _apply_decimate,
    "WIREFRAME": _apply_wireframe,
    "SCREW": _apply_screw,
}


def restore_modifiers(data_dir):
    """Restore modifier stacks from modifiers.json.

    Phase 3 of reconstruction — must run AFTER all objects exist in the scene.
    Clears existing modifiers on each target object for idempotent rebuilds.

    Args:
        data_dir: Path to the data/ directory.
    """
    modifiers_path = os.path.join(data_dir, "modifiers.json")
    mod_data = load_json(modifiers_path)

    if not mod_data:
        print("[Vertex] ℹ No modifier data to restore.")
        return

    restored_objects = 0

    for entry in mod_data:
        obj_name = entry.get("object_name")
        if not obj_name:
            print("[Vertex] ⚠ Modifier entry missing 'object_name', skipping.")
            continue

        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            print(f"[Vertex] ⚠ Object '{obj_name}' not found, cannot apply modifiers.")
            continue

        # Clear existing modifiers for idempotent rebuild
        obj.modifiers.clear()

        mod_list = entry.get("modifiers", [])
        applied_count = 0

        for mod_settings in mod_list:
            mod_type = mod_settings.get("type")
            applicator = _MODIFIER_APPLICATORS.get(mod_type)

            if applicator is None:
                print(
                    f"[Vertex] ⚠ Unsupported modifier type '{mod_type}' "
                    f"on '{obj_name}', skipping."
                )
                continue

            try:
                applicator(obj, mod_settings)
                applied_count += 1
            except Exception as e:
                print(
                    f"[Vertex] ⚠ Failed to apply '{mod_type}' "
                    f"on '{obj_name}': {e}"
                )

        if applied_count > 0:
            restored_objects += 1

    print(f"[Vertex] ✅ Phase 3: Restored modifiers on {restored_objects} object(s)")


# ══════════════════════════════════════════════════════════════════════════════
# Material Assignment (Post-Spatial Restore)
# ══════════════════════════════════════════════════════════════════════════════

def assign_materials_to_objects(mat_map):
    """Assign restored materials to mesh objects that reference them.

    Checks each mesh object's existing material slots and updates them
    if a matching material name exists in the restored map.

    Args:
        mat_map: dict of material_name → bpy.types.Material.
    """
    if not mat_map:
        return

    assigned = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        for i, slot in enumerate(obj.material_slots):
            if slot.material and slot.material.name in mat_map:
                slot.material = mat_map[slot.material.name]
                assigned += 1

    if assigned:
        print(f"[Vertex] ✅ Reassigned {assigned} material slot(s)")


# ══════════════════════════════════════════════════════════════════════════════
# Version Discovery
# ══════════════════════════════════════════════════════════════════════════════

def get_versions(history_dir, domain_filter="spatial"):
    """Return list of (version_num, domain, timestamp, is_merge, filepath) sorted by version.

    Args:
        history_dir: Path to the history directory.
        domain_filter: If set, only return snapshots for this domain.
            Use None to return all domains. Default: "spatial".
    """
    files = sorted(glob.glob(os.path.join(history_dir, "v*.json")))
    entries = []
    for f in files:
        basename = os.path.basename(f)
        try:
            # Parse: v014_spatial_2026-03-28_02-57-16.json
            #   or:  v003_merge_2026-03-27_23-07-02.json
            #   or:  v001_2026-03-27_22-54-17.json  (legacy, pre-domain)
            name_no_ext = basename.replace(".json", "")
            parts = name_no_ext.split("_", 1)
            ver_num = int(parts[0][1:])
            rest = parts[1] if len(parts) > 1 else "unknown"

            # Detect domain from filename
            is_merge = "merge" in rest
            domain = "spatial"  # default for legacy snapshots
            matched = False
            for d in ("spatial", "lighting", "materials", "modifiers"):
                if rest.startswith(d + "_") or rest == d:
                    domain = d
                    rest = rest[len(d) + 1:]  # strip domain prefix
                    matched = True
                    break
            if not matched and rest.startswith("merge_"):
                domain = "spatial"  # legacy merges are spatial
                rest = rest.replace("merge_", "")

            timestamp = rest.replace("_", " ") if rest else "unknown"

            # Apply domain filter
            if domain_filter and domain != domain_filter:
                continue

            entries.append((ver_num, domain, timestamp, is_merge, f))
        except (ValueError, IndexError):
            continue
    return entries


# ══════════════════════════════════════════════════════════════════════════════
# Spatial Restore (from snapshot)
# ══════════════════════════════════════════════════════════════════════════════

def restore_spatial(snapshot_path, current_path):
    """Apply a spatial snapshot to the scene.

    Args:
        snapshot_path: Path to the versioned spatial snapshot.
        current_path: Path to the current spatial.json.

    Returns:
        set: Names of objects in the restored scene.
    """
    spatial_data = load_json(snapshot_path)
    if not spatial_data:
        print("[Vertex] ⚠ Spatial snapshot is empty or corrupt.")
        return set()

    # Validate and filter entries
    valid_entries = []
    skipped = 0
    for entry in spatial_data:
        if _validate_spatial_entry(entry):
            valid_entries.append(entry)
        else:
            skipped += 1
            print(f"[Vertex] ⚠ Skipping invalid spatial entry: {entry}")

    if skipped > 0:
        print(f"[Vertex] ⚠ Skipped {skipped} invalid entries out of {len(spatial_data)}")

    if not valid_entries:
        print("[Vertex] ⚠ No valid spatial entries found in snapshot.")
        return set()

    json_names = {entry["name"] for entry in valid_entries}

    # Non-destructive: only report extra objects, don't delete them
    cleanup_scene(json_names)

    updated = 0
    created = 0
    missing = 0

    for entry in valid_entries:
        name = entry["name"]
        obj, was_created = get_or_create_object(name)

        if obj is None:
            # Object doesn't exist and can't be safely recreated
            missing += 1
            continue

        apply_transforms(obj, entry)
        if was_created:
            created += 1
        else:
            updated += 1

    if missing > 0:
        print(
            f"[Vertex] ⚠ {missing} object(s) could not be restored "
            f"(not found in .blend file)"
        )

    # Sync spatial.json with restored state
    shutil.copy2(snapshot_path, current_path)

    # Show attribution info
    users = set()
    for entry in valid_entries:
        user = entry.get("modified_by")
        if user and user != "unknown":
            users.add(user)

    print(
        f"\n[Vertex] ✅ Spatial: Restored {len(valid_entries)} object(s) "
        f"from {os.path.basename(snapshot_path)} "
        f"({created} created, {updated} updated)"
    )
    if users:
        print(f"         👤 Contributors: {', '.join(sorted(users))}")

    return json_names


# ══════════════════════════════════════════════════════════════════════════════
# Image Cleanup (GPU Texture Error Prevention)
# ══════════════════════════════════════════════════════════════════════════════

def _cleanup_orphaned_images():
    """Remove orphaned image datablocks that cause GPU texture errors.

    Blender keeps image datablocks even when their source files are missing.
    These broken images trigger:
        gpu.texture | ERROR Failed to create GPU texture from Blender image

    This function removes images that:
      - Have no file path
      - Reference files that don't exist on disk
      - Have zero users (orphaned)
    """
    removed = 0
    for img in list(bpy.data.images):
        # Skip built-in images (Render Result, Viewer Node, etc.)
        if img.name in ("Render Result", "Viewer Node"):
            continue

        # Remove images with no filepath
        if not img.filepath:
            if img.users == 0:
                bpy.data.images.remove(img)
                removed += 1
            continue

        # Remove images referencing missing files
        resolved = bpy.path.abspath(img.filepath)
        if not os.path.isfile(resolved):
            print(f"[Vertex] 🗑 Removing orphaned image '{img.name}' (file missing: {img.filepath})")
            bpy.data.images.remove(img)
            removed += 1

    if removed:
        print(f"[Vertex] ✅ Cleaned up {removed} orphaned image(s)")


# ══════════════════════════════════════════════════════════════════════════════
# Full Scene Restore (Phased Pipeline)
# ══════════════════════════════════════════════════════════════════════════════

def full_restore(snapshot_path, data_dir, current_path):
    """Execute the complete phased restoration pipeline.

    Order:
        1. Materials  — so objects can reference them
        2. Spatial    — create/update all objects
        3. Lights     — apply light datablock properties
        4. Modifiers  — apply stacks after all objects exist

    Args:
        snapshot_path: Path to the versioned spatial snapshot.
        data_dir: Path to the data/ directory.
        current_path: Path to the current spatial.json.
    """
    print("\n[Vertex] 🔄 Starting phased scene reconstruction...\n")

    # Phase 1: Materials (created before objects so they can be assigned)
    mat_map = restore_materials(data_dir)

    # Phase 2: Spatial (create/position all objects)
    scene_names = restore_spatial(snapshot_path, current_path)

    # Post-spatial: Assign materials to objects
    assign_materials_to_objects(mat_map)

    # Phase 3: Lights (update light datablocks with correct properties)
    restore_lights(data_dir)

    # Phase 4: Modifiers (applied after all objects exist for dependency safety)
    restore_modifiers(data_dir)

    # Cleanup: Remove orphaned images that cause GPU texture errors
    _cleanup_orphaned_images()

    # Save the .blend file
    bpy.ops.wm.save_mainfile()

    print("\n[Vertex] 🎯 Full scene reconstruction complete.\n")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

def parse_args():
    argv = sys.argv
    if "--" in argv:
        script_args = argv[argv.index("--") + 1:]
    else:
        script_args = []

    version = None
    i = 0
    while i < len(script_args):
        if script_args[i] == "--version" and i + 1 < len(script_args):
            version = int(script_args[i + 1])
            i += 2
        else:
            i += 1
    return version

def main():
    base_dir = (
        os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    )
    data_dir = os.path.join(base_dir, "data")
    history_dir = os.path.join(data_dir, "history")
    current_path = os.path.join(data_dir, "spatial.json")

    # Only show spatial snapshots (the root cause of KeyError was loading
    # lighting/materials/modifiers snapshots as spatial data)
    versions = get_versions(history_dir, domain_filter="spatial")

    if not versions:
        print("[Vertex] ❌ No spatial version history found.")
        print("         Run serialize.py at least twice to build history.")
        return

    # --- Only 1 version: restore it directly ---
    if len(versions) == 1:
        ver_num, domain, timestamp, is_merge, filepath = versions[0]
        tag = " [MERGE]" if is_merge else ""
        print(
            f"[Vertex] Only one spatial snapshot available "
            f"(v{ver_num}{tag} — {timestamp}), restoring..."
        )
        full_restore(filepath, data_dir, current_path)
        return

    chosen_ver = parse_args()

    # --- Print versions if no version specified ---
    if chosen_ver is None:
        print(f"\n[Vertex] 📋 Available spatial versions ({len(versions)} snapshots):\n")
        print(f"  {'#':<6} {'Type':<10} {'Timestamp':<25}")
        print(f"  {'---':<6} {'---':<10} {'---':<25}")

        for ver_num, domain, timestamp, is_merge, _ in versions:
            tag = "[MERGE]" if is_merge else ""
            print(f"  v{ver_num:<5} {tag:<10} {timestamp}")

        print("\n[Vertex] ℹ Use the Version Number input to select a version to restore.")
        return

    # Find the chosen version
    match = None
    for ver_num, domain, timestamp, is_merge, filepath in versions:
        if ver_num == chosen_ver:
            match = filepath
            break

    if not match:
        print(f"[Vertex] ❌ Version {chosen_ver} not found.")
        return

    full_restore(match, data_dir, current_path)


if __name__ == "__main__":
    main()