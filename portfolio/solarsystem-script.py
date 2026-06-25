import bpy
import os
import math
import random

# Config
base_path = r"C:\Users\admin\Downloads\Planets (Textures)-20260504T042323Z-3-001\Planets (Textures)"
bg_image_path = os.path.join(base_path, "universe.jpg")
sun_tex_path = os.path.join(base_path, "sun.jpg") 

TOTAL_FRAMES = 2160 
INTRO_HOLD = 120 
TRANSITION_FRAMES = 45 
HOLD_FRAMES = 75 

# Planet Data: [Scale, Distance, Orbit_Loops, Rotation_Loops]
system_data = {
    "mercury": [0.4,  6,  8,  2],
    "venus":   [0.9,  9,  6, -1],
    "earth":   [1.0, 13,  5, 10],
    "mars":    [0.5, 17,  4, 10],
    "jupiter": [3.5, 26,  2, 25],
    "saturn":  [2.8, 42,  2, 23],
    "uranus":  [1.8, 55,  1, -15],
    "neptune": [1.7, 65,  1, 16]  
}

# Cleanup
for obj in bpy.data.objects:
    bpy.data.objects.remove(obj, do_unlink=True)
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat, do_unlink=True)
bpy.context.scene.timeline_markers.clear()

# Scene
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = TOTAL_FRAMES

# Background
world = scene.world
world.use_nodes = True
nodes = world.node_tree.nodes
links = world.node_tree.links
nodes.clear()

bg_node = nodes.new('ShaderNodeBackground')
env_node = nodes.new('ShaderNodeTexEnvironment')
out_world = nodes.new('ShaderNodeOutputWorld')

if os.path.exists(bg_image_path):
    env_node.image = bpy.data.images.load(bg_image_path)
bg_node.inputs['Strength'].default_value = 1.0
links.new(env_node.outputs['Color'], bg_node.inputs['Color'])
links.new(bg_node.outputs['Background'], out_world.inputs['Surface'])

# Text Material
text_mat = bpy.data.materials.new(name="Text_Metallic")
text_mat.use_nodes = True
t_bsdf = text_mat.node_tree.nodes.get("Principled BSDF")
t_bsdf.inputs['Base Color'].default_value = (0.7, 0.85, 1.0, 1.0) 
t_bsdf.inputs['Metallic'].default_value = 1.0  
t_bsdf.inputs['Roughness'].default_value = 0.15 
t_bsdf.inputs['Emission Color'].default_value = (0.1, 0.4, 0.8, 1.0) 
t_bsdf.inputs['Emission Strength'].default_value = 0.2 

# Helpers
def add_perfect_loop(obj, axis_index, loops):
    original_interp = bpy.context.preferences.edit.keyframe_new_interpolation_type
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    
    obj.rotation_euler[axis_index] = 0
    obj.keyframe_insert(data_path="rotation_euler", index=axis_index, frame=1)
    obj.rotation_euler[axis_index] = loops * 2 * math.pi 
    obj.keyframe_insert(data_path="rotation_euler", index=axis_index, frame=TOTAL_FRAMES + 1)
    
    bpy.context.preferences.edit.keyframe_new_interpolation_type = original_interp

def create_planet_label(name, parent_obj, distance, height_offset, text_scale):
    bpy.ops.object.text_add(location=(distance, 0, height_offset))
    txt = bpy.context.object
    txt.name = f"{name}_Text"
    txt.data.body = name.capitalize()
    txt.data.extrude = 0.05
    txt.data.align_x = 'CENTER'
    txt.data.align_y = 'BOTTOM'
    txt.data.materials.append(text_mat)
    
    txt.scale = (text_scale, text_scale, text_scale)
    txt.rotation_euler = (math.radians(90), 0, 0)
    txt.parent = parent_obj
    
    txt.hide_viewport = True
    txt.hide_render = True
    txt.keyframe_insert(data_path="hide_viewport", frame=1)
    txt.keyframe_insert(data_path="hide_render", frame=1)
    return txt

