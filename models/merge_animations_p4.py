"""
Blender script to merge P4 animation GLB files into one.
Run with: blender --background --python merge_animations_p4.py
"""

import bpy
import os

# Clear the scene
bpy.ops.wm.read_factory_settings(use_empty=True)

MODELS_DIR = os.path.dirname(os.path.abspath(__file__))
P4_DIR = os.path.join(MODELS_DIR, "p4")

BASE_FILE = "Meshy_AI_Animation_Idle_5_P4_withSkin.glb"
ANIM_FILES = {
    'idle': 'Meshy_AI_Animation_Idle_5_P4_withSkin.glb',
    'left': 'Meshy_AI_Animation_Cautious_Crouch_Walk_Left_inplace_P4_withSkin.glb',
    'right': 'Meshy_AI_Animation_Cautious_Crouch_Walk_Right_inplace_P4_withSkin.glb',
    'cast_loop': 'Meshy_AI_Animation_mage_soell_cast_5_P4_withSkin.glb',
    'cast_release': 'Meshy_AI_Animation_mage_soell_cast_3_P4_withSkin.glb',
    'victory': 'Meshy_AI_Animation_Cherish_Pop_Dance_P4_withSkin.glb',
    'defeat': 'Meshy_AI_Animation_Angry_Ground_Stomp_1_P4_withSkin.glb',
}

OUTPUT_FILE = "Character_All_Animations_P4.glb"

print(f"Working in: {MODELS_DIR}")
print(f"P4 folder: {P4_DIR}")

# Import base file
base_path = os.path.join(P4_DIR, BASE_FILE)
print(f"Importing base: {base_path}")

if not os.path.exists(base_path):
    print(f"ERROR: Base file not found: {base_path}")
    exit(1)

bpy.ops.import_scene.gltf(filepath=base_path)

# Get the armature
armature = None
for obj in bpy.context.scene.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

if not armature:
    print("ERROR: No armature found!")
    exit(1)

print(f"Found armature: {armature.name}")

if armature.animation_data and armature.animation_data.action:
    armature.animation_data.action.name = "idle"
    print(f"Renamed base animation to 'idle'")

all_actions = {}
if armature.animation_data and armature.animation_data.action:
    all_actions['idle'] = armature.animation_data.action

for action_name, filename in ANIM_FILES.items():
    if action_name == 'idle':
        continue

    filepath = os.path.join(P4_DIR, filename)
    if not os.path.exists(filepath):
        print(f"WARNING: File not found: {filepath}")
        continue

    print(f"Importing {action_name} from {filename}...")
    bpy.ops.import_scene.gltf(filepath=filepath)

    new_armature = None
    for obj in bpy.context.selected_objects:
        if obj.type == 'ARMATURE' and obj != armature:
            new_armature = obj
            break

    if new_armature and new_armature.animation_data and new_armature.animation_data.action:
        action = new_armature.animation_data.action
        action.name = action_name
        all_actions[action_name] = action
        print(f"  Got action: {action_name}")

        bpy.ops.object.select_all(action='DESELECT')
        new_armature.select_set(True)
        for obj in bpy.context.scene.objects:
            if obj.parent == new_armature:
                obj.select_set(True)
        bpy.ops.object.delete()
    else:
        print(f"  WARNING: No animation found in {filename}")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj != armature and obj.type == 'ARMATURE':
                obj.select_set(True)
                for child in bpy.context.scene.objects:
                    if child.parent == obj:
                        child.select_set(True)
        if bpy.context.selected_objects:
            bpy.ops.object.delete()

print(f"\nCollected {len(all_actions)} actions: {list(all_actions.keys())}")

if not armature.animation_data:
    armature.animation_data_create()

while len(armature.animation_data.nla_tracks) > 0:
    armature.animation_data.nla_tracks.remove(armature.animation_data.nla_tracks[0])

for action_name, action in all_actions.items():
    track = armature.animation_data.nla_tracks.new()
    track.name = action_name
    strip = track.strips.new(action_name, int(action.frame_range[0]), action)
    strip.name = action_name
    print(f"Added NLA track: {action_name}")

if 'idle' in all_actions:
    armature.animation_data.action = all_actions['idle']

bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type in ['MESH', 'ARMATURE']:
        obj.select_set(True)

output_path = os.path.join(MODELS_DIR, OUTPUT_FILE)
print(f"\nExporting to: {output_path}")

bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_nla_strips=True,
    export_animation_mode='ACTIONS',
    use_selection=True
)

print(f"\nDone! Created {OUTPUT_FILE} with {len(all_actions)} animations.")
