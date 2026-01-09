import bpy
import os

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

models_dir = "C:/Users/andre/BabylonPong/models"

# Import base model with idle animation
bpy.ops.import_scene.fbx(filepath=os.path.join(models_dir, "idle.fbx"))

# Get the armature
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

if not armature:
    print("ERROR: No armature found!")
    exit(1)

# Rename the idle action
if armature.animation_data and armature.animation_data.action:
    armature.animation_data.action.name = "idle"
    print(f"Renamed base action to 'idle'")

# Animation files to import (filename, animation_name)
anim_files = [
    ("left_strafe.fbx", "left"),
    ("right_strafe.fbx", "right"),
    ("wizard_cast.fbx", "cast"),
    ("parry.fbx", "parry"),
    ("Casting Spell.fbx", "charging"),
]

# Import each animation
for filename, anim_name in anim_files:
    filepath = os.path.join(models_dir, filename)

    if not os.path.exists(filepath):
        print(f"WARNING: File not found: {filepath}")
        continue

    # Import the FBX
    bpy.ops.import_scene.fbx(filepath=filepath)

    # Find the newly imported armature
    new_armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj != armature:
            new_armature = obj
            break

    if new_armature and new_armature.animation_data and new_armature.animation_data.action:
        # Get the action and rename it
        action = new_armature.animation_data.action
        action.name = anim_name
        print(f"Found action '{anim_name}' from {filename}")

        # Unlink the action so it's not deleted with the armature
        new_armature.animation_data.action = None

        # Select and delete extra objects
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.data.objects:
            if obj != armature and obj.type in ['ARMATURE', 'MESH']:
                if obj.parent != armature and obj not in [c for c in armature.children]:
                    obj.select_set(True)

        bpy.ops.object.delete()
    else:
        print(f"WARNING: No animation found in {filename}")

# Make sure all actions are linked to the armature for export
if not armature.animation_data:
    armature.animation_data_create()

# Push all actions to NLA tracks so they export
expected_anims = ["idle", "left", "right", "cast", "parry", "charging"]
for action in bpy.data.actions:
    if action.name in expected_anims:
        track = armature.animation_data.nla_tracks.new()
        track.name = action.name
        strip = track.strips.new(action.name, int(action.frame_range[0]), action)
        strip.name = action.name
        print(f"Added NLA track for '{action.name}'")

# Export as GLB
output_path = os.path.join(models_dir, "wizard_combined.glb")
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_skins=True,
    export_nla_strips=True,
    export_apply=False
)

print(f"\nExported combined model to: {output_path}")
print(f"Actions exported: {[a.name for a in bpy.data.actions if a.name in expected_anims]}")