def create_centered_tracking_camera(name, parent_obj, dist, scale, text_height, look_target_obj):
    cam_y = -(scale * 7 + 6) 
    cam_z = scale * 2.8 + 2
    
    bpy.ops.object.camera_add(location=(dist, cam_y, cam_z))
    cam = bpy.context.object
    cam.name = f"Cam_{name}"
    cam.data.lens = 45 
    cam.parent = parent_obj
    
    track_con = cam.constraints.new('TRACK_TO')
    track_con.target = look_target_obj
    track_con.track_axis = 'TRACK_NEGATIVE_Z'
    track_con.up_axis = 'UP_Y'
    
    return cam

tour_stops = [] 

# 0. Main Camera
bpy.ops.object.camera_add(location=(0, -140, 100))
main_cam = bpy.context.object
main_cam.name = "Anchor_Overview"
main_cam.rotation_euler = (math.radians(53), 0, 0)

# 1. Sun & Lighting
bpy.ops.mesh.primitive_uv_sphere_add(radius=4.5, segments=128, ring_count=64) 
sun = bpy.context.object
sun.name = "Sun"
bpy.ops.object.shade_smooth()
add_perfect_loop(sun, 2, 1)

sun_mat = bpy.data.materials.new(name="Sun_Procedural_Material")
sun_mat.use_nodes = True
sun_mat.node_tree.nodes.clear()
out_node = sun_mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
emission = sun_mat.node_tree.nodes.new('ShaderNodeEmission')

noise1 = sun_mat.node_tree.nodes.new('ShaderNodeTexNoise')
noise1.inputs['Scale'].default_value = 3.0
noise1.inputs['Detail'].default_value = 15.0
noise1.inputs['Distortion'].default_value = 2.0

noise2 = sun_mat.node_tree.nodes.new('ShaderNodeTexNoise')
noise2.inputs['Scale'].default_value = 25.0
noise2.inputs['Detail'].default_value = 15.0

mix_noise = sun_mat.node_tree.nodes.new('ShaderNodeMath')
mix_noise.operation = 'MULTIPLY'
sun_mat.node_tree.links.new(noise1.outputs['Fac'], mix_noise.inputs[0])
sun_mat.node_tree.links.new(noise2.outputs['Fac'], mix_noise.inputs[1])

add_noise = sun_mat.node_tree.nodes.new('ShaderNodeMath')
add_noise.operation = 'ADD'
add_noise.inputs[1].default_value = 0.15
sun_mat.node_tree.links.new(mix_noise.outputs['Value'], add_noise.inputs[0])

ramp = sun_mat.node_tree.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.interpolation = 'B_SPLINE'
ramp.color_ramp.elements[0].position = 0.05
ramp.color_ramp.elements[0].color = (0.5, 0.02, 0.0, 1.0) 
ramp.color_ramp.elements.new(0.2)
ramp.color_ramp.elements[1].color = (0.9, 0.2, 0.0, 1.0) 
ramp.color_ramp.elements.new(0.4)
ramp.color_ramp.elements[2].color = (1.0, 0.6, 0.05, 1.0) 
ramp.color_ramp.elements[3].position = 0.7
ramp.color_ramp.elements[3].color = (1.0, 0.95, 0.8, 1.0) 

sun_mat.node_tree.links.new(add_noise.outputs['Value'], ramp.inputs['Fac'])
sun_mat.node_tree.links.new(ramp.outputs['Color'], emission.inputs['Color'])

layer_weight = sun_mat.node_tree.nodes.new('ShaderNodeLayerWeight')
layer_weight.inputs['Blend'].default_value = 0.6

strength_mult = sun_mat.node_tree.nodes.new('ShaderNodeMath')
strength_mult.operation = 'MULTIPLY'
strength_mult.inputs[1].default_value = 12.0 
sun_mat.node_tree.links.new(layer_weight.outputs['Facing'], strength_mult.inputs[0])

base_glow = sun_mat.node_tree.nodes.new('ShaderNodeMath')
base_glow.operation = 'ADD'
base_glow.inputs[1].default_value = 1.5 
sun_mat.node_tree.links.new(strength_mult.outputs['Value'], base_glow.inputs[0])

sun_mat.node_tree.links.new(base_glow.outputs['Value'], emission.inputs['Strength'])
sun_mat.node_tree.links.new(emission.outputs['Emission'], out_node.inputs['Surface'])
sun.data.materials.append(sun_mat)

bpy.ops.object.light_add(type='POINT', radius=4.5, location=(0,0,0))
sun_light = bpy.context.object
sun_light.data.energy = 500000 

