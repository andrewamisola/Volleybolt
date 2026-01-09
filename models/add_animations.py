import bpy
import os

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

models_dir = "C:/Users/andre/BabylonPong/models"

# Import existing combined model
bpy.ops.import_scene.gltf(filepath=os.path.join(models_dir, "wizard_combined.glb"))

# Get the armature
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

if not armature:
    print("ERROR: No armature found!")
    exit(1)

print(f"Found armature: {armature.name}")
print(f"Existing actions: {[a.name for a in bpy.data.actions]}")

# New animation files to import
new_anims = [
    ("parry.fbx", "parry"),
    ("Casting Spell.fbx", "charging"),
]

# Import each new animation
for filename, anim_name in new_anims:
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
        action = new_armature.animation_data.action
        action.name = anim_name
        print(f"Found action '{anim_name}' from {filename}")

        # Unlink the action
        new_armature.animation_data.action = None

        # Delete extra objects
        bpy.ops.object.select_all(action='DESELECT')
        for obj in list(bpy.data.objects):
            if obj != armature and obj.type == 'ARMATURE':
                obj.select_set(True)
            elif obj.type == 'MESH' and obj.parent != armature:
                # Check if it's parented to the new armature
                if obj.parent == new_armature or (hasattr(obj, 'parent') and obj.parent and obj.parent.type == 'ARMATURE' and obj.parent != armature):
                    obj.select_set(True)

        bpy.ops.object.delete()
    else:
        print(f"WARNING: No animation found in {filename}")

# Ensure armature has animation data
if not armature.animation_data:
    armature.animation_data_create()

# Add new actions to NLA tracks
new_action_names = ["parry", "charging"]
for action in bpy.data.actions:
    if action.name in new_action_names:
        # Check if track already exists
        existing = [t for t in armature.animation_data.nla_tracks if t.name == action.name]
        if not existing:
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

print(f"\nExported to: {output_path}")
print(f"All actions: {[a.name for a in bpy.data.actions]}")