bpy.ops.object.light_add(type='SUN', rotation=(math.radians(45), math.radians(45), 0))
fill_light = bpy.context.object
fill_light.data.energy = 1.5

sun_text_height = 4.5 + 2.0
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, sun_text_height / 2.0))
sun_target = bpy.context.object
sun_target.name = "Sun_Look_Target"

sun_txt = create_planet_label("Sun", None, 0, sun_text_height, text_scale=4.5)
sun_cam = create_centered_tracking_camera("Sun", sun, 0, 4.5, sun_text_height, sun_target)
tour_stops.append((sun_txt, sun_cam))

# 2. Planets, Moons, Asteroids
for name, data in system_data.items():
    
    if name == "jupiter":
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
        belt_pivot = bpy.context.object
        belt_pivot.name = "Asteroid_Belt"
        add_perfect_loop(belt_pivot, 2, 3)

        rock_mat = bpy.data.materials.new("Asteroid_Rock")
        rock_mat.use_nodes = True
        rock_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.3, 0.28, 0.25, 1.0)

        for i in range(150):
            radius, angle = random.uniform(20, 23), random.uniform(0, 2 * math.pi)
            x, y, z = radius * math.cos(angle), radius * math.sin(angle), random.uniform(-0.8, 0.8)
            bpy.ops.mesh.primitive_ico_sphere_add(radius=random.uniform(0.05, 0.25), subdivisions=1, location=(x, y, z))
            rock = bpy.context.object
            rock.data.materials.append(rock_mat)
            rock.parent = belt_pivot

        bpy.ops.mesh.primitive_ico_sphere_add(radius=0.4, subdivisions=2, location=(21.5, 0, 0))
        main_rock = bpy.context.object
        main_rock.data.materials.append(rock_mat)
        main_rock.parent = belt_pivot

        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(21.5, 0, 0.75))
        ast_target = bpy.context.object
        ast_target.parent = belt_pivot

        ast_txt = create_planet_label("Asteroids", belt_pivot, 21.5, 1.5, text_scale=1.5)
        ast_cam = create_centered_tracking_camera("Asteroids", belt_pivot, 21.5, 0.6, 1.5, ast_target)
        tour_stops.append((ast_txt, ast_cam))

    scale, dist, orbit_loops, rot_loops = data
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
    orbit_pivot = bpy.context.object
    orbit_pivot.name = f"{name.capitalize()}_Orbit"
    add_perfect_loop(orbit_pivot, 2, orbit_loops)
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=scale, location=(dist, 0, 0), segments=64, ring_count=32)
    planet = bpy.context.object
    planet.name = name.capitalize()
    bpy.ops.object.shade_smooth()
    planet.cycles.shadow_terminator_geometry_offset = 0.15
    planet.parent = orbit_pivot
    add_perfect_loop(planet, 2, rot_loops)
    
    mat = bpy.data.materials.new(name=f"{name}_Material")
    mat.use_nodes = True
    p_bsdf = mat.node_tree.nodes.get("Principled BSDF")
    p_bsdf.inputs['Roughness'].default_value = 0.8
    
    tex_path = os.path.join(base_path, f"{name.lower()}.jpg")
    if os.path.exists(tex_path):
        p_tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        p_tex.image = bpy.data.images.load(tex_path)
        mat.node_tree.links.new(p_tex.outputs['Color'], p_bsdf.inputs['Base Color'])
    planet.data.materials.append(mat)
    
    if name == "saturn":
        bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=scale*2.4, depth=0.005, location=(0, 0, 0))
        rings = bpy.context.object
        rings.name = "Saturn_Rings"
        rings.parent = planet 
        rings.location = (0, 0, 0)
        
        ring_mat = bpy.data.materials.new("Ring_Material")
        ring_mat.use_nodes = True
        r_nodes = ring_mat.node_tree.nodes
        r_links = ring_mat.node_tree.links
        r_bsdf = r_nodes.get("Principled BSDF")
        
        ring_tex_path = os.path.join(base_path, "saturn_rings.png")
        if os.path.exists(ring_tex_path):
            r_tex = r_nodes.new('ShaderNodeTexImage')
            r_tex.image = bpy.data.images.load(ring_tex_path)
            r_links.new(r_tex.outputs['Color'], r_bsdf.inputs['Base Color'])
            r_links.new(r_tex.outputs['Alpha'], r_bsdf.inputs['Alpha'])
        else:
            r_bsdf.inputs['Base Color'].default_value = (0.8, 0.7, 0.6, 1.0)
            
        rings.data.materials.append(ring_mat)
    
    text_height = scale + 2.0 if name == "saturn" else scale + 1.0
    
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(dist, 0, text_height / 2.0))
    p_target = bpy.context.object
    p_target.name = f"{name}_Look_Target"
    p_target.parent = orbit_pivot

    txt = create_planet_label(name, orbit_pivot, dist, text_height, text_scale=scale)
    cam = create_centered_tracking_camera(name, orbit_pivot, dist, scale, text_height, p_target)
    tour_stops.append((txt, cam))

    if name == "earth":
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
        moon_pivot = bpy.context.object
        moon_pivot.name = "Moon_Orbit"
        moon_pivot.parent = planet 
        moon_pivot.location = (0, 0, 0)
        add_perfect_loop(moon_pivot, 2, 25) 

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(0, 0, 0), segments=32, ring_count=16)
        moon = bpy.context.object
        moon.name = "Moon"
        bpy.ops.object.shade_smooth()
        moon.parent = moon_pivot
        moon.location = (1.6, 0, 0) 
        add_perfect_loop(moon, 2, 6)

        moon_mat = bpy.data.materials.new("Moon_Material")
        moon_mat.use_nodes = True
        moon_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.4, 0.4, 0.4, 1.0)
        moon.data.materials.append(moon_mat)

        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(1.6, 0, 0.3))
        moon_target = bpy.context.object
        moon_target.parent = moon_pivot

        moon_txt = create_planet_label("Moon", moon_pivot, 1.6, 0.6, text_scale=0.22)
        moon_cam = create_centered_tracking_camera("Moon", moon_pivot, 1.6, 0.22, 0.6, moon_target)
        tour_stops.append((moon_txt, moon_cam))

# 3. Procedural Rocket
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
rocket_pivot = bpy.context.object
rocket_pivot.name = "Rocket_Trajectory"
add_perfect_loop(rocket_pivot, 2, -2) 

mat_metal = bpy.data.materials.new("Rocket_Metal")
mat_metal.use_nodes = True
mat_metal.node_tree.nodes["Principled BSDF"].inputs['Metallic'].default_value = 1.0
mat_red = bpy.data.materials.new("Rocket_Red")
mat_red.use_nodes = True
mat_red.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.8, 0.05, 0.05, 1.0)
mat_glow = bpy.data.materials.new("Rocket_Glow")
mat_glow.use_nodes = True
mat_glow.node_tree.nodes["Principled BSDF"].inputs['Emission Color'].default_value = (0.1, 0.5, 1.0, 1.0)
mat_glow.node_tree.nodes["Principled BSDF"].inputs['Emission Strength'].default_value = 15.0

rocket_dist = 65 
bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.0, location=(rocket_dist, 0, 0))
rocket_body = bpy.context.object
rocket_body.rotation_euler = (math.radians(90), 0, 0)
rocket_body.data.materials.append(mat_metal)
rocket_body.parent = rocket_pivot

bpy.ops.mesh.primitive_cone_add(radius1=0.2, depth=0.5, location=(rocket_dist, 0.75, 0))
rocket_tip = bpy.context.object
rocket_tip.rotation_euler = (math.radians(90), 0, 0)
rocket_tip.data.materials.append(mat_red)
rocket_tip.parent = rocket_pivot

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(rocket_dist, -0.6, 0))
rocket_engine = bpy.context.object
rocket_engine.data.materials.append(mat_glow)
rocket_engine.parent = rocket_pivot

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(rocket_dist, 0, 0.75))
rocket_target = bpy.context.object
rocket_target.parent = rocket_pivot

rock_txt = create_planet_label("Explorer", rocket_pivot, rocket_dist, 1.5, text_scale=0.8)

bpy.ops.object.camera_add(location=(rocket_dist + 5, -6, 3)) 
rock_cam = bpy.context.object
rock_cam.name = "Cam_Rocket"
rock_cam.data.lens = 45
rock_cam.parent = rocket_pivot

track_con = rock_cam.constraints.new('TRACK_TO')
track_con.target = rocket_target 
track_con.track_axis = 'TRACK_NEGATIVE_Z'
track_con.up_axis = 'UP_Y'

tour_stops.append((rock_txt, rock_cam))

# 4. Meteors
meteor_mat = bpy.data.materials.new("Meteor_Glow")
meteor_mat.use_nodes = True
meteor_mat.node_tree.nodes["Principled BSDF"].inputs['Emission Color'].default_value = (1.0, 0.5, 0.1, 1.0) 
meteor_mat.node_tree.nodes["Principled BSDF"].inputs['Emission Strength'].default_value = 25.0

for m in range(20): 
    bpy.ops.mesh.primitive_ico_sphere_add(radius=random.uniform(0.08, 0.18), subdivisions=1)
    meteor = bpy.context.object
    meteor.name = f"Meteor_{m}"
    meteor.data.materials.append(meteor_mat)
    meteor.scale = (1.0, random.uniform(2.0, 4.0), 1.0) 
    
    start_f = random.randint(1, TOTAL_FRAMES - 40)
    end_f = start_f + random.randint(12, 22) 
    
    start_loc = (random.uniform(-50, 50), random.uniform(60, 80), random.uniform(5, 25))
    end_loc = (start_loc[0] + random.uniform(-30, 30), start_loc[1] - random.uniform(120, 150), start_loc[2] - random.uniform(5, 15))
    
    meteor.location = start_loc
    meteor.hide_viewport = True
    meteor.hide_render = True
    meteor.keyframe_insert(data_path="location", frame=1)
    meteor.keyframe_insert(data_path="hide_viewport", frame=1)
    meteor.keyframe_insert(data_path="hide_render", frame=1)
    
    meteor.keyframe_insert(data_path="location", frame=start_f)
    meteor.hide_viewport = False
    meteor.hide_render = False
    meteor.keyframe_insert(data_path="hide_viewport", frame=start_f)
    meteor.keyframe_insert(data_path="hide_render", frame=start_f)
    
    meteor.location = end_loc
    meteor.keyframe_insert(data_path="location", frame=end_f)
    
    meteor.hide_viewport = True
    meteor.hide_render = True
    meteor.keyframe_insert(data_path="hide_viewport", frame=end_f + 1)
    meteor.keyframe_insert(data_path="hide_render", frame=end_f + 1)

# 5. Camera Animation
bpy.ops.object.camera_add()
render_cam = bpy.context.object
render_cam.name = "MASTER_RENDER_CAMERA"
scene.camera = render_cam

visit_sequence = [(None, main_cam)] + tour_stops + [(None, main_cam)]
constraints = []

for i, (txt, cam) in enumerate(visit_sequence):
    cr = render_cam.constraints.new('COPY_TRANSFORMS')
    cr.target = cam
    cr.name = f"Track_{i}"
    cr.influence = 0.0
    cr.keyframe_insert(data_path="influence", frame=1)
    constraints.append((cr, txt, cam))

constraints[0][0].influence = 1.0
constraints[0][0].keyframe_insert(data_path="influence", frame=1)
render_cam.data.lens = constraints[0][2].data.lens
render_cam.data.keyframe_insert(data_path="lens", frame=1)

current_frame = INTRO_HOLD 

for i in range(1, len(constraints)):
    cr, txt, target_cam = constraints[i]
    
    cr.influence = 0.0
    cr.keyframe_insert(data_path="influence", frame=current_frame)
    render_cam.data.keyframe_insert(data_path="lens", frame=current_frame)
    
    current_frame += TRANSITION_FRAMES
    
    cr.influence = 1.0
    cr.keyframe_insert(data_path="influence", frame=current_frame)
    render_cam.data.lens = target_cam.data.lens
    render_cam.data.keyframe_insert(data_path="lens", frame=current_frame)
    
    if txt:
        txt.hide_viewport = False
        txt.hide_render = False
        txt.keyframe_insert(data_path="hide_viewport", frame=current_frame)
        txt.keyframe_insert(data_path="hide_render", frame=current_frame)
        
    current_frame += HOLD_FRAMES
    
    if txt:
        txt.hide_viewport = True
        txt.hide_render = True
        txt.keyframe_insert(data_path="hide_viewport", frame=current_frame)
        txt.keyframe_insert(data_path="hide_render", frame=current_frame)

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'RENDERED'