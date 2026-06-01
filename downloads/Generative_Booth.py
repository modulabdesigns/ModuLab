bl_info = {
    "name": "Generative Booth",
    "author": "Arya Harditya","Graciella T.N.S."
    "version": (0, 0, 4),
    "blender": (5, 0, 0),
    "location": "3D Viewport > Sidebar > Generative Booth",
    "description": "Generative Booth Add-on",
    "category": "Development",
}

import bpy
import math
import random

blendMesh = bpy.ops.mesh
blendCtx = bpy.context

# ------------------------------------DEFS-----------------------------------

# ______________MATERIAL______________
            
def add_material(mat_name, col):
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    
    mat.diffuse_color = col
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    principled = nodes.get("Principled BSDF")
    if principled:
        principled.inputs[0].default_value = col
        
    return mat

def add_emission_material(mat_name, col, strength=1.0):
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear() 
    node_emission = nodes.new(type='ShaderNodeEmission')
    node_emission.inputs[0].default_value = col
    node_emission.inputs[1].default_value = strength 
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    links = mat.node_tree.links
    links.new(node_emission.outputs[0], node_output.inputs[0])
    mat.diffuse_color = col
    
    return mat

def get_or_create_collection(name):
    if name not in bpy.data.collections:
        new_col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(new_col)
    return bpy.data.collections[name]

def clear_previous_booth_elements():
    """Wipes out objects inside the booth collections to prevent mesh overlapping."""
    booth_collections = [
        "Booth_Structure",
        "Booth_Tables", 
        "Booth_Chairs", 
        "Booth_floorelement", 
        "Booth_CeilingElements", 
        "Booth_Poles",
        "Booth_Humans"
    ]
    
    for col_name in booth_collections:
        col = bpy.data.collections.get(col_name)
        if col:
            for obj in list(col.objects):
                bpy.data.objects.remove(obj, do_unlink=True)

def is_overlapping(x, y, current_obj, context, safety_margin=0.2):
    """
    Checks if placing current_obj at coordinate (x, y) overlaps with any existing objects,
    using true 3D AABB calculations (X, Y, and Z axes).
    """
    booth_collections = [
        "Booth_Tables", 
        "Booth_Chairs", 
        "Booth_floorelement", 
        "Booth_CeilingElements", 
        "Booth_Poles",
        "Booth_Humans"
    ]
    
    current_half_x = (current_obj.dimensions.x / 2.0) + safety_margin
    current_half_y = (current_obj.dimensions.y / 2.0) + safety_margin
    current_half_z = (current_obj.dimensions.z / 2.0)
    
    curr_min_x = x - current_half_x
    curr_max_x = x + current_half_x
    curr_min_y = y - current_half_y
    curr_max_y = y + current_half_y
    
    curr_min_z = current_obj.location.z - current_half_z
    curr_max_z = current_obj.location.z + current_half_z
    
    for col_name in booth_collections:
        col = bpy.data.collections.get(col_name)
        if not col:
            continue
            
        for other_obj in col.objects:
            if other_obj == current_obj:
                continue
                
            other_half_x = other_obj.dimensions.x / 2.0
            other_half_y = other_obj.dimensions.y / 2.0
            other_half_z = other_obj.dimensions.z / 2.0
            
            other_min_x = other_obj.location.x - other_half_x
            other_max_x = other_obj.location.x + other_half_x
            other_min_y = other_obj.location.y - other_half_y
            other_max_y = other_obj.location.y + other_half_y
            other_min_z = other_obj.location.z - other_half_z
            other_max_z = other_obj.location.z + other_half_z
            
            overlap_x = curr_min_x < other_max_x and curr_max_x > other_min_x
            overlap_y = curr_min_y < other_max_y and curr_max_y > other_min_y
            overlap_z = curr_min_z < other_max_z and curr_max_z > other_min_z
            
            if overlap_x and overlap_y and overlap_z:
                return True 
                
    return False


# ______________FLOOR______________

def add_floor_booth(width, length, height, color):
    if height <= 0.001:
        obj = bpy.data.objects.get("Booth_Floor")
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
        return
    
    obj = bpy.data.objects.get("Booth_Floor")
    
    if not obj:
        blendMesh.primitive_cube_add(size=1.0)
        obj = bpy.context.active_object
        obj.name = "Booth_Floor"
        
        col = get_or_create_collection("Booth_Structure")
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)
        for other_col in bpy.data.collections:
            if other_col.name != "Booth_Structure" and obj.name in other_col.objects:
                other_col.objects.unlink(obj)
        if obj.name not in col.objects:
            col.objects.link(obj)
            
        bpy.ops.object.editmode_toggle()
        blendMesh.subdivide(number_cuts=5)
        bpy.ops.object.editmode_toggle()

    obj.scale = (width, length, height)
    obj.location = (0, 0, height / 2.0)
    
    mat = add_material("floor_mat", color)
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
    
    return obj
        
def update_floor_color(self, context):
    props = context.scene.generative_booth_props
    floor_obj = bpy.data.objects.get("Booth_Floor")
    if floor_obj:
        mat = add_material("floor_mat", props.floor_color)
        if not floor_obj.data.materials:
            floor_obj.data.materials.append(mat)
        else:
            floor_obj.data.materials[0] = mat

# ______________ROOF______________

def add_roof_booth(width, length, height, master_height, color):
    obj = bpy.data.objects.get("Booth_Roof")
    
    if not obj:
        blendMesh.primitive_cube_add(size=1.0)
        obj = bpy.context.active_object
        obj.name = "Booth_Roof"
        target_col_name = "Booth_Structure"
        col = get_or_create_collection(target_col_name)
        
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)
            
        for other_col in bpy.data.collections:
            if other_col.name != target_col_name and obj.name in other_col.objects:
                other_col.objects.unlink(obj)
                
        if obj.name not in col.objects:
            col.objects.link(obj)
            
        bpy.ops.object.editmode_toggle()
        blendMesh.subdivide(number_cuts=5)
        bpy.ops.object.editmode_toggle()

    obj.scale = (width, length, height)
    obj.location = (0, 0, master_height - (height / 2.0))
    
    mat = add_material("roof_mat", color)
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
        
    return obj

def update_roof_color(self, context):
    props = context.scene.generative_booth_props
    roof_obj = bpy.data.objects.get("Booth_Roof")
    if roof_obj:
        mat = add_material("roof_mat", props.roof_color)
        if not roof_obj.data.materials:
            roof_obj.data.materials.append(mat)
        else:
            roof_obj.data.materials[0] = mat

# ______________WALL______________

def create_single_wall(wall_name, location, scale, rotation_degrees, color):
    obj = bpy.data.objects.get(wall_name)
    
    if not obj:
        blendMesh.primitive_cube_add(size=1.0)
        obj = bpy.context.active_object
        obj.name = wall_name
        
        target_col_name = "Booth_Structure"
        col = get_or_create_collection(target_col_name)
        
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)
            
        for other_col in bpy.data.collections:
            if other_col.name != target_col_name and obj.name in other_col.objects:
                other_col.objects.unlink(obj)
        if obj.name not in col.objects:
            col.objects.link(obj)

    obj.location = location
    obj.rotation_euler = (
        math.radians(rotation_degrees[0]), 
        math.radians(rotation_degrees[1]), 
        math.radians(rotation_degrees[2])
    )
    obj.scale = scale 
    
    mat = add_material(f"{wall_name}_mat", color)
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
    
    bpy.ops.object.select_all(action='DESELECT')
    return obj

def add_all_walls(props):
    dynamic_height = props.booth_master_height - props.floor_height - props.roof_height
    wall_z_pos = props.floor_height + (dynamic_height / 2.0)
    
    props.back_wall_height = dynamic_height
    props.left_wall_height = dynamic_height
    props.right_wall_height = dynamic_height
    
    back_y_pos = props.floor_length / 2.0 - props.back_wall_width / 2.0
    
    create_single_wall(
        wall_name="Booth_Wall_Back",
        location=(0, back_y_pos, wall_z_pos), 
        scale=(props.back_wall_length, props.back_wall_width, dynamic_height),
        rotation_degrees=(0, 0, 0), 
        color=props.back_wall_color 
    )

    left_x_pos = props.floor_width / 2.0 - props.left_wall_width / 2.0
    create_single_wall(
        wall_name="Booth_Wall_Left",
        location=(left_x_pos, 0, wall_z_pos), 
        scale=(props.left_wall_width, props.left_wall_length, dynamic_height),
        rotation_degrees=(0, 0, 0), 
        color=props.left_wall_color
    )

    right_x_pos = -props.floor_width / 2.0 + props.right_wall_width / 2.0
    create_single_wall(
        wall_name="Booth_Wall_Right",
        location=(right_x_pos, 0, wall_z_pos),
        scale=(props.right_wall_width, props.right_wall_length, dynamic_height),
        rotation_degrees=(0, 0, 0), 
        color=props.right_wall_color
    )
    
    props.update_back_wall_dimensions(bpy.context)
    props.update_left_wall_dimensions(bpy.context)
    props.update_right_wall_dimensions(bpy.context)

def toggle_wall_visibility(wall_name, visible):
    try:
        wall_obj = bpy.data.objects[wall_name]
        wall_obj.hide_set(not visible)
        wall_obj.hide_render = not visible
    except KeyError:
        pass

# ______________BOOTH ELEMENTS______________

#_____TABLE_____
def create_table_mesh(table_type):
    if table_type == 'TABLE_A':
        verts = [(0.5343, 0.2798, -0.0), (0.5654, 0.2798, -0.0), (0.5343, 0.2798, 0.7279), (0.5654, 0.2798, 0.7279), (0.5654, 0.2483, 0.7279), (0.5654, 0.2483, -0.0), (0.5343, 0.2483, -0.0), (0.5343, 0.2483, 0.7279), (0.5628, 0.2659, 0.544), (0.5369, 0.2659, 0.544), (0.5628, 0.2659, 0.519), (0.5369, 0.2659, 0.519), (0.5607, 0.1646, 0.5323), (0.5437, 0.1646, 0.5323), (0.5607, 0.133, 0.5323), (0.5437, 0.133, 0.5323), (0.3447, 0.1646, 0.7315), (0.3276, 0.1646, 0.7315), (0.3447, 0.133, 0.7315), (0.3276, 0.133, 0.7315), (0.3884, 0.1457, 0.6894), (0.3749, 0.1457, 0.6894), (0.3979, 0.1457, 0.6803), (0.3848, 0.1457, 0.6803), (-0.5343, 0.2798, -0.0), (-0.5654, 0.2798, -0.0), (-0.5343, 0.2798, 0.7279), (-0.5654, 0.2798, 0.7279), (-0.5654, 0.2483, 0.7279), (-0.5654, 0.2483, -0.0), (-0.5343, 0.2483, -0.0), (-0.5343, 0.2483, 0.7279), (-0.5628, 0.2659, 0.544), (-0.5369, 0.2659, 0.544), (-0.5628, 0.2659, 0.519), (-0.5369, 0.2659, 0.519), (-0.5607, 0.1646, 0.5323), (-0.5437, 0.1646, 0.5323), (-0.5607, 0.133, 0.5323), (-0.5437, 0.133, 0.5323), (-0.3447, 0.1646, 0.7315), (-0.3276, 0.1646, 0.7315), (-0.3447, 0.133, 0.7315), (-0.3276, 0.133, 0.7315), (-0.3884, 0.1457, 0.6894), (-0.3749, 0.1457, 0.6894), (-0.3979, 0.1457, 0.6803), (-0.3848, 0.1457, 0.6803), (0.5343, -0.2798, -0.0), (0.5654, -0.2798, -0.0), (0.5343, -0.2798, 0.7279), (0.5654, -0.2798, 0.7279), (0.5654, -0.2483, 0.7279), (0.5654, -0.2483, -0.0), (0.5343, -0.2483, -0.0), (0.5343, -0.2483, 0.7279), (0.5628, -0.2659, 0.544), (0.5369, -0.2659, 0.544), (0.5628, -0.2659, 0.519), (0.5369, -0.2659, 0.519), (0.5607, -0.1646, 0.5323), (0.5437, -0.1646, 0.5323), (0.5607, -0.133, 0.5323), (0.5437, -0.133, 0.5323), (0.3447, -0.1646, 0.7315), (0.3276, -0.1646, 0.7315), (0.3447, -0.133, 0.7315), (0.3276, -0.133, 0.7315), (0.3884, -0.1457, 0.6894), (0.3749, -0.1457, 0.6894), (0.3979, -0.1457, 0.6803), (0.3848, -0.1457, 0.6803), (-0.5343, -0.2798, -0.0), (-0.5654, -0.2798, -0.0), (-0.5343, -0.2798, 0.7279), (-0.5654, -0.2798, 0.7279), (-0.5654, -0.2483, 0.7279), (-0.5654, -0.2483, -0.0), (-0.5343, -0.2483, -0.0), (-0.5343, -0.2483, 0.7279), (-0.5628, -0.2659, 0.544), (-0.5369, -0.2659, 0.544), (-0.5628, -0.2659, 0.519), (-0.5369, -0.2659, 0.519), (-0.5607, -0.1646, 0.5323), (-0.5437, -0.1646, 0.5323), (-0.5607, -0.133, 0.5323), (-0.5437, -0.133, 0.5323), (-0.3447, -0.1646, 0.7315), (-0.3276, -0.1646, 0.7315), (-0.3447, -0.133, 0.7315), (-0.3276, -0.133, 0.7315), (-0.3884, -0.1457, 0.6894), (-0.3749, -0.1457, 0.6894), (-0.3979, -0.1457, 0.6803), (-0.3848, -0.1457, 0.6803), (-0.6, -0.3, 0.75), (-0.6, 0.3, 0.75), (0.6, -0.3, 0.75), (0.6, 0.3, 0.75), (-0.6, -0.3, 0.7211), (-0.6, 0.3, 0.7211), (0.6, 0.3, 0.7211), (0.6, -0.3, 0.7211)]
        faces = [(0, 2, 3, 1), (6, 5, 4, 7), (0, 1, 5, 6), (1, 3, 4, 5), (3, 2, 7, 4), (0, 6, 7, 2), (9, 8, 10, 11), (69, 68, 20, 21), (56, 58, 10, 8), (59, 57, 9, 11), (58, 59, 11, 10), (13, 12, 14, 15), (17, 19, 18, 16), (15, 19, 17, 13), (14, 18, 19, 15), (12, 16, 18, 14), (13, 17, 16, 12), (21, 20, 22, 23), (81, 33, 32, 80), (68, 70, 22, 20), (71, 69, 21, 23), (70, 71, 23, 22), (24, 25, 27, 26), (30, 31, 28, 29), (24, 30, 29, 25), (25, 29, 28, 27), (27, 28, 31, 26), (24, 26, 31, 30), (33, 35, 34, 32), (93, 45, 44, 92), (80, 32, 34, 82), (83, 35, 33, 81), (82, 34, 35, 83), (37, 39, 38, 36), (41, 40, 42, 43), (39, 37, 41, 43), (38, 39, 43, 42), (36, 38, 42, 40), (37, 36, 40, 41), (45, 47, 46, 44), (92, 44, 46, 94), (95, 47, 45, 93), (94, 46, 47, 95), (48, 49, 51, 50), (54, 55, 52, 53), (48, 54, 53, 49), (49, 53, 52, 51), (51, 52, 55, 50), (48, 50, 55, 54), (57, 59, 58, 56), (61, 63, 62, 60), (65, 64, 66, 67), (63, 61, 65, 67), (62, 63, 67, 66), (60, 62, 66, 64), (61, 60, 64, 65), (69, 71, 70, 68), (72, 74, 75, 73), (78, 77, 76, 79), (72, 73, 77, 78), (73, 75, 76, 77), (75, 74, 79, 76), (72, 78, 79, 74), (81, 80, 82, 83), (85, 84, 86, 87), (89, 91, 90, 88), (87, 91, 89, 85), (86, 90, 91, 87), (84, 88, 90, 86), (85, 89, 88, 84), (93, 92, 94, 95), (100, 96, 97, 101), (101, 97, 99, 102), (102, 99, 98, 103), (103, 98, 96, 100), (99, 97, 96, 98), (101, 102, 103, 100), (57, 56, 8, 9)]
    
    elif table_type == 'TABLE_B':
        verts = [(-0.4692, 0.2906, 0.75), (-0.4692, -0.2094, 0.0), (-0.4692, 0.2906, 0.0), (-0.4692, -0.2094, 0.75), (-0.5, 0.2906, 0.0), (-0.5, 0.2906, 0.75), (-0.5, -0.2094, 0.0), (-0.5, -0.2094, 0.75), (-0.4692, 0.2602, 0.0), (-0.5, 0.2602, 0.0), (-0.5, 0.2602, 0.75), (-0.4692, 0.2602, 0.75), (-0.4692, -0.2094, 0.7181), (-0.4692, 0.2906, 0.7181), (-0.5, -0.2094, 0.7181), (-0.5, 0.2906, 0.7181), (-0.5, 0.2602, 0.7181), (-0.4692, -0.2094, 0.0352), (-0.4692, 0.2906, 0.0352), (-0.5, -0.2094, 0.0352), (-0.5, 0.2906, 0.0352), (-0.5, 0.2602, 0.0352), (-0.5, -0.181, 0.0), (-0.4692, -0.181, 0.0), (-0.5, -0.181, 0.75), (-0.4692, -0.181, 0.75), (-0.5, -0.181, 0.0352), (-0.4692, 0.2602, 0.7181), (-0.4692, 0.2602, 0.0352), (-0.4692, -0.181, 0.0352), (-0.5, -0.181, 0.7181), (-0.4692, -0.181, 0.7181), (-0.4921, 0.2726, 0.7345), (-0.4921, -0.1934, 0.7345), (-0.4921, 0.2726, 0.0163), (-0.4921, -0.1934, 0.0163), (-0.4787, -0.1934, 0.7345), (-0.4787, 0.2726, 0.7345), (-0.4787, -0.1934, 0.0163), (-0.4787, 0.2726, 0.0163), (-0.4766, -0.2038, 0.7246), (-0.4766, -0.2038, 0.0287), (-0.4766, -0.1883, 0.7246), (-0.4766, -0.1883, 0.0287), (-0.4727, 0.2743, 0.7448), (-0.4727, -0.1951, 0.7448), (-0.4727, 0.2743, 0.7298), (-0.4727, -0.1951, 0.7298), (0.4692, 0.2906, 0.75), (0.4692, -0.2094, 0.0), (0.4692, 0.2906, 0.0), (0.4692, -0.2094, 0.75), (0.5, 0.2906, 0.0), (0.5, 0.2906, 0.75), (0.5, -0.2094, 0.0), (0.5, -0.2094, 0.75), (0.4692, 0.2602, 0.0), (0.5, 0.2602, 0.0), (0.5, 0.2602, 0.75), (0.4692, 0.2602, 0.75), (0.4692, -0.2094, 0.7181), (0.4692, 0.2906, 0.7181), (0.5, -0.2094, 0.7181), (0.5, 0.2906, 0.7181), (0.5, 0.2602, 0.7181), (0.4692, -0.2094, 0.0352), (0.4692, 0.2906, 0.0352), (0.5, -0.2094, 0.0352), (0.5, 0.2906, 0.0352), (0.5, 0.2602, 0.0352), (0.5, -0.181, 0.0), (0.4692, -0.181, 0.0), (0.5, -0.181, 0.75), (0.4692, -0.181, 0.75), (0.5, -0.181, 0.0352), (0.4692, 0.2602, 0.7181), (0.4692, 0.2602, 0.0352), (0.4692, -0.181, 0.0352), (0.5, -0.181, 0.7181), (0.4692, -0.181, 0.7181), (0.4921, 0.2726, 0.7345), (0.4921, -0.1934, 0.7345), (0.4921, 0.2726, 0.0163), (0.4921, -0.1934, 0.0163), (0.4787, -0.1934, 0.7345), (0.4787, 0.2726, 0.7345), (0.4787, -0.1934, 0.0163), (0.4787, 0.2726, 0.0163), (0.4766, -0.2038, 0.7246), (0.4766, -0.2038, 0.0287), (0.4766, -0.1883, 0.7246), (0.4766, -0.1883, 0.0287), (0.4727, 0.2743, 0.7448), (0.4727, -0.1951, 0.7448), (0.4727, 0.2743, 0.7298), (0.4727, -0.1951, 0.7298)]
        faces = [(51, 73, 25, 3), (12, 3, 7, 14), (16, 10, 5, 15), (8, 9, 4, 2), (10, 11, 0, 5), (61, 13, 0, 48), (1, 49, 65, 17), (59, 11, 27, 75), (15, 5, 0, 13), (24, 25, 11, 10), (23, 22, 9, 8), (30, 24, 10, 16), (2, 18, 28, 8), (20, 15, 13, 18), (21, 16, 15, 20), (17, 12, 14, 19), (18, 13, 27, 28), (23, 71, 49, 1), (1, 17, 19, 6), (9, 21, 20, 4), (4, 20, 18, 2), (22, 26, 21, 9), (6, 19, 26, 22), (19, 14, 30, 26), (14, 7, 24, 30), (29, 77, 71, 23), (1, 6, 22, 23), (7, 3, 25, 24), (79, 31, 25, 73), (75, 27, 13, 61), (23, 8, 28, 29), (29, 28, 21, 26), (16, 21, 28, 27), (29, 26, 30, 31), (27, 31, 30, 16), (25, 31, 27, 11), (17, 65, 77, 29), (17, 29, 31, 12), (60, 12, 31, 79), (32, 34, 35, 33), (37, 36, 38, 39), (33, 35, 38, 36), (35, 34, 39, 38), (34, 32, 37, 39), (32, 33, 36, 37), (41, 40, 42, 43), (89, 88, 40, 41), (88, 90, 42, 40), (90, 91, 43, 42), (92, 44, 45, 93), (91, 89, 41, 43), (44, 46, 47, 45), (94, 46, 44, 92), (93, 45, 47, 95), (95, 47, 46, 94), (60, 62, 55, 51), (64, 63, 53, 58), (56, 50, 52, 57), (58, 53, 48, 59), (63, 61, 48, 53), (72, 58, 59, 73), (71, 56, 57, 70), (78, 64, 58, 72), (50, 56, 76, 66), (68, 66, 61, 63), (69, 68, 63, 64), (65, 67, 62, 60), (66, 76, 75, 61), (49, 54, 67, 65), (57, 52, 68, 69), (52, 50, 66, 68), (70, 57, 69, 74), (54, 70, 74, 67), (67, 74, 78, 62), (62, 78, 72, 55), (49, 71, 70, 54), (55, 72, 73, 51), (71, 77, 76, 56), (77, 74, 69, 76), (64, 75, 76, 69), (77, 79, 78, 74), (75, 64, 78, 79), (73, 59, 75, 79), (65, 60, 79, 77), (80, 81, 83, 82), (85, 87, 86, 84), (81, 84, 86, 83), (83, 86, 87, 82), (82, 87, 85, 80), (80, 85, 84, 81), (89, 91, 90, 88), (92, 93, 95, 94), (59, 48, 0, 11), (12, 60, 51, 3)]
        
    elif table_type == 'TABLE_C':
        verts = [(0.0, 0.3, 0.72), (0.1148, 0.2772, 0.72), (0.2121, 0.2121, 0.72), (0.2772, 0.1148, 0.72), (0.3, 0.0, 0.72), (0.2772, -0.1148, 0.72), (0.2121, -0.2121, 0.72), (0.1148, -0.2772, 0.72), (0.0, -0.3, 0.72), (-0.1148, -0.2772, 0.72), (-0.2121, -0.2121, 0.72), (-0.2772, -0.1148, 0.72), (-0.3, 0.0, 0.72), (-0.2772, 0.1148, 0.72), (-0.2121, 0.2121, 0.72), (-0.1148, 0.2772, 0.72), (0.0052, 0.2173, 0.72), (0.1218, 0.1218, 0.72), (0.2173, 0.0052, 0.72), (-0.1148, 0.1148, 0.72), (-0.0, 0.0, 0.72), (0.1148, -0.1148, 0.72), (-0.2173, -0.0052, 0.72), (-0.1218, -0.1218, 0.72), (-0.0052, -0.2173, 0.72), (0.0, 0.3, 0.676), (0.1148, 0.2772, 0.676), (0.2121, 0.2121, 0.676), (0.2772, 0.1148, 0.676), (0.3, 0.0, 0.676), (0.2772, -0.1148, 0.676), (0.2121, -0.2121, 0.676), (0.1148, -0.2772, 0.676), (0.0, -0.3, 0.676), (-0.1148, -0.2772, 0.676), (-0.2121, -0.2121, 0.676), (-0.2772, -0.1148, 0.676), (-0.3, 0.0, 0.676), (-0.2772, 0.1148, 0.676), (-0.2121, 0.2121, 0.676), (-0.1148, 0.2772, 0.676), (0.0052, 0.2173, 0.676), (0.1218, 0.1218, 0.676), (0.2173, 0.0052, 0.676), (-0.1148, 0.1148, 0.676), (-0.0, 0.0, 0.676), (0.1148, -0.1148, 0.676), (-0.2173, -0.0052, 0.676), (-0.1218, -0.1218, 0.676), (-0.0052, -0.2173, 0.676), (-0.0, 0.0238, 0.0167), (-0.0, 0.0238, 0.6901), (0.0169, 0.0169, 0.0167), (0.0169, 0.0169, 0.6901), (0.0238, 0.0, 0.0167), (0.0238, 0.0, 0.6901), (0.0169, -0.0169, 0.0167), (0.0169, -0.0169, 0.6901), (-0.0, -0.0238, 0.0167), (-0.0, -0.0238, 0.6901), (-0.0169, -0.0169, 0.0167), (-0.0169, -0.0169, 0.6901), (-0.0238, 0.0, 0.0167), (-0.0238, 0.0, 0.6901), (-0.0169, 0.0169, 0.0167), (-0.0169, 0.0169, 0.6901), (0.0, 0.1492, 0.0), (0.0, 0.1492, 0.022), (0.1055, 0.1055, 0.0), (0.1055, 0.1055, 0.022), (0.1492, 0.0, 0.0), (0.1492, 0.0, 0.022), (0.1055, -0.1055, 0.0), (0.1055, -0.1055, 0.022), (0.0, -0.1492, 0.0), (0.0, -0.1492, 0.022), (-0.1055, -0.1055, 0.0), (-0.1055, -0.1055, 0.022), (-0.1492, 0.0, 0.0), (-0.1492, 0.0, 0.022), (-0.1055, 0.1055, 0.0), (-0.1055, 0.1055, 0.022), (-0.0, -0.0, 0.022), (-0.0, 0.0, 0.0)]
        faces = [(1, 0, 15, 16), (16, 15, 14, 19), (19, 14, 13, 22), (22, 13, 12, 11), (2, 1, 16, 17), (17, 16, 19, 20), (20, 19, 22, 23), (23, 22, 11, 10), (3, 2, 17, 18), (18, 17, 20, 21), (21, 20, 23, 24), (24, 23, 10, 9), (4, 3, 18, 5), (5, 18, 21, 6), (6, 21, 24, 7), (7, 24, 9, 8), (26, 41, 40, 25), (41, 44, 39, 40), (44, 47, 38, 39), (47, 36, 37, 38), (27, 42, 41, 26), (42, 45, 44, 41), (45, 48, 47, 44), (48, 35, 36, 47), (28, 43, 42, 27), (43, 46, 45, 42), (46, 49, 48, 45), (49, 34, 35, 48), (29, 30, 43, 28), (30, 31, 46, 43), (31, 32, 49, 46), (32, 33, 34, 49), (15, 0, 25, 40), (8, 9, 34, 33), (1, 2, 27, 26), (9, 10, 35, 34), (2, 3, 28, 27), (10, 11, 36, 35), (3, 4, 29, 28), (11, 12, 37, 36), (4, 5, 30, 29), (12, 13, 38, 37), (5, 6, 31, 30), (13, 14, 39, 38), (6, 7, 32, 31), (14, 15, 40, 39), (7, 8, 33, 32), (0, 1, 26, 25), (50, 51, 53, 52), (52, 53, 55, 54), (54, 55, 57, 56), (56, 57, 59, 58), (58, 59, 61, 60), (60, 61, 63, 62), (62, 63, 65, 64), (64, 65, 51, 50), (66, 67, 69, 68), (68, 69, 71, 70), (70, 71, 73, 72), (72, 73, 75, 74), (74, 75, 77, 76), (76, 77, 79, 78), (78, 79, 81, 80), (80, 81, 67, 66), (71, 69, 82, 73), (69, 67, 81, 82), (73, 82, 77, 75), (82, 81, 79, 77), (70, 72, 83, 68), (72, 74, 76, 83), (68, 83, 80, 66), (83, 76, 78, 80)]
        
    else:
        verts = [(-0.0, 0.0239, 0.0167), (-0.0, 0.0239, 0.6901), (0.0169, 0.0169, 0.0167), (0.0169, 0.0169, 0.6901), (0.0239, 0.0, 0.0167), (0.0239, 0.0, 0.6901), (0.0169, -0.0169, 0.0167), (0.0169, -0.0169, 0.6901), (-0.0, -0.0239, 0.0167), (-0.0, -0.0239, 0.6901), (-0.0169, -0.0169, 0.0167), (-0.0169, -0.0169, 0.6901), (-0.0239, 0.0, 0.0167), (-0.0239, 0.0, 0.6901), (-0.0169, 0.0169, 0.0167), (-0.0169, 0.0169, 0.6901), (0.1547, 0.1547, 0.0294), (0.1547, 0.1547, -0.0), (0.1547, -0.1547, 0.0294), (0.1547, -0.1547, -0.0), (-0.1547, 0.1547, 0.0294), (-0.1547, 0.1547, -0.0), (-0.1547, -0.1547, 0.0294), (-0.1547, -0.1547, -0.0), (-0.3, -0.3, 0.6771), (-0.3, -0.3, 0.72), (-0.3, 0.3, 0.6771), (-0.3, 0.3, 0.72), (0.3, -0.3, 0.6771), (0.3, -0.3, 0.72), (0.3, 0.3, 0.6771), (0.3, 0.3, 0.72)]
        faces = [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6), (6, 7, 9, 8), (8, 9, 11, 10), (10, 11, 13, 12), (12, 13, 15, 14), (14, 15, 1, 0), (21, 17, 19, 23), (19, 18, 22, 23), (23, 22, 20, 21), (16, 20, 22, 18), (21, 20, 16, 17), (17, 16, 18, 19), (24, 25, 27, 26), (26, 27, 31, 30), (30, 31, 29, 28), (28, 29, 25, 24), (26, 30, 28, 24), (31, 27, 25, 29)]
        
    return verts, faces

def update_table_count(self, context):
    props = context.scene.generative_booth_props
    if getattr(props, "programmatic_update", False):
        return

    col = get_or_create_collection("Booth_Tables")
    current_objects = list(col.objects)
    
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_Table_"):
        target_type = active_obj.individual_table_type
        target_color = active_obj.individual_table_color
    else:
        target_type = props.table_type
        target_color = props.table_color

    matching_objs = [o for o in current_objects if getattr(o, "individual_table_type", "") == target_type]
    count_needed = props.table_count

    while len(matching_objs) > count_needed:
        obj_to_remove = matching_objs[-1]
        
        if context.active_object == obj_to_remove:
            remaining_companions = [o for o in matching_objs if o != obj_to_remove]
            if remaining_companions:
                context.view_layer.objects.active = remaining_companions[-1]
                remaining_companions[-1].select_set(True)
            else:
                context.view_layer.objects.active = None
                
        matching_objs.remove(obj_to_remove)
        bpy.data.objects.remove(obj_to_remove, do_unlink=True)

    while len(matching_objs) < count_needed:
        new_index = len(col.objects)
        
        new_obj = add_table_booth(
            target_type, 
            props.floor_width, 
            props.floor_length, 
            props.floor_height,
            props.table_rotation_random,
            new_index
        )
        
        new_obj.individual_table_type = target_type
        new_obj.individual_table_color = target_color
        matching_objs.append(new_obj)

def update_table_style(self, context):
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_Tables")
    
    verts, faces = create_table_mesh(props.table_type)
    mat = add_material("Booth_Table_Mat", props.table_color)
    
    for obj in col.objects:
        obj.data.clear_geometry()
        obj.data.from_pydata(verts, [], faces)
        obj.data.update()
        obj.location.z = props.floor_height
        if not obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

def add_table_booth(table_type, floor_width, floor_length, floor_height, rot_random, index):
    verts, faces = create_table_mesh(table_type)
    mesh_data = bpy.data.meshes.new(f"Table_Mesh_{index}")
    mesh_data.from_pydata(verts, [], faces)
    mesh_data.update()
    
    obj = bpy.data.objects.new(f"Booth_Table_{index}", mesh_data)
    col = get_or_create_collection("Booth_Tables")
    col.objects.link(obj)

    props = bpy.context.scene.generative_booth_props
    obj.individual_table_type = table_type
    obj.individual_table_color = props.table_color
    
    bpy.context.view_layer.update()

    margin = 0.5
    x_max = (floor_width / 2.0) - margin
    y_max = (floor_length / 2.0) - margin
    
    for _ in range(100):
        new_x = random.uniform(-x_max, x_max)
        new_y = random.uniform(-y_max, y_max)
        if not is_overlapping(new_x, new_y, obj, bpy.context, safety_margin=0.8):
            obj.location.x = new_x
            obj.location.y = new_y
            break
    else:
        obj.location.x = random.uniform(-x_max, x_max)
        obj.location.y = random.uniform(-y_max, y_max)
        
    obj.location.z = floor_height
    
    rotation_intensity = rot_random * 3.0
    random.seed(index + 200) 
    rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
    obj.rotation_euler.z = math.radians(rand_angle)
    
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj

def update_table_rotation(self, context):
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_Tables")
    
    rotation_intensity = props.table_rotation_random * 3.0
    
    for i, obj in enumerate(col.objects):
        random.seed(i + 200)
        rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
        obj.rotation_euler.z = math.radians(rand_angle)
        
def update_individual_table_style(self, context):
    """Triggers whenever a clicked table changes its type or color tint."""
    if not self or self.type != 'MESH':
        return
        
    props = context.scene.generative_booth_props
        
    verts, faces = create_table_mesh(self.individual_table_type)
    self.data.clear_geometry()
    self.data.from_pydata(verts, [], faces)
    self.data.update()
    
    current_type = self.individual_table_type
    matching_count = sum(
        1 for o in context.scene.objects 
        if o.name.startswith("Booth_Table_") 
        and getattr(o, "individual_table_type", "") == current_type
    )
    
    props.programmatic_update = True
    props.table_count = matching_count
    props.programmatic_update = False
    
    mat_name = f"Mat_{self.name}_Unique"
    color_tuple = (
        self.individual_table_color[0],
        self.individual_table_color[1],
        self.individual_table_color[2],
        self.individual_table_color[3]
    )
    
    mat = add_material(mat_name, color_tuple)
    if not self.data.materials:
        self.data.materials.append(mat)
    else:
        self.data.materials[0] = mat
        
def sync_ui_on_table_selection_change(scene):
    """Safely updates the count slider when a user selects a different table type."""
    context = bpy.context
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_Table_"):
        props = context.scene.generative_booth_props
        current_type = getattr(active_obj, "individual_table_type", "")
        
        matching_count = sum(
            1 for o in context.scene.objects 
            if o.name.startswith("Booth_Table_") 
            and getattr(o, "individual_table_type", "") == current_type
        )
        
        if props.table_count != matching_count:
            props.programmatic_update = True
            props.table_count = matching_count
            props.programmatic_update = False


#_____CHAIR_____

def create_chair_mesh(chair_type):
    if chair_type == 'CHAIR_A':
        verts = [(0.1211, 0.1321, 0.0069), (0.1211, 0.1321, 0.5198), (0.1317, 0.143, 0.0069), (0.1317, 0.143, 0.5198), (0.1321, 0.1215, 0.0069), (0.1321, 0.1215, 0.5198), (0.1426, 0.1325, 0.0069), (0.1426, 0.1325, 0.5198), (-0.1211, 0.1321, 0.0069), (-0.1211, 0.1321, 0.5198), (-0.1317, 0.143, 0.0069), (-0.1317, 0.143, 0.5198), (-0.1321, 0.1215, 0.0069), (-0.1321, 0.1215, 0.5198), (-0.1426, 0.1325, 0.0069), (-0.1426, 0.1325, 0.5198), (0.1211, -0.1321, 0.0069), (0.1211, -0.1321, 0.5198), (0.1317, -0.143, 0.0069), (0.1317, -0.143, 0.5198), (0.1321, -0.1215, 0.0069), (0.1321, -0.1215, 0.5198), (0.1426, -0.1325, 0.0069), (0.1426, -0.1325, 0.5198), (-0.1211, -0.1321, 0.0069), (-0.1211, -0.1321, 0.5198), (-0.1317, -0.143, 0.0069), (-0.1317, -0.143, 0.5198), (-0.1321, -0.1215, 0.0069), (-0.1321, -0.1215, 0.5198), (-0.1426, -0.1325, 0.0069), (-0.1426, -0.1325, 0.5198), (-0.0, 0.185, 0.5653), (0.0708, 0.1709, 0.5653), (0.1308, 0.1308, 0.5653), (0.1709, 0.0708, 0.5653), (0.185, 0.0, 0.5653), (0.1709, -0.0708, 0.5653), (0.1308, -0.1308, 0.5653), (0.0708, -0.1709, 0.5653), (-0.0, -0.185, 0.5653), (-0.0708, -0.1709, 0.5653), (-0.1308, -0.1308, 0.5653), (-0.1709, -0.0708, 0.5653), (-0.185, 0.0, 0.5653), (-0.1709, 0.0708, 0.5653), (-0.1308, 0.1308, 0.5653), (-0.0708, 0.1709, 0.5653), (0.0032, 0.134, 0.5653), (0.0751, 0.0751, 0.5653), (0.134, 0.0032, 0.5653), (-0.0708, 0.0708, 0.5653), (-0.0, 0.0, 0.5653), (0.0708, -0.0708, 0.5653), (-0.134, -0.0032, 0.5653), (-0.0751, -0.0751, 0.5653), (-0.0032, -0.134, 0.5653), (-0.0, 0.185, 0.5155), (0.0708, 0.1709, 0.5155), (0.1308, 0.1308, 0.5155), (0.1709, 0.0708, 0.5155), (0.185, 0.0, 0.5155), (0.1709, -0.0708, 0.5155), (0.1308, -0.1308, 0.5155), (0.0708, -0.1709, 0.5155), (-0.0, -0.185, 0.5155), (-0.0708, -0.1709, 0.5155), (-0.1308, -0.1308, 0.5155), (-0.1709, -0.0708, 0.5155), (-0.185, 0.0, 0.5155), (-0.1709, 0.0708, 0.5155), (-0.1308, 0.1308, 0.5155), (-0.0708, 0.1709, 0.5155), (0.0032, 0.134, 0.5155), (0.0751, 0.0751, 0.5155), (0.134, 0.0032, 0.5155), (-0.0708, 0.0708, 0.5155), (-0.0, 0.0, 0.5155), (0.0708, -0.0708, 0.5155), (-0.134, -0.0032, 0.5155), (-0.0751, -0.0751, 0.5155), (-0.0032, -0.134, 0.5155), (-0.0, 0.199, 0.5241), (0.0762, 0.1839, 0.5241), (0.1407, 0.1407, 0.5241), (0.1839, 0.0762, 0.5241), (0.199, 0.0, 0.5241), (0.1839, -0.0762, 0.5241), (0.1407, -0.1407, 0.5241), (0.0762, -0.1839, 0.5241), (-0.0, -0.199, 0.5241), (-0.0762, -0.1839, 0.5241), (-0.1407, -0.1407, 0.5241), (-0.1839, -0.0762, 0.5241), (-0.199, 0.0, 0.5241), (-0.1839, 0.0762, 0.5241), (-0.1407, 0.1407, 0.5241), (-0.0762, 0.1839, 0.5241), (-0.0, 0.1788, 0.5241), (0.0684, 0.1652, 0.5241), (0.1265, 0.1265, 0.5241), (0.1652, 0.0684, 0.5241), (0.1788, 0.0, 0.5241), (0.1652, -0.0684, 0.5241), (0.1265, -0.1265, 0.5241), (0.0684, -0.1652, 0.5241), (-0.0, -0.1788, 0.5241), (-0.0684, -0.1652, 0.5241), (-0.1265, -0.1265, 0.5241), (-0.1652, -0.0684, 0.5241), (-0.1788, 0.0, 0.5241), (-0.1652, 0.0684, 0.5241), (-0.1265, 0.1265, 0.5241), (-0.0684, 0.1652, 0.5241), (-0.0, 0.199, 0.5096), (0.0762, 0.1839, 0.5096), (0.1407, 0.1407, 0.5096), (0.1839, 0.0762, 0.5096), (0.199, 0.0, 0.5096), (0.1839, -0.0762, 0.5096), (0.1407, -0.1407, 0.5096), (0.0762, -0.1839, 0.5096), (-0.0, -0.199, 0.5096), (-0.0762, -0.1839, 0.5096), (-0.1407, -0.1407, 0.5096), (-0.1839, -0.0762, 0.5096), (-0.199, 0.0, 0.5096), (-0.1839, 0.0762, 0.5096), (-0.1407, 0.1407, 0.5096), (-0.0762, 0.1839, 0.5096), (-0.0, 0.1788, 0.5096), (0.0684, 0.1652, 0.5096), (0.1265, 0.1265, 0.5096), (0.1652, 0.0684, 0.5096), (0.1788, 0.0, 0.5096), (0.1652, -0.0684, 0.5096), (0.1265, -0.1265, 0.5096), (0.0684, -0.1652, 0.5096), (-0.0, -0.1788, 0.5096), (-0.0684, -0.1652, 0.5096), (-0.1265, -0.1265, 0.5096), (-0.1652, -0.0684, 0.5096), (-0.1788, 0.0, 0.5096), (-0.1652, 0.0684, 0.5096), (-0.1265, 0.1265, 0.5096), (-0.0684, 0.1652, 0.5096), (-0.0, 0.199, 0.019), (0.0762, 0.1839, 0.019), (0.1407, 0.1407, 0.019), (0.1839, 0.0762, 0.019), (0.199, 0.0, 0.019), (0.1839, -0.0762, 0.019), (0.1407, -0.1407, 0.019), (0.0762, -0.1839, 0.019), (-0.0, -0.199, 0.019), (-0.0762, -0.1839, 0.019), (-0.1407, -0.1407, 0.019), (-0.1839, -0.0762, 0.019), (-0.199, 0.0, 0.019), (-0.1839, 0.0762, 0.019), (-0.1407, 0.1407, 0.019), (-0.0762, 0.1839, 0.019), (-0.0, 0.1754, 0.019), (0.0671, 0.1621, 0.019), (0.1241, 0.1241, 0.019), (0.1621, 0.0671, 0.019), (0.1754, 0.0, 0.019), (0.1621, -0.0671, 0.019), (0.1241, -0.1241, 0.019), (0.0671, -0.1621, 0.019), (-0.0, -0.1754, 0.019), (-0.0671, -0.1621, 0.019), (-0.1241, -0.1241, 0.019), (-0.1621, -0.0671, 0.019), (-0.1754, 0.0, 0.019), (-0.1621, 0.0671, 0.019), (-0.1241, 0.1241, 0.019), (-0.0671, 0.1621, 0.019), (-0.0, 0.199, 0.0), (0.0762, 0.1839, 0.0), (0.1407, 0.1407, 0.0), (0.1839, 0.0762, 0.0), (0.199, 0.0, 0.0), (0.1839, -0.0762, 0.0), (0.1407, -0.1407, 0.0), (0.0762, -0.1839, 0.0), (-0.0, -0.199, 0.0), (-0.0762, -0.1839, 0.0), (-0.1407, -0.1407, 0.0), (-0.1839, -0.0762, 0.0), (-0.199, 0.0, 0.0), (-0.1839, 0.0762, 0.0), (-0.1407, 0.1407, 0.0), (-0.0762, 0.1839, 0.0), (-0.0, 0.1754, 0.0), (0.0671, 0.1621, 0.0), (0.1241, 0.1241, 0.0), (0.1621, 0.0671, 0.0), (0.1754, 0.0, 0.0), (0.1621, -0.0671, 0.0), (0.1241, -0.1241, 0.0), (0.0671, -0.1621, 0.0), (-0.0, -0.1754, 0.0), (-0.0671, -0.1621, 0.0), (-0.1241, -0.1241, 0.0), (-0.1621, -0.0671, 0.0), (-0.1754, 0.0, 0.0), (-0.1621, 0.0671, 0.0), (-0.1241, 0.1241, 0.0), (-0.0671, 0.1621, 0.0)]
        faces = [(0, 1, 3, 2), (2, 3, 7, 6), (6, 7, 5, 4), (4, 5, 1, 0), (2, 6, 4, 0), (7, 3, 1, 5), (8, 10, 11, 9), (10, 14, 15, 11), (14, 12, 13, 15), (12, 8, 9, 13), (10, 8, 12, 14), (15, 13, 9, 11), (16, 18, 19, 17), (18, 22, 23, 19), (22, 20, 21, 23), (20, 16, 17, 21), (18, 16, 20, 22), (23, 21, 17, 19), (24, 25, 27, 26), (26, 27, 31, 30), (30, 31, 29, 28), (28, 29, 25, 24), (26, 30, 28, 24), (31, 27, 25, 29), (33, 32, 47, 48), (48, 47, 46, 51), (51, 46, 45, 54), (54, 45, 44, 43), (34, 33, 48, 49), (49, 48, 51, 52), (52, 51, 54, 55), (55, 54, 43, 42), (35, 34, 49, 50), (50, 49, 52, 53), (53, 52, 55, 56), (56, 55, 42, 41), (36, 35, 50, 37), (37, 50, 53, 38), (38, 53, 56, 39), (39, 56, 41, 40), (58, 73, 72, 57), (73, 76, 71, 72), (76, 79, 70, 71), (79, 68, 69, 70), (59, 74, 73, 58), (74, 77, 76, 73), (77, 80, 79, 76), (80, 67, 68, 79), (60, 75, 74, 59), (75, 78, 77, 74), (78, 81, 80, 77), (81, 66, 67, 80), (61, 62, 75, 60), (62, 63, 78, 75), (63, 64, 81, 78), (64, 65, 66, 81), (35, 36, 61, 60), (43, 44, 69, 68), (36, 37, 62, 61), (44, 45, 70, 69), (37, 38, 63, 62), (45, 46, 71, 70), (38, 39, 64, 63), (46, 47, 72, 71), (39, 40, 65, 64), (32, 33, 58, 57), (47, 32, 57, 72), (40, 41, 66, 65), (33, 34, 59, 58), (41, 42, 67, 66), (34, 35, 60, 59), (42, 43, 68, 67), (86, 85, 101, 102), (94, 93, 109, 110), (87, 86, 102, 103), (95, 94, 110, 111), (88, 87, 103, 104), (96, 95, 111, 112), (89, 88, 104, 105), (97, 96, 112, 113), (90, 89, 105, 106), (83, 82, 98, 99), (82, 97, 113, 98), (91, 90, 106, 107), (84, 83, 99, 100), (92, 91, 107, 108), (85, 84, 100, 101), (93, 92, 108, 109), (118, 134, 133, 117), (126, 142, 141, 125), (119, 135, 134, 118), (127, 143, 142, 126), (120, 136, 135, 119), (128, 144, 143, 127), (121, 137, 136, 120), (129, 145, 144, 128), (122, 138, 137, 121), (115, 131, 130, 114), (114, 130, 145, 129), (123, 139, 138, 122), (116, 132, 131, 115), (124, 140, 139, 123), (117, 133, 132, 116), (125, 141, 140, 124), (83, 115, 114, 82), (109, 141, 142, 110), (97, 129, 128, 96), (84, 116, 115, 83), (110, 142, 143, 111), (82, 114, 129, 97), (85, 117, 116, 84), (111, 143, 144, 112), (98, 130, 131, 99), (86, 118, 117, 85), (112, 144, 145, 113), (99, 131, 132, 100), (87, 119, 118, 86), (113, 145, 130, 98), (100, 132, 133, 101), (88, 120, 119, 87), (101, 133, 134, 102), (89, 121, 120, 88), (102, 134, 135, 103), (90, 122, 121, 89), (103, 135, 136, 104), (91, 123, 122, 90), (104, 136, 137, 105), (92, 124, 123, 91), (105, 137, 138, 106), (93, 125, 124, 92), (106, 138, 139, 107), (94, 126, 125, 93), (107, 139, 140, 108), (95, 127, 126, 94), (108, 140, 141, 109), (96, 128, 127, 95), (150, 149, 165, 166), (158, 157, 173, 174), (151, 150, 166, 167), (159, 158, 174, 175), (152, 151, 167, 168), (160, 159, 175, 176), (153, 152, 168, 169), (161, 160, 176, 177), (154, 153, 169, 170), (147, 146, 162, 163), (146, 161, 177, 162), (155, 154, 170, 171), (148, 147, 163, 164), (156, 155, 171, 172), (149, 148, 164, 165), (157, 156, 172, 173), (182, 198, 197, 181), (190, 206, 205, 189), (183, 199, 198, 182), (191, 207, 206, 190), (184, 200, 199, 183), (192, 208, 207, 191), (185, 201, 200, 184), (193, 209, 208, 192), (186, 202, 201, 185), (179, 195, 194, 178), (178, 194, 209, 193), (187, 203, 202, 186), (180, 196, 195, 179), (188, 204, 203, 187), (181, 197, 196, 180), (189, 205, 204, 188), (147, 179, 178, 146), (173, 205, 206, 174), (161, 193, 192, 160), (148, 180, 179, 147), (174, 206, 207, 175), (146, 178, 193, 161), (149, 181, 180, 148), (175, 207, 208, 176), (162, 194, 195, 163), (150, 182, 181, 149), (176, 208, 209, 177), (163, 195, 196, 164), (151, 183, 182, 150), (177, 209, 194, 162), (164, 196, 197, 165), (152, 184, 183, 151), (165, 197, 198, 166), (153, 185, 184, 152), (166, 198, 199, 167), (154, 186, 185, 153), (167, 199, 200, 168), (155, 187, 186, 154), (168, 200, 201, 169), (156, 188, 187, 155), (169, 201, 202, 170), (157, 189, 188, 156), (170, 202, 203, 171), (158, 190, 189, 157), (171, 203, 204, 172), (159, 191, 190, 158), (172, 204, 205, 173), (160, 192, 191, 159)]
    
    elif chair_type == 'CHAIR_B':
        verts = [(0.1969, -0.3533, 0.4359), (0.1873, -0.3373, 0.5118), (0.1969, 0.0631, 0.4359), (0.1873, 0.0471, 0.5118), (0.1989, 0.0652, 0.479), (0.1989, -0.3553, 0.479), (0.2025, -0.3751, 0.0), (0.23, -0.3751, 0.0), (0.2025, -0.3483, 0.0), (0.23, -0.3483, 0.0), (0.2025, -0.2892, 0.4321), (0.23, -0.2892, 0.4321), (0.2025, -0.271, 0.4359), (0.23, -0.271, 0.4359), (0.2025, 0.131, 0.0), (0.23, 0.131, 0.0), (0.2025, 0.1042, 0.0), (0.23, 0.1042, 0.0), (0.2025, 0.0451, 0.4321), (0.23, 0.0451, 0.4321), (0.2025, 0.0269, 0.4359), (0.23, 0.0269, 0.4359), (0.2025, -0.2958, 0.3319), (0.2025, 0.0529, 0.3319), (0.23, -0.2958, 0.3319), (0.23, 0.0529, 0.3319), (0.2025, -0.2958, 0.3132), (0.2025, 0.0529, 0.3132), (0.23, -0.2958, 0.3132), (0.23, 0.0529, 0.3132), (0.1714, 0.1272, 0.5593), (0.1547, 0.2009, 0.9284), (0.1551, 0.0827, 0.5933), (0.1424, 0.1414, 0.9184), (0.1707, 0.1011, 0.5737), (0.1546, 0.1703, 0.9303), (0.2025, 0.057, 0.4132), (0.23, 0.057, 0.4132), (0.23, 0.0308, 0.4132), (0.2025, 0.0308, 0.4132), (0.2025, -0.3014, 0.4112), (0.23, -0.3014, 0.4112), (0.23, -0.2753, 0.4112), (0.2025, -0.2753, 0.4112), (0.2032, -0.3573, 0.4128), (0.2032, 0.0732, 0.4128), (0.2032, 0.1257, 0.4489), (0.1701, 0.2203, 0.9412), (0.2032, -0.3573, 0.4373), (0.2032, 0.0614, 0.4373), (0.2032, 0.1023, 0.4654), (0.1701, 0.1976, 0.9412), (0.2032, -0.328, 0.4128), (0.2032, -0.3288, 0.4373), (0.1788, 0.2161, 0.9207), (0.1788, 0.1924, 0.9213), (-0.0, 0.2249, 0.9703), (-0.0, 0.2012, 0.9703), (-0.0, 0.2202, 0.9438), (-0.0, 0.1964, 0.9444), (0.1714, -0.3573, 0.4128), (0.1714, -0.3573, 0.4373), (0.1714, -0.328, 0.4128), (0.1508, 0.1924, 0.9249), (0.1714, 0.0732, 0.4128), (0.1714, 0.1257, 0.4489), (0.15, 0.2208, 0.9508), (0.1714, 0.0614, 0.4373), (0.1714, 0.1023, 0.4654), (0.15, 0.1971, 0.9508), (0.1714, -0.3288, 0.4373), (0.1508, 0.2161, 0.9243), (-0.1969, -0.3533, 0.4359), (-0.1873, -0.3373, 0.5118), (-0.1969, 0.0631, 0.4359), (-0.1873, 0.0471, 0.5118), (-0.1989, 0.0652, 0.479), (-0.1989, -0.3553, 0.479), (-0.2025, -0.3751, 0.0), (-0.23, -0.3751, 0.0), (-0.2025, -0.3483, 0.0), (-0.23, -0.3483, 0.0), (-0.2025, -0.2892, 0.4321), (-0.23, -0.2892, 0.4321), (-0.2025, -0.271, 0.4359), (-0.23, -0.271, 0.4359), (-0.2025, 0.131, 0.0), (-0.23, 0.131, 0.0), (-0.2025, 0.1042, 0.0), (-0.23, 0.1042, 0.0), (-0.2025, 0.0451, 0.4321), (-0.23, 0.0451, 0.4321), (-0.2025, 0.0269, 0.4359), (-0.23, 0.0269, 0.4359), (-0.2025, -0.2958, 0.3319), (-0.2025, 0.0529, 0.3319), (-0.23, -0.2958, 0.3319), (-0.23, 0.0529, 0.3319), (-0.2025, -0.2958, 0.3132), (-0.2025, 0.0529, 0.3132), (-0.23, -0.2958, 0.3132), (-0.23, 0.0529, 0.3132), (-0.1714, 0.1272, 0.5593), (-0.1547, 0.2009, 0.9284), (-0.1551, 0.0827, 0.5933), (-0.1424, 0.1414, 0.9184), (-0.1707, 0.1011, 0.5737), (-0.1546, 0.1703, 0.9303), (-0.2025, 0.057, 0.4132), (-0.23, 0.057, 0.4132), (-0.23, 0.0308, 0.4132), (-0.2025, 0.0308, 0.4132), (-0.2025, -0.3014, 0.4112), (-0.23, -0.3014, 0.4112), (-0.23, -0.2753, 0.4112), (-0.2025, -0.2753, 0.4112), (-0.2032, -0.3573, 0.4128), (-0.2032, 0.0732, 0.4128), (-0.2032, 0.1257, 0.4489), (-0.1701, 0.2203, 0.9412), (-0.2032, -0.3573, 0.4373), (-0.2032, 0.0614, 0.4373), (-0.2032, 0.1023, 0.4654), (-0.1701, 0.1976, 0.9412), (-0.2032, -0.328, 0.4128), (-0.2032, -0.3288, 0.4373), (-0.1788, 0.2161, 0.9207), (-0.1788, 0.1924, 0.9213), (-0.1714, -0.3573, 0.4128), (-0.1714, -0.3573, 0.4373), (-0.1714, -0.328, 0.4128), (-0.1508, 0.1924, 0.9249), (-0.1714, 0.0732, 0.4128), (-0.1714, 0.1257, 0.4489), (-0.15, 0.2208, 0.9508), (-0.1714, 0.0614, 0.4373), (-0.1714, 0.1023, 0.4654), (-0.15, 0.1971, 0.9508), (-0.1714, -0.3288, 0.4373), (-0.1508, 0.2161, 0.9243)]
        faces = [(4, 3, 1, 5), (77, 5, 1, 73), (2, 4, 5, 0), (72, 0, 5, 77), (7, 6, 8, 9), (11, 13, 12, 10), (41, 11, 10, 40), (42, 13, 11, 41), (42, 38, 21, 13), (40, 10, 12, 43), (15, 17, 16, 14), (19, 18, 20, 21), (37, 36, 18, 19), (38, 37, 19, 21), (43, 39, 38, 42), (36, 39, 20, 18), (25, 23, 22, 24), (29, 28, 26, 27), (22, 26, 28, 24), (25, 29, 27, 23), (24, 28, 29, 25), (23, 27, 26, 22), (35, 33, 32, 34), (106, 34, 32, 104), (35, 107, 105, 33), (31, 35, 34, 30), (14, 16, 39, 36), (16, 17, 38, 39), (17, 15, 37, 38), (15, 14, 36, 37), (6, 40, 43, 8), (8, 43, 42, 9), (9, 42, 41, 7), (7, 41, 40, 6), (13, 21, 20, 12), (12, 20, 39, 43), (31, 103, 107, 35), (104, 32, 33, 105), (102, 103, 31, 30), (128, 60, 61, 129), (75, 73, 1, 3), (0, 72, 74, 2), (4, 76, 75, 3), (52, 53, 48, 44), (54, 55, 50, 46), (63, 55, 51, 69), (46, 50, 49, 45), (45, 49, 53, 52), (60, 128, 130, 62), (67, 70, 53, 49), (66, 69, 51, 47), (70, 61, 48, 53), (62, 52, 44, 60), (66, 71, 58, 56), (47, 51, 55, 54), (64, 45, 52, 62), (65, 68, 63, 71), (47, 54, 71, 66), (46, 45, 64, 65), (70, 138, 129, 61), (62, 130, 138, 70), (49, 50, 68, 67), (56, 57, 69, 66), (71, 63, 59, 58), (44, 48, 61, 60), (59, 63, 69, 57), (54, 46, 65, 71), (50, 55, 63, 68), (64, 67, 68, 65), (62, 70, 67, 64), (76, 77, 73, 75), (74, 72, 77, 76), (79, 81, 80, 78), (83, 82, 84, 85), (113, 112, 82, 83), (114, 113, 83, 85), (114, 85, 93, 110), (112, 115, 84, 82), (87, 86, 88, 89), (91, 93, 92, 90), (109, 91, 90, 108), (110, 93, 91, 109), (115, 114, 110, 111), (108, 90, 92, 111), (97, 96, 94, 95), (101, 99, 98, 100), (94, 96, 100, 98), (97, 95, 99, 101), (96, 97, 101, 100), (95, 94, 98, 99), (107, 106, 104, 105), (103, 102, 106, 107), (86, 108, 111, 88), (88, 111, 110, 89), (89, 110, 109, 87), (87, 109, 108, 86), (78, 80, 115, 112), (80, 81, 114, 115), (81, 79, 113, 114), (79, 78, 112, 113), (85, 84, 92, 93), (84, 115, 111, 92), (124, 116, 120, 125), (126, 118, 122, 127), (131, 137, 123, 127), (118, 117, 121, 122), (117, 124, 125, 121), (135, 121, 125, 138), (134, 119, 123, 137), (138, 125, 120, 129), (130, 128, 116, 124), (134, 56, 58, 139), (119, 126, 127, 123), (132, 130, 124, 117), (133, 139, 131, 136), (119, 134, 139, 126), (118, 133, 132, 117), (121, 135, 136, 122), (56, 134, 137, 57), (139, 58, 59, 131), (116, 128, 129, 120), (59, 57, 137, 131), (126, 139, 133, 118), (122, 136, 131, 127), (132, 133, 136, 135), (130, 132, 135, 138), (2, 74, 76, 4), (102, 30, 34, 106)]
        
    elif chair_type == 'CHAIR_C':
        verts = [(0.1873, -0.4563, 0.5118), (0.1873, -0.0719, 0.5118), (0.1953, -0.0443, 0.4885), (0.2085, -0.4723, 0.4745), (0.23, -0.4942, 0.0), (0.23, -0.0621, 0.4132), (0.2297, -0.4763, 0.4128), (0.2032, 0.0067, 0.4489), (0.2297, -0.4763, 0.4373), (0.2297, -0.0742, 0.4373), (0.2032, -0.0168, 0.4654), (0.1788, 0.097, 0.9207), (0.1788, 0.0733, 0.9213), (-0.0, 0.1058, 0.9703), (-0.0, 0.0821, 0.9703), (0.15, 0.078, 0.9507), (0.15, 0.1018, 0.9507), (-0.0, -0.0719, 0.5118), (-0.0, 0.0223, 0.9184), (0.0, -0.4563, 0.5118), (0.0, -0.4723, 0.4745), (0.0, -0.4763, 0.4128), (0.0, -0.4763, 0.4373), (0.1184, 0.0223, 0.9184), (0.1433, 0.018, 0.8947), (0.1611, 0.0457, 0.908), (-0.0, 0.0523, 0.9444), (0.1342, 0.0502, 0.9346), (-0.0, 0.097, 0.9207), (-0.0, 0.0067, 0.4489), (-0.0, 0.0119, 0.0), (0.23, -0.0514, 0.0), (0.1938, 0.0119, 0.0), (0.1873, -0.1115, 0.5118), (0.2085, -0.0928, 0.4745), (0.0, -0.1115, 0.5118), (0.0, -0.4942, 0.0), (-0.0, -0.0514, 0.0), (-0.1873, -0.4563, 0.5118), (-0.1873, -0.0719, 0.5118), (-0.1953, -0.0443, 0.4885), (-0.2085, -0.4723, 0.4745), (-0.23, -0.4942, 0.0), (-0.23, -0.0621, 0.4132), (-0.2297, -0.4763, 0.4128), (-0.2032, 0.0067, 0.4489), (-0.2297, -0.4763, 0.4373), (-0.2297, -0.0742, 0.4373), (-0.2032, -0.0168, 0.4654), (-0.1788, 0.097, 0.9207), (-0.1788, 0.0733, 0.9213), (-0.15, 0.078, 0.9507), (-0.15, 0.1018, 0.9507), (-0.1184, 0.0223, 0.9184), (-0.1433, 0.018, 0.8947), (-0.1611, 0.0457, 0.908), (-0.1342, 0.0502, 0.9346), (-0.23, -0.0514, 0.0), (-0.1938, 0.0119, 0.0), (-0.1873, -0.1115, 0.5118), (-0.2085, -0.0928, 0.4745)]
        faces = [(34, 33, 0, 3), (20, 3, 0, 19), (5, 9, 8, 6), (35, 19, 0, 33), (11, 12, 10, 7), (12, 11, 16, 15), (25, 27, 23, 24), (13, 14, 15, 16), (26, 18, 23, 27), (6, 8, 22, 21), (17, 1, 24, 23, 18), (14, 26, 27, 15), (12, 15, 27, 25), (25, 24, 1, 2), (10, 12, 25, 2), (20, 22, 8, 3), (28, 13, 16, 11), (7, 29, 28, 11), (7, 10, 9, 5), (7, 5, 31, 32), (4, 31, 5, 6), (29, 7, 32, 30), (17, 35, 33, 1), (2, 1, 33, 34), (2, 34, 9, 10), (8, 9, 34, 3), (4, 6, 21, 36), (37, 30, 32, 31), (31, 4, 36, 37), (60, 41, 38, 59), (20, 19, 38, 41), (43, 44, 46, 47), (35, 59, 38, 19), (49, 45, 48, 50), (50, 51, 52, 49), (55, 54, 53, 56), (13, 52, 51, 14), (26, 56, 53, 18), (44, 21, 22, 46), (17, 18, 53, 54, 39), (14, 51, 56, 26), (50, 55, 56, 51), (55, 40, 39, 54), (48, 40, 55, 50), (20, 41, 46, 22), (28, 49, 52, 13), (45, 49, 28, 29), (45, 43, 47, 48), (45, 58, 57, 43), (42, 44, 43, 57), (29, 30, 58, 45), (17, 39, 59, 35), (40, 60, 59, 39), (40, 48, 47, 60), (46, 41, 60, 47), (42, 36, 21, 44), (37, 57, 58, 30), (57, 37, 36, 42)]
        
    elif chair_type == 'CHAIR_D':
        verts = [(0.2175, -0.3048, 0.0), (0.2175, -0.3351, 0.0), (0.1922, -0.3351, 0.0), (0.1922, -0.3048, 0.0), (-0.0, 0.0652, 0.8101), (-0.0, 0.0349, 0.8101), (0.2175, 0.0235, 0.785), (-0.0, 0.0537, 0.785), (-0.0, 0.0235, 0.785), (0.1943, 0.0155, 0.7675), (0.175, 0.0235, 0.785), (0.1922, 0.0349, 0.81), (0.175, 0.0537, 0.785), (0.1943, 0.0458, 0.7675), (0.2175, 0.0537, 0.785), (0.1922, 0.0652, 0.81), (0.2158, -0.2485, 0.1343), (0.2158, -0.2686, 0.1343), (-0.0, -0.2686, 0.1343), (-0.0, -0.2485, 0.1343), (0.2158, -0.2405, 0.1507), (0.2158, -0.2607, 0.1507), (-0.0, -0.2607, 0.1507), (-0.0, -0.2405, 0.1507), (-0.0, 0.1132, 0.0241), (-0.0, 0.0839, 0.0226), (0.1937, -0.3932, 0.3463), (0.1937, -0.3932, 0.3788), (0.1937, 0.0175, 0.3463), (0.1937, 0.0175, 0.3788), (0.1953, 0.0839, 0.0226), (0.1953, 0.1132, 0.0241), (0.1774, -0.3768, 0.3961), (0.1774, 0.0011, 0.3961), (0.2152, 0.0839, 0.0226), (0.2152, 0.1132, 0.0241), (0.1919, -0.3922, 0.376), (0.1919, 0.0165, 0.376), (-0.0, -0.0531, 0.6285), (0.2074, 0.092, 0.0081), (-0.0, -0.012, 0.6285), (0.2074, 0.122, 0.0087), (-0.0, 0.0216, 0.7908), (0.2152, -0.1321, 0.4074), (-0.0, 0.0627, 0.7908), (0.2152, -0.119, 0.4347), (0.1953, -0.119, 0.4347), (0.1884, 0.0574, 0.7807), (0.1953, -0.1321, 0.4074), (0.1884, 0.0164, 0.7807), (0.1953, 0.1268, 0.0), (0.1996, -0.0023, 0.649), (0.1953, 0.0965, 0.0), (0.1996, -0.0434, 0.649), (-0.0, 0.0175, 0.3463), (-0.0, 0.0175, 0.3788), (0.0, -0.3932, 0.3463), (0.0, -0.3932, 0.3788), (-0.0, 0.0011, 0.3961), (0.0, -0.3768, 0.3961), (-0.0, 0.0165, 0.376), (0.0, -0.3922, 0.376), (-0.0, 0.0965, 0.0), (-0.0, 0.1268, 0.0), (0.1749, 0.0629, 0.7925), (0.1749, 0.0221, 0.7926), (0.1223, -0.0105, 0.632), (0.1223, -0.0516, 0.632), (-0.0, 0.0516, 0.7668), (0.1999, 0.0115, 0.7705), (0.1999, 0.0526, 0.7705), (-0.0, 0.0105, 0.7668), (0.1749, 0.0531, 0.7699), (0.1749, 0.012, 0.7699), (-0.2175, -0.3048, 0.0), (-0.2175, -0.3351, 0.0), (-0.1922, -0.3351, 0.0), (-0.1922, -0.3048, 0.0), (-0.2175, 0.0235, 0.785), (-0.1943, 0.0155, 0.7675), (-0.175, 0.0235, 0.785), (-0.1922, 0.0349, 0.81), (-0.175, 0.0537, 0.785), (-0.1943, 0.0458, 0.7675), (-0.2175, 0.0537, 0.785), (-0.1922, 0.0652, 0.81), (-0.2158, -0.2485, 0.1343), (-0.2158, -0.2686, 0.1343), (-0.2158, -0.2405, 0.1507), (-0.2158, -0.2607, 0.1507), (-0.1937, -0.3932, 0.3463), (-0.1937, -0.3932, 0.3788), (-0.1937, 0.0175, 0.3463), (-0.1937, 0.0175, 0.3788), (-0.1953, 0.0839, 0.0226), (-0.1953, 0.1132, 0.0241), (-0.1774, -0.3768, 0.3961), (-0.1774, 0.0011, 0.3961), (-0.2152, 0.0839, 0.0226), (-0.2152, 0.1132, 0.0241), (-0.1919, -0.3922, 0.376), (-0.1919, 0.0165, 0.376), (-0.2074, 0.092, 0.0081), (-0.2074, 0.122, 0.0087), (-0.2152, -0.1321, 0.4074), (-0.2152, -0.119, 0.4347), (-0.1953, -0.119, 0.4347), (-0.1884, 0.0574, 0.7807), (-0.1953, -0.1321, 0.4074), (-0.1884, 0.0164, 0.7807), (-0.1953, 0.1268, 0.0), (-0.1996, -0.0023, 0.649), (-0.1953, 0.0965, 0.0), (-0.1996, -0.0434, 0.649), (-0.1749, 0.0629, 0.7925), (-0.1749, 0.0221, 0.7926), (-0.1223, -0.0105, 0.632), (-0.1223, -0.0516, 0.632), (-0.1999, 0.0115, 0.7705), (-0.1999, 0.0526, 0.7705), (-0.1749, 0.0531, 0.7699), (-0.1749, 0.012, 0.7699)]
        faces = [(3, 0, 1, 2), (4, 5, 11, 15), (0, 14, 6, 1), (9, 6, 11, 10), (12, 15, 14, 13), (12, 13, 9, 10), (15, 11, 6, 14), (9, 13, 3, 2), (8, 7, 12, 10), (1, 6, 9, 2), (11, 5, 8, 10), (7, 4, 15, 12), (3, 13, 14, 0), (19, 16, 17, 18), (23, 22, 21, 20), (18, 17, 21, 22), (17, 16, 20, 21), (16, 19, 23, 20), (54, 55, 29, 28), (28, 29, 27, 26), (54, 28, 26, 56), (62, 52, 30, 25), (32, 36, 37, 33), (59, 61, 36, 32), (52, 39, 34, 30), (52, 50, 41, 39), (48, 43, 45, 46), (41, 50, 31, 35), (73, 71, 38, 67), (34, 35, 45, 43), (30, 34, 43, 48), (64, 65, 49, 47), (66, 51, 53, 67), (50, 63, 24, 31), (70, 69, 53, 51), (72, 70, 51, 66), (29, 55, 57, 27), (26, 27, 57, 56), (33, 37, 60, 58), (39, 41, 35, 34), (37, 36, 61, 60), (33, 58, 59, 32), (35, 31, 46, 45), (62, 63, 50, 52), (48, 46, 31, 30), (25, 30, 31, 24), (68, 72, 66, 40), (40, 66, 67, 38), (44, 42, 65, 64), (69, 73, 67, 53), (49, 65, 73, 69), (44, 64, 72, 68), (64, 47, 70, 72), (47, 49, 69, 70), (65, 42, 71, 73), (77, 76, 75, 74), (4, 85, 81, 5), (74, 75, 78, 84), (79, 80, 81, 78), (82, 83, 84, 85), (82, 80, 79, 83), (85, 84, 78, 81), (79, 76, 77, 83), (8, 80, 82, 7), (75, 76, 79, 78), (81, 80, 8, 5), (7, 82, 85, 4), (77, 74, 84, 83), (19, 18, 87, 86), (23, 88, 89, 22), (18, 22, 89, 87), (87, 89, 88, 86), (86, 88, 23, 19), (54, 92, 93, 55), (92, 90, 91, 93), (54, 56, 90, 92), (62, 25, 94, 112), (96, 97, 101, 100), (59, 96, 100, 61), (112, 94, 98, 102), (112, 102, 103, 110), (108, 106, 105, 104), (103, 99, 95, 110), (121, 117, 38, 71), (98, 104, 105, 99), (94, 108, 104, 98), (114, 107, 109, 115), (116, 117, 113, 111), (110, 95, 24, 63), (119, 111, 113, 118), (120, 116, 111, 119), (93, 91, 57, 55), (90, 56, 57, 91), (97, 58, 60, 101), (102, 98, 99, 103), (101, 60, 61, 100), (97, 96, 59, 58), (99, 105, 106, 95), (62, 112, 110, 63), (108, 94, 95, 106), (25, 24, 95, 94), (68, 40, 116, 120), (40, 38, 117, 116), (44, 114, 115, 42), (118, 113, 117, 121), (109, 118, 121, 115), (44, 68, 120, 114), (114, 120, 119, 107), (107, 119, 118, 109), (115, 121, 71, 42)]
        
    else:
        verts = [(0.2252, -0.2016, 0.0), (0.184, -0.1693, 0.383), (0.1991, -0.2016, 0.0), (0.1595, -0.1693, 0.383), (0.2252, -0.1736, 0.0), (0.184, -0.143, 0.383), (0.1991, -0.1736, 0.0), (0.1595, -0.143, 0.383), (-0.2248, -0.2016, 0.0), (-0.1837, -0.1693, 0.383), (-0.1988, -0.2016, 0.0), (-0.1592, -0.1693, 0.383), (-0.2248, -0.1736, 0.0), (-0.1837, -0.143, 0.383), (-0.1988, -0.1736, 0.0), (-0.1592, -0.143, 0.383), (0.2252, 0.1984, 0.0), (0.1978, 0.1984, 0.8598), (0.1812, 0.1866, 0.4104), (0.2252, 0.1675, 0.0), (0.1978, 0.1675, 0.8598), (0.1812, 0.1575, 0.4104), (0.1712, 0.1984, 0.8598), (0.1986, 0.1984, 0.0), (0.1563, 0.1866, 0.4104), (0.1986, 0.1675, 0.0), (0.1712, 0.1675, 0.8598), (0.1563, 0.1575, 0.4104), (0.1817, 0.1898, 0.8012), (0.1817, 0.1705, 0.8012), (0.1817, 0.1898, 0.7863), (0.1817, 0.1705, 0.7863), (0.1742, 0.1884, 0.6724), (0.1742, 0.1692, 0.6724), (0.1742, 0.1884, 0.6575), (0.1742, 0.1692, 0.6575), (0.1733, 0.1856, 0.5997), (0.1733, 0.1664, 0.5997), (0.1733, 0.1856, 0.5848), (0.1733, 0.1664, 0.5848), (0.1733, 0.1833, 0.5251), (0.1733, 0.1641, 0.5251), (0.191, -0.1705, 0.2797), (0.1732, -0.1705, 0.2797), (0.1733, 0.1833, 0.5102), (0.1733, 0.1641, 0.5102), (0.191, -0.1705, 0.2946), (0.1732, -0.1705, 0.2946), (0.1742, 0.1776, 0.401), (0.1742, 0.1583, 0.401), (-0.1729, -0.1705, 0.2797), (-0.1907, -0.1705, 0.2797), (0.1742, 0.1776, 0.3861), (0.1742, 0.1583, 0.3861), (-0.1729, -0.1705, 0.2946), (-0.1907, -0.1705, 0.2946), (0.177, 0.184, 0.3244), (0.177, 0.1647, 0.3244), (0.191, 0.1833, 0.2797), (0.1732, 0.1833, 0.2797), (0.177, 0.184, 0.3095), (0.177, 0.1647, 0.3095), (0.191, 0.1833, 0.2946), (0.1732, 0.1833, 0.2946), (0.177, -0.1519, 0.3244), (0.177, -0.1712, 0.3244), (-0.1729, 0.1833, 0.2797), (-0.1907, 0.1833, 0.2797), (0.177, -0.1519, 0.3095), (0.177, -0.1712, 0.3095), (-0.1729, 0.1833, 0.2946), (-0.1907, 0.1833, 0.2946), (-0.2248, 0.1984, 0.0), (-0.1975, 0.1984, 0.8598), (-0.1809, 0.1866, 0.4104), (-0.2248, 0.1675, 0.0), (-0.1975, 0.1675, 0.8598), (-0.1809, 0.1575, 0.4104), (-0.1709, 0.1984, 0.8598), (-0.1983, 0.1984, 0.0), (-0.156, 0.1866, 0.4104), (-0.1983, 0.1675, 0.0), (-0.1709, 0.1675, 0.8598), (-0.156, 0.1575, 0.4104), (-0.1813, 0.1898, 0.8012), (-0.1813, 0.1705, 0.8012), (-0.1813, 0.1898, 0.7863), (-0.1813, 0.1705, 0.7863), (-0.1739, 0.1884, 0.6724), (-0.1739, 0.1692, 0.6724), (-0.1739, 0.1884, 0.6575), (-0.1739, 0.1692, 0.6575), (-0.1747, 0.1856, 0.5997), (-0.1747, 0.1664, 0.5997), (-0.1747, 0.1856, 0.5848), (-0.1747, 0.1664, 0.5848), (-0.1747, 0.1833, 0.5251), (-0.1747, 0.1641, 0.5251), (-0.1747, 0.1833, 0.5102), (-0.1747, 0.1641, 0.5102), (-0.1739, 0.1776, 0.401), (-0.1739, 0.1583, 0.401), (-0.1739, 0.1776, 0.3861), (-0.1739, 0.1583, 0.3861), (-0.1767, 0.184, 0.3244), (-0.1767, 0.1647, 0.3244), (-0.1767, 0.184, 0.3095), (-0.1767, 0.1647, 0.3095), (-0.1767, -0.1519, 0.3244), (-0.1767, -0.1712, 0.3244), (-0.1767, -0.1519, 0.3095), (-0.1767, -0.1712, 0.3095), (-0.1891, 0.1358, 0.3768), (-0.1642, 0.1574, 0.3768), (-0.1891, 0.1358, 0.4074), (-0.1642, 0.1574, 0.4074), (0.1645, 0.1574, 0.3768), (0.1895, 0.1358, 0.3768), (0.1895, 0.1358, 0.4074), (0.1645, 0.1574, 0.4074), (-0.1743, -0.1937, 0.3768), (-0.198, -0.1721, 0.3768), (-0.198, -0.1721, 0.4074), (-0.1743, -0.1937, 0.4074), (0.1983, -0.1721, 0.3768), (0.1746, -0.1937, 0.3768), (0.1746, -0.1937, 0.4074), (0.1983, -0.1721, 0.4074), (-0.0052, 0.185, 0.665), (-0.0052, 0.1728, 0.665), (0.0056, 0.1728, 0.665), (0.0056, 0.185, 0.665), (0.0056, 0.1859, 0.7922), (0.0056, 0.1738, 0.7922), (-0.0052, 0.1738, 0.7922), (-0.0052, 0.1859, 0.7922), (0.0494, 0.185, 0.665), (0.0494, 0.1728, 0.665), (0.0603, 0.1728, 0.665), (0.0603, 0.185, 0.665), (0.0646, 0.1859, 0.7922), (0.0646, 0.1738, 0.7922), (0.0538, 0.1738, 0.7922), (0.0538, 0.1859, 0.7922), (0.1095, 0.185, 0.665), (0.1095, 0.1728, 0.665), (0.1204, 0.1728, 0.665), (0.1204, 0.185, 0.665), (0.1252, 0.1859, 0.7922), (0.1252, 0.1738, 0.7922), (0.1143, 0.1738, 0.7922), (0.1143, 0.1859, 0.7922), (-0.0491, 0.185, 0.665), (-0.0491, 0.1728, 0.665), (-0.06, 0.1728, 0.665), (-0.06, 0.185, 0.665), (-0.0643, 0.1859, 0.7922), (-0.0643, 0.1738, 0.7922), (-0.0535, 0.1738, 0.7922), (-0.0535, 0.1859, 0.7922), (-0.1092, 0.185, 0.665), (-0.1092, 0.1728, 0.665), (-0.1201, 0.1728, 0.665), (-0.1201, 0.185, 0.665), (-0.1249, 0.1859, 0.7922), (-0.1249, 0.1738, 0.7922), (-0.114, 0.1738, 0.7922), (-0.114, 0.1859, 0.7922)]
        faces = [(4, 5, 1, 0), (0, 1, 3, 2), (4, 0, 2, 6), (2, 3, 7, 6), (1, 5, 7, 3), (12, 8, 9, 13), (8, 10, 11, 9), (12, 14, 10, 8), (10, 14, 15, 11), (9, 11, 15, 13), (24, 22, 17, 18), (23, 24, 18, 16), (16, 18, 21, 19), (18, 17, 20, 21), (25, 19, 21, 27), (20, 26, 27, 21), (27, 26, 22, 24), (16, 19, 25, 23), (20, 17, 22, 26), (25, 27, 24, 23), (86, 30, 31, 87), (85, 87, 31, 29), (30, 86, 84, 28), (28, 29, 31, 30), (88, 89, 33, 32), (90, 34, 35, 91), (89, 91, 35, 33), (34, 90, 88, 32), (32, 33, 35, 34), (92, 93, 37, 36), (94, 38, 39, 95), (93, 95, 39, 37), (38, 94, 92, 36), (36, 37, 39, 38), (96, 97, 41, 40), (98, 44, 45, 99), (97, 99, 45, 41), (44, 98, 96, 40), (40, 41, 45, 44), (100, 101, 49, 48), (102, 52, 53, 103), (101, 103, 53, 49), (52, 102, 100, 48), (48, 49, 53, 52), (104, 105, 57, 56), (106, 60, 61, 107), (105, 107, 61, 57), (60, 106, 104, 56), (56, 57, 61, 60), (108, 109, 65, 64), (110, 68, 69, 111), (109, 111, 69, 65), (68, 110, 108, 64), (64, 65, 69, 68), (55, 54, 70, 71), (80, 74, 73, 78), (79, 72, 74, 80), (72, 75, 77, 74), (74, 77, 76, 73), (81, 83, 77, 75), (76, 77, 83, 82), (83, 80, 78, 82), (72, 79, 81, 75), (76, 82, 78, 73), (81, 79, 80, 83), (84, 86, 87, 85), (88, 90, 91, 89), (92, 94, 95, 93), (96, 98, 99, 97), (47, 43, 42, 46), (55, 51, 50, 54), (100, 102, 103, 101), (63, 62, 58, 59), (59, 43, 47, 63), (46, 42, 58, 62), (43, 59, 58, 42), (104, 106, 107, 105), (47, 46, 62, 63), (71, 70, 66, 67), (67, 51, 55, 71), (54, 50, 66, 70), (108, 110, 111, 109), (51, 67, 66, 50), (84, 85, 29, 28), (112, 114, 115, 113), (118, 117, 116, 119), (126, 125, 124, 127), (122, 123, 126, 127), (122, 121, 120, 123), (113, 115, 119, 116), (121, 122, 114, 112), (117, 118, 127, 124), (125, 126, 123, 120), (116, 117, 112, 113), (117, 124, 121, 112), (124, 125, 120, 121), (132, 131, 128, 135), (133, 130, 131, 132), (134, 129, 130, 133), (135, 128, 129, 134), (128, 131, 130, 129), (135, 134, 133, 132), (140, 139, 136, 143), (141, 138, 139, 140), (142, 137, 138, 141), (143, 136, 137, 142), (136, 139, 138, 137), (143, 142, 141, 140), (148, 147, 144, 151), (149, 146, 147, 148), (150, 145, 146, 149), (151, 144, 145, 150), (144, 147, 146, 145), (151, 150, 149, 148), (156, 159, 152, 155), (157, 156, 155, 154), (158, 157, 154, 153), (159, 158, 153, 152), (152, 153, 154, 155), (159, 156, 157, 158), (164, 167, 160, 163), (165, 164, 163, 162), (166, 165, 162, 161), (167, 166, 161, 160), (160, 161, 162, 163), (167, 164, 165, 166), (114, 122, 127, 118), (115, 114, 118, 119)]
    return verts, faces

def update_chair_count(self, context):
    props = context.scene.generative_booth_props
    if getattr(props, "programmatic_update", False):
        return

    col = get_or_create_collection("Booth_Chairs")
    current_objects = list(col.objects)
    
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_Chair_"):
        target_type = active_obj.individual_chair_type
        target_color = active_obj.individual_chair_color
    else:
        target_type = props.chair_type
        target_color = props.chair_color

    matching_objs = [o for o in current_objects if getattr(o, "individual_chair_type", "") == target_type]
    count_needed = props.chair_count

    while len(matching_objs) > count_needed:
        obj_to_remove = matching_objs[-1]
        
        if context.active_object == obj_to_remove:
            remaining_companions = [o for o in matching_objs if o != obj_to_remove]
            if remaining_companions:
                context.view_layer.objects.active = remaining_companions[-1]
                remaining_companions[-1].select_set(True)
            else:
                context.view_layer.objects.active = None
                
        matching_objs.remove(obj_to_remove)
        bpy.data.objects.remove(obj_to_remove, do_unlink=True)

    while len(matching_objs) < count_needed:
        new_index = len(col.objects)
        
        new_obj = add_chair_booth(
            target_type, 
            props.floor_width, 
            props.floor_length, 
            props.floor_height,
            props.chair_rotation_random,
            new_index
        )
        
        new_obj.individual_chair_type = target_type
        new_obj.individual_chair_color = target_color
        matching_objs.append(new_obj)

def update_chair_style(self, context):
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_Chairs")
    
    verts, faces = create_chair_mesh(props.chair_type)
    mat = add_material("Booth_Chair_Mat", props.chair_color)
    
    for obj in col.objects:
        obj.data.clear_geometry()
        obj.data.from_pydata(verts, [], faces)
        obj.data.update()
        obj.location.z = props.floor_height
        if not obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

def add_chair_booth(chair_type, floor_width, floor_length, floor_height, rot_random, index):
    verts, faces = create_chair_mesh(chair_type)
    mesh_data = bpy.data.meshes.new(f"Chair_Mesh_{index}")
    mesh_data.from_pydata(verts, [], faces)
    mesh_data.update()
    
    obj = bpy.data.objects.new(f"Booth_Chair_{index}", mesh_data)
    col = get_or_create_collection("Booth_Chairs")
    col.objects.link(obj)

    props = bpy.context.scene.generative_booth_props
    obj.individual_chair_type = chair_type
    obj.individual_chair_color = props.chair_color
    
    bpy.context.view_layer.update()

    margin = 0.5
    x_max = (floor_width / 2.0) - margin
    y_max = (floor_length / 2.0) - margin
    
    for _ in range(100):
        new_x = random.uniform(-x_max, x_max)
        new_y = random.uniform(-y_max, y_max)
        if not is_overlapping(new_x, new_y, obj, bpy.context, safety_margin=0.7):
            obj.location.x = new_x
            obj.location.y = new_y
            break
    else:
        obj.location.x = random.uniform(-x_max, x_max)
        obj.location.y = random.uniform(-y_max, y_max)
        
    obj.location.z = floor_height
    
    rotation_intensity = rot_random * 5.0
    random.seed(index + 700) 
    rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
    obj.rotation_euler.z = math.radians(rand_angle)
    
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj

def update_chair_rotation(self, context):
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_Chairs")
    
    rotation_intensity = props.chair_rotation_random * 5.0
    
    for i, obj in enumerate(col.objects):
        random.seed(i + 700)
        rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
        obj.rotation_euler.z = math.radians(rand_angle)
        
def update_individual_chair_style(self, context):
    """Triggers whenever a clicked chair changes its individual type or color tint."""
    if not self or self.type != 'MESH':
        return
        
    props = context.scene.generative_booth_props
        
    verts, faces = create_chair_mesh(self.individual_chair_type)
    self.data.clear_geometry()
    self.data.from_pydata(verts, [], faces)
    self.data.update()
    
    current_type = self.individual_chair_type
    matching_count = sum(
        1 for o in context.scene.objects 
        if o.name.startswith("Booth_Chair_") 
        and getattr(o, "individual_chair_type", "") == current_type
    )
    
    props.programmatic_update = True
    props.chair_count = matching_count
    props.programmatic_update = False
    
    mat_name = f"Mat_{self.name}_Unique"
    color_tuple = (
        self.individual_chair_color[0],
        self.individual_chair_color[1],
        self.individual_chair_color[2],
        self.individual_chair_color[3]
    )
    
    mat = add_material(mat_name, color_tuple)
    if not self.data.materials:
        self.data.materials.append(mat)
    else:
        self.data.materials[0] = mat
        
def sync_ui_on_chair_selection_change(scene):
    """Safely updates the count slider when a user selects a different chair type."""
    context = bpy.context
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_Chair_"):
        props = context.scene.generative_booth_props
        current_type = getattr(active_obj, "individual_chair_type", "")
        
        matching_count = sum(
            1 for o in context.scene.objects 
            if o.name.startswith("Booth_Chair_") 
            and getattr(o, "individual_chair_type", "") == current_type
        )
        
        if props.chair_count != matching_count:
            props.programmatic_update = True
            props.chair_count = matching_count
            props.programmatic_update = False

class OBJECT_OT_modify_chair_booth_position(bpy.types.Operator):
    bl_idname = "object.modify_chair_booth_position"
    bl_label = "Generate Random Chair Positions"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        props = context.scene.generative_booth_props
        col = get_or_create_collection("Booth_Chairs")

        margin = 0.5
        x_max = (props.floor_width / 2.0) - margin
        y_max = (props.floor_length / 2.0) - margin
        
        for obj in col.objects:
            success = False
            for _ in range(150):
                new_x = random.uniform(-x_max, x_max)
                new_y = random.uniform(-y_max, y_max)
                if not is_overlapping(new_x, new_y, obj, context, safety_margin=0.15):
                    obj.location.x = new_x
                    obj.location.y = new_y
                    success = True
                    break
            if not success:
                obj.location.x = random.uniform(-x_max, x_max)
                obj.location.y = random.uniform(-y_max, y_max)
                
            obj.location.z = props.floor_height
            
        return {'FINISHED'}

#_____FLOOR ELEMENT_____
def create_floorelement_mesh(floorelement_type):
    if floorelement_type == 'floorelement_A':
        verts = [(0.3378, -0.19, 0.0002), (0.3378, -0.19, 0.1004), (0.3378, 0.19, 0.0002), (0.3378, 0.19, 0.1004), (0.375, -0.19, 0.0002), (0.375, -0.19, 0.1004), (0.375, 0.19, 0.0002), (0.375, 0.19, 0.1004), (0.375, -0.19, 0.066), (0.375, 0.19, 0.066), (0.3378, 0.19, 0.066), (0.3378, -0.19, 0.066), (0.3378, -0.1552, 0.0002), (0.3378, 0.1552, 0.0002), (0.3378, 0.1552, 0.1004), (0.3378, -0.1552, 0.1004), (0.375, 0.1552, 0.0002), (0.375, -0.1552, 0.0002), (0.375, -0.1552, 0.1004), (0.375, 0.1552, 0.1004), (0.375, -0.1552, 0.066), (0.375, 0.1552, 0.066), (0.3378, 0.1552, 0.066), (0.3378, -0.1552, 0.066), (0.3378, -0.0182, 1.1999), (0.3378, 0.0182, 1.1999), (0.375, 0.0182, 1.1999), (0.375, -0.0182, 1.1999), (0.3378, 0.0182, 0.1004), (0.3378, -0.0182, 0.1004), (0.375, -0.0182, 0.1004), (0.375, 0.0182, 0.1004), (0.3378, -0.0182, 0.066), (0.3378, 0.0182, 0.066), (0.375, 0.0182, 0.066), (0.375, -0.0182, 0.066), (0.375, 0.0182, 1.1676), (0.375, -0.0182, 1.1676), (0.3378, 0.0182, 1.1676), (0.3378, -0.0182, 1.1676), (0.3448, -0.0457, 0.0933), (0.3448, -0.0667, 0.0933), (0.3448, -0.0457, 0.0731), (0.3448, -0.0667, 0.0731), (0.3448, 0.0658, 0.0933), (0.3448, 0.0447, 0.0933), (0.3448, 0.0658, 0.0731), (0.3448, 0.0447, 0.0731), (-0.3378, -0.19, 0.0002), (-0.3378, -0.19, 0.1004), (-0.3378, 0.19, 0.0002), (-0.3378, 0.19, 0.1004), (-0.375, -0.19, 0.0002), (-0.375, -0.19, 0.1004), (-0.375, 0.19, 0.0002), (-0.375, 0.19, 0.1004), (-0.375, -0.19, 0.066), (-0.375, 0.19, 0.066), (-0.3378, 0.19, 0.066), (-0.3378, -0.19, 0.066), (-0.3378, -0.1552, 0.0002), (-0.3378, 0.1552, 0.0002), (-0.3378, 0.1552, 0.1004), (-0.3378, -0.1552, 0.1004), (-0.375, 0.1552, 0.0002), (-0.375, -0.1552, 0.0002), (-0.375, -0.1552, 0.1004), (-0.375, 0.1552, 0.1004), (-0.375, -0.1552, 0.066), (-0.375, 0.1552, 0.066), (-0.3378, 0.1552, 0.066), (-0.3378, -0.1552, 0.066), (-0.3378, -0.0182, 1.1999), (-0.3378, 0.0182, 1.1999), (-0.375, 0.0182, 1.1999), (-0.375, -0.0182, 1.1999), (-0.3378, 0.0182, 0.1004), (-0.3378, -0.0182, 0.1004), (-0.375, -0.0182, 0.1004), (-0.375, 0.0182, 0.1004), (-0.3378, -0.0182, 0.066), (-0.3378, 0.0182, 0.066), (-0.375, 0.0182, 0.066), (-0.375, -0.0182, 0.066), (-0.375, 0.0182, 1.1676), (-0.375, -0.0182, 1.1676), (-0.3378, 0.0182, 1.1676), (-0.3378, -0.0182, 1.1676), (-0.3448, -0.0457, 0.0933), (-0.3448, -0.0667, 0.0933), (-0.3448, -0.0457, 0.0731), (-0.3448, -0.0667, 0.0731), (-0.3448, 0.0658, 0.0933), (-0.3448, 0.0447, 0.0933), (-0.3448, 0.0658, 0.0731), (-0.3448, 0.0447, 0.0731)]
        faces = [(10, 3, 7, 9), (6, 9, 21, 16), (8, 5, 1, 11), (4, 8, 11, 0), (0, 11, 23, 12), (13, 22, 10, 2), (17, 20, 8, 4), (2, 10, 9, 6), (20, 17, 12, 23), (11, 1, 15, 23), (2, 6, 16, 13), (12, 17, 4, 0), (22, 14, 3, 10), (7, 3, 14, 19), (18, 15, 1, 5), (9, 7, 19, 21), (20, 18, 5, 8), (87, 39, 24, 72), (16, 21, 22, 13), (26, 25, 24, 27), (37, 36, 26, 27), (36, 38, 25, 26), (35, 32, 33, 34), (39, 37, 27, 24), (34, 31, 30, 35), (32, 29, 28, 33), (15, 18, 30, 29), (14, 22, 33, 28), (28, 31, 19, 14), (29, 32, 23, 15), (18, 20, 35, 30), (31, 34, 21, 19), (35, 20, 23, 32), (21, 34, 33, 22), (29, 30, 37, 39), (31, 28, 38, 36), (30, 31, 36, 37), (28, 29, 39, 38), (92, 93, 45, 44), (86, 38, 39, 87), (72, 24, 25, 73), (40, 41, 43, 42), (44, 45, 47, 46), (94, 92, 44, 46), (95, 94, 46, 47), (90, 88, 40, 42), (91, 90, 42, 43), (88, 89, 41, 40), (93, 95, 47, 45), (89, 91, 43, 41), (58, 57, 55, 51), (54, 64, 69, 57), (56, 59, 49, 53), (52, 48, 59, 56), (48, 60, 71, 59), (61, 50, 58, 70), (65, 52, 56, 68), (50, 54, 57, 58), (68, 71, 60, 65), (59, 71, 63, 49), (50, 61, 64, 54), (60, 48, 52, 65), (70, 58, 51, 62), (55, 67, 62, 51), (66, 53, 49, 63), (57, 69, 67, 55), (68, 56, 53, 66), (64, 61, 70, 69), (74, 75, 72, 73), (85, 75, 74, 84), (84, 74, 73, 86), (83, 82, 81, 80), (87, 72, 75, 85), (82, 83, 78, 79), (80, 81, 76, 77), (63, 77, 78, 66), (62, 76, 81, 70), (76, 62, 67, 79), (77, 63, 71, 80), (66, 78, 83, 68), (79, 67, 69, 82), (83, 80, 71, 68), (69, 70, 81, 82), (77, 87, 85, 78), (79, 84, 86, 76), (78, 85, 84, 79), (76, 86, 87, 77), (88, 90, 91, 89), (92, 94, 95, 93), (73, 25, 38, 86)]
    
    elif floorelement_type == 'floorelement_B':
        verts = [(-0.25, -0.1062, 0.0005), (-0.25, 0.1411, 1.1747), (0.25, -0.1062, 0.0005), (0.25, 0.1411, 1.1747), (-0.2121, -0.1454, 0.0568), (-0.2121, 0.0824, 1.139), (0.2121, -0.1454, 0.0568), (0.2121, 0.0824, 1.139), (0.25, 0.0921, 1.185), (0.25, -0.1551, 0.0108), (-0.25, -0.1551, 0.0108), (-0.25, 0.0921, 1.185), (0.2121, 0.1116, 1.1328), (0.2121, -0.1163, 0.0507), (-0.2121, -0.1163, 0.0507), (-0.2121, 0.1116, 1.1328), (-0.0971, 0.2033, 0.0054), (-0.0971, 0.0637, 0.8282), (0.0971, 0.2033, 0.0054), (0.0971, 0.0637, 0.8282), (-0.0971, 0.1714, -0.0), (-0.0971, 0.0457, 0.7413), (0.0971, 0.1714, -0.0), (0.0971, 0.0457, 0.7413)]
        faces = [(0, 1, 3, 2), (2, 3, 8, 9), (7, 5, 15, 12), (10, 11, 1, 0), (2, 9, 10, 0), (8, 3, 1, 11), (7, 6, 9, 8), (6, 4, 10, 9), (5, 7, 8, 11), (4, 5, 11, 10), (13, 12, 15, 14), (6, 7, 12, 13), (5, 4, 14, 15), (4, 6, 13, 14), (16, 17, 19, 18), (18, 19, 23, 22), (22, 23, 21, 20), (20, 21, 17, 16), (18, 22, 20, 16), (23, 19, 17, 21)]
    
    else:
        verts = [(0.0878, 0.004, 1.2), (0.0878, -0.1261, 1.2), (0.287, 0.0375, 0.0795), (0.287, -0.0449, 0.0795), (0.287, 0.0375, 0.051), (0.287, -0.0449, 0.051), (0.0563, -0.0157, 0.0643), (0.0994, -0.0157, 0.0643), (0.0563, 0.0071, 0.0643), (0.0994, 0.0071, 0.0643), (0.0563, -0.0157, 0.9621), (0.0994, -0.0157, 0.9621), (0.0563, 0.0071, 0.9621), (0.0994, 0.0071, 0.9621), (0.0878, 0.004, 1.1919), (0.0878, -0.1261, 1.1919), (0.014, -0.0127, 0.7592), (0.014, 0.004, 0.7592), (0.014, -0.0127, 1.1959), (0.014, 0.004, 1.1959), (0.059, -0.0119, 0.3919), (0.059, 0.0032, 0.3919), (0.059, -0.0119, 0.4059), (0.059, 0.0032, 0.4059), (0.1294, -0.1578, 0.4682), (0.1294, -0.0153, 0.4682), (0.1294, -0.1578, 0.4892), (0.1294, -0.0153, 0.4892), (0.1441, -0.0157, 0.7866), (0.1664, -0.0157, 0.7866), (0.1441, 0.0071, 0.7866), (0.1664, 0.0071, 0.7866), (0.1441, -0.0157, 1.0271), (0.1664, -0.0157, 1.0271), (0.1441, 0.0071, 1.0271), (0.1664, 0.0071, 1.0271), (0.45, -0.0646, 0.6562), (0.45, -0.0346, 0.6562), (0.45, -0.0646, 1.1562), (0.45, -0.0346, 1.1562), (0.2501, -0.0364, 0.8262), (0.2501, -0.0145, 0.8262), (0.2501, -0.0364, 0.9805), (0.2501, -0.0145, 0.9805), (-0.0878, 0.004, 1.2), (-0.0878, -0.1261, 1.2), (-0.287, 0.0375, 0.0795), (-0.287, -0.0449, 0.0795), (-0.287, 0.0375, 0.051), (-0.287, -0.0449, 0.051), (-0.0563, -0.0157, 0.0643), (-0.0994, -0.0157, 0.0643), (-0.0563, 0.0071, 0.0643), (-0.0994, 0.0071, 0.0643), (-0.0563, -0.0157, 0.9621), (-0.0994, -0.0157, 0.9621), (-0.0563, 0.0071, 0.9621), (-0.0994, 0.0071, 0.9621), (-0.0878, 0.004, 1.1919), (-0.0878, -0.1261, 1.1919), (-0.014, -0.0127, 0.7592), (-0.014, 0.004, 0.7592), (-0.014, -0.0127, 1.1959), (-0.014, 0.004, 1.1959), (-0.059, -0.0119, 0.3919), (-0.059, 0.0032, 0.3919), (-0.059, -0.0119, 0.4059), (-0.059, 0.0032, 0.4059), (-0.1294, -0.1578, 0.4682), (-0.1294, -0.0153, 0.4682), (-0.1294, -0.1578, 0.4892), (-0.1294, -0.0153, 0.4892), (-0.1441, -0.0157, 0.7866), (-0.1664, -0.0157, 0.7866), (-0.1441, 0.0071, 0.7866), (-0.1664, 0.0071, 0.7866), (-0.1441, -0.0157, 1.0271), (-0.1664, -0.0157, 1.0271), (-0.1441, 0.0071, 1.0271), (-0.1664, 0.0071, 1.0271), (-0.45, -0.0646, 0.6562), (-0.45, -0.0346, 0.6562), (-0.45, -0.0646, 1.1562), (-0.45, -0.0346, 1.1562), (-0.2501, -0.0364, 0.8262), (-0.2501, -0.0145, 0.8262), (-0.2501, -0.0364, 0.9805), (-0.2501, -0.0145, 0.9805), (0.282, 0.1991, 0.0), (0.282, 0.1991, 0.0852), (0.32, 0.1991, 0.0), (0.32, 0.1991, 0.0852), (0.282, -0.4009, 0.0), (0.282, -0.4009, 0.0852), (0.32, -0.4009, 0.0), (0.32, -0.4009, 0.0852), (0.282, -0.4009, 0.0456), (0.32, -0.4009, 0.0456), (0.32, 0.1991, 0.0456), (0.282, 0.1991, 0.0456), (0.32, 0.1624, 0.0), (0.32, -0.3643, 0.0), (0.32, -0.3643, 0.0852), (0.32, 0.1624, 0.0852), (0.282, -0.3643, 0.0), (0.282, 0.1624, 0.0), (0.282, 0.1624, 0.0852), (0.282, -0.3643, 0.0852), (0.282, 0.1624, 0.0456), (0.282, -0.3643, 0.0456), (0.32, -0.3643, 0.0456), (0.32, 0.1624, 0.0456), (-0.282, 0.1991, 0.0), (-0.282, 0.1991, 0.0852), (-0.32, 0.1991, 0.0), (-0.32, 0.1991, 0.0852), (-0.282, -0.4009, 0.0), (-0.282, -0.4009, 0.0852), (-0.32, -0.4009, 0.0), (-0.32, -0.4009, 0.0852), (-0.282, -0.4009, 0.0456), (-0.32, -0.4009, 0.0456), (-0.32, 0.1991, 0.0456), (-0.282, 0.1991, 0.0456), (-0.32, 0.1624, 0.0), (-0.32, -0.3643, 0.0), (-0.32, -0.3643, 0.0852), (-0.32, 0.1624, 0.0852), (-0.282, -0.3643, 0.0), (-0.282, 0.1624, 0.0), (-0.282, 0.1624, 0.0852), (-0.282, -0.3643, 0.0852), (-0.282, 0.1624, 0.0456), (-0.282, -0.3643, 0.0456), (-0.32, -0.3643, 0.0456), (-0.32, 0.1624, 0.0456)]
        faces = [(2, 3, 5, 4), (48, 46, 2, 4), (49, 48, 4, 5), (47, 49, 5, 3), (36, 80, 81, 37), (6, 8, 9, 7), (10, 11, 13, 12), (7, 9, 13, 11), (6, 7, 11, 10), (9, 8, 12, 13), (12, 8, 6, 10), (59, 58, 14, 15), (1, 45, 59, 15), (44, 0, 14, 58), (1, 15, 14, 0), (19, 63, 62, 18), (18, 62, 60, 16), (16, 17, 19, 18), (61, 63, 19, 17), (40, 84, 85, 41), (23, 67, 66, 22), (22, 66, 64, 20), (20, 21, 23, 22), (65, 67, 23, 21), (46, 47, 3, 2), (27, 71, 70, 26), (26, 70, 68, 24), (24, 25, 27, 26), (69, 71, 27, 25), (20, 64, 65, 21), (28, 30, 31, 29), (32, 33, 35, 34), (29, 31, 35, 33), (28, 29, 33, 32), (31, 30, 34, 35), (34, 30, 28, 32), (39, 83, 82, 38), (38, 82, 80, 36), (36, 37, 39, 38), (81, 83, 39, 37), (16, 60, 61, 17), (43, 87, 86, 42), (42, 86, 84, 40), (40, 41, 43, 42), (85, 87, 43, 41), (46, 48, 49, 47), (50, 51, 53, 52), (54, 56, 57, 55), (51, 55, 57, 53), (50, 54, 55, 51), (53, 57, 56, 52), (56, 54, 50, 52), (45, 44, 58, 59), (60, 62, 63, 61), (64, 66, 67, 65), (68, 70, 71, 69), (72, 73, 75, 74), (76, 78, 79, 77), (73, 77, 79, 75), (72, 76, 77, 73), (75, 79, 78, 74), (78, 76, 72, 74), (80, 82, 83, 81), (84, 86, 87, 85), (24, 68, 69, 25), (45, 1, 0, 44), (99, 89, 91, 98), (106, 108, 109, 107), (97, 95, 93, 96), (101, 110, 97, 94), (105, 108, 99, 88), (94, 97, 96, 92), (102, 110, 111, 103), (90, 98, 111, 100), (92, 96, 109, 104), (88, 99, 98, 90), (103, 106, 107, 102), (110, 101, 104, 109), (98, 91, 103, 111), (101, 94, 92, 104), (90, 100, 105, 88), (110, 102, 95, 97), (95, 102, 107, 93), (103, 91, 89, 106), (96, 93, 107, 109), (108, 106, 89, 99), (111, 110, 109, 108), (100, 111, 108, 105), (123, 122, 115, 113), (130, 131, 133, 132), (121, 120, 117, 119), (125, 118, 121, 134), (129, 112, 123, 132), (118, 116, 120, 121), (126, 127, 135, 134), (114, 124, 135, 122), (116, 128, 133, 120), (112, 114, 122, 123), (127, 126, 131, 130), (134, 133, 128, 125), (122, 135, 127, 115), (125, 128, 116, 118), (114, 112, 129, 124), (134, 121, 119, 126), (119, 117, 131, 126), (127, 130, 113, 115), (120, 133, 131, 117), (132, 123, 113, 130), (135, 132, 133, 134), (124, 129, 132, 135)]
        
    return verts, faces

def update_floorelement_count(self, context):
    props = context.scene.generative_booth_props
    if getattr(props, "programmatic_update", False):
        return

    col = get_or_create_collection("Booth_floorelement")
    current_objects = list(col.objects)
    
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_floorelement_"):
        target_type = active_obj.individual_floorelement_type
        target_color = active_obj.individual_floorelement_color
    else:
        target_type = props.floorelement_type
        target_color = props.floorelement_color

    matching_objs = [o for o in current_objects if getattr(o, "individual_floorelement_type", "") == target_type]
    count_needed = props.floorelement_count

    while len(matching_objs) > count_needed:
        obj_to_remove = matching_objs[-1]
        
        if context.active_object == obj_to_remove:
            remaining_companions = [o for o in matching_objs if o != obj_to_remove]
            if remaining_companions:
                context.view_layer.objects.active = remaining_companions[-1]
                remaining_companions[-1].select_set(True)
            else:
                context.view_layer.objects.active = None
                
        matching_objs.remove(obj_to_remove)
        bpy.data.objects.remove(obj_to_remove, do_unlink=True)

    while len(matching_objs) < count_needed:
        new_index = len(col.objects)
        
        new_obj = add_floorelement_booth(
            target_type, 
            props.floor_width, 
            props.floor_length, 
            props.floor_height,
            props.floorelement_rotation_random,
            new_index
        )
        
        new_obj.individual_floorelement_type = target_type
        new_obj.individual_floorelement_color = target_color
        matching_objs.append(new_obj)
        
def update_floorelement_style(self, context):
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_floorelement")
    
    verts, faces = create_floorelement_mesh(props.floorelement_type)
    mat = add_material("Booth_floorelement_Mat", props.floorelement_color)
    
    for obj in col.objects:
        obj.data.clear_geometry()
        obj.data.from_pydata(verts, [], faces)
        obj.data.update()
        obj.location.z = props.floor_height
        if not obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

def add_floorelement_booth(floorelement_type, floor_width, floor_length, floor_height, rot_random, index):
    verts, faces = create_floorelement_mesh(floorelement_type)
    mesh_data = bpy.data.meshes.new(f"floorelement_Mesh_{index}")
    mesh_data.from_pydata(verts, [], faces)
    mesh_data.update()
    
    obj = bpy.data.objects.new(f"Booth_floorelement_{index}", mesh_data)
    col = get_or_create_collection("Booth_floorelement")
    col.objects.link(obj)

    props = bpy.context.scene.generative_booth_props
    obj.individual_floorelement_type = floorelement_type
    obj.individual_floorelement_color = props.floorelement_color
    
    bpy.context.view_layer.update()

    margin = 0.5
    x_max = (floor_width / 2.0) - margin
    y_max = (floor_length / 2.0) - margin
    
    for _ in range(100):
        new_x = random.uniform(-x_max, x_max)
        new_y = random.uniform(-y_max, y_max)
        if not is_overlapping(new_x, new_y, obj, bpy.context, safety_margin=0.8):
            obj.location.x = new_x
            obj.location.y = new_y
            break
    else:
        obj.location.x = random.uniform(-x_max, x_max)
        obj.location.y = random.uniform(-y_max, y_max)
        
    obj.location.z = floor_height
    
    rotation_intensity = rot_random * 5.0
    random.seed(index + 900) 
    rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
    obj.rotation_euler.z = math.radians(rand_angle)
    
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj

def update_floorelement_rotation(self, context):
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_floorelement")
    
    rotation_intensity = props.floorelement_rotation_random * 5.0
    
    for i, obj in enumerate(col.objects):
        random.seed(i + 900)
        rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
        obj.rotation_euler.z = math.radians(rand_angle)
        
def update_individual_element_style(self, context):
    """Triggers whenever a clicked element changes its type or color tint."""
    if not self or self.type != 'MESH':
        return
        
    props = context.scene.generative_booth_props
        
    verts, faces = create_floorelement_mesh(self.individual_floorelement_type)
    self.data.clear_geometry()
    self.data.from_pydata(verts, [], faces)
    self.data.update()
    
    current_type = self.individual_floorelement_type
    matching_count = sum(
        1 for o in context.scene.objects 
        if o.name.startswith("Booth_floorelement_") 
        and getattr(o, "individual_floorelement_type", "") == current_type
    )
    
    props.programmatic_update = True
    props.floorelement_count = matching_count
    props.programmatic_update = False
    
    mat_name = f"Mat_{self.name}_Unique"
    color_tuple = (
        self.individual_floorelement_color[0],
        self.individual_floorelement_color[1],
        self.individual_floorelement_color[2],
        self.individual_floorelement_color[3]
    )
    
    mat = add_material(mat_name, color_tuple)
    if not self.data.materials:
        self.data.materials.append(mat)
    else:
        self.data.materials[0] = mat
        
def sync_ui_on_selection_change(scene):
    """Safely updates the count slider when a user selects a different asset type."""
    context = bpy.context
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_floorelement_"):
        props = context.scene.generative_booth_props
        current_type = getattr(active_obj, "individual_floorelement_type", "")
        
        matching_count = sum(
            1 for o in context.scene.objects 
            if o.name.startswith("Booth_floorelement_") 
            and getattr(o, "individual_floorelement_type", "") == current_type
        )
        
        if props.floorelement_count != matching_count:
            props.programmatic_update = True
            props.floorelement_count = matching_count
            props.programmatic_update = False

#_____CEILING ELEMENT_____

def create_ceilingelement_mesh(ceilingelement_type):
    if ceilingelement_type == 'CEILINGELEMENT_A':
        verts = [(-0.0, 0.115, -0.023), (-0.0, 0.115, -0.0), (0.0813, 0.0813, -0.023), (0.0813, 0.0813, -0.0), (0.115, 0.0, -0.023), (0.115, 0.0, -0.0), (0.0813, -0.0813, -0.023), (0.0813, -0.0813, -0.0), (-0.0, -0.115, -0.023), (-0.0, -0.115, -0.0), (-0.0813, -0.0813, -0.023), (-0.0813, -0.0813, -0.0), (-0.115, 0.0, -0.023), (-0.115, 0.0, -0.0), (-0.0813, 0.0813, -0.023), (-0.0813, 0.0813, -0.0), (-0.0, 0.0856, -0.023), (0.0605, 0.0605, -0.023), (0.0856, 0.0, -0.023), (0.0605, -0.0605, -0.023), (-0.0, -0.0856, -0.023), (-0.0605, -0.0605, -0.023), (-0.0856, 0.0, -0.023), (-0.0605, 0.0605, -0.023), (-0.0, 0.0856, -0.0116), (0.0605, 0.0605, -0.0116), (0.0856, 0.0, -0.0116), (0.0605, -0.0605, -0.0116), (-0.0, -0.0856, -0.0116), (-0.0605, -0.0605, -0.0116), (-0.0856, 0.0, -0.0116), (-0.0605, 0.0605, -0.0116), (-0.0, 0.0, -0.0), (-0.0, -0.0, -0.0116)]
        faces = [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6), (6, 7, 9, 8), (8, 9, 11, 10), (10, 11, 13, 12), (1, 15, 32, 3), (12, 13, 15, 14), (14, 15, 1, 0), (4, 6, 19, 18), (23, 16, 24, 31), (10, 12, 22, 21), (6, 8, 20, 19), (12, 14, 23, 22), (2, 4, 18, 17), (8, 10, 21, 20), (14, 0, 16, 23), (0, 2, 17, 16), (28, 29, 33, 27), (21, 22, 30, 29), (19, 20, 28, 27), (17, 18, 26, 25), (22, 23, 31, 30), (20, 21, 29, 28), (18, 19, 27, 26), (16, 17, 25, 24), (15, 13, 11, 32), (3, 32, 7, 5), (32, 11, 9, 7), (29, 30, 31, 33), (27, 33, 25, 26), (33, 31, 24, 25)]
    
    elif ceilingelement_type == 'CEILINGELEMENT_B':
        verts = [(-0.6, -0.0375, -0.023), (-0.6, -0.0375, 0.0), (-0.6, 0.0375, -0.023), (-0.6, 0.0375, 0.0), (0.6, -0.0375, -0.023), (0.6, -0.0375, 0.0), (0.6, 0.0375, -0.023), (0.6, 0.0375, 0.0)]
        faces = [(0, 1, 3, 2), (2, 3, 7, 6), (6, 7, 5, 4), (4, 5, 1, 0), (2, 6, 4, 0), (7, 3, 1, 5)]
        
    else:
        verts = [(0.0115, 0.0156, -0.0861), (0.0115, 0.0156, -0.0169), (0.0315, 0.0156, -0.0861), (0.0315, 0.0156, -0.0169), (0.0115, -0.0061, -0.0861), (0.0115, -0.0061, -0.0169), (0.0315, -0.0061, -0.0861), (0.0315, -0.0061, -0.0169), (-0.0365, 0.0234, -0.1939), (0.0817, 0.0234, -0.1397), (-0.0365, -0.0139, -0.1939), (0.0817, -0.0139, -0.1397), (-0.0466, -0.0403, -0.1717), (0.0715, -0.0403, -0.1175), (-0.061, -0.0403, -0.1404), (0.0572, -0.0403, -0.0862), (-0.0711, -0.0139, -0.1183), (0.047, -0.0139, -0.0641), (-0.0711, 0.0234, -0.1183), (0.047, 0.0234, -0.0641), (-0.061, 0.0497, -0.1404), (0.0572, 0.0497, -0.0862), (-0.0466, 0.0497, -0.1717), (0.0715, 0.0497, -0.1175), (-0.0392, 0.0205, -0.188), (-0.0392, -0.011, -0.188), (-0.0478, -0.0333, -0.1693), (-0.0599, -0.0333, -0.1429), (-0.0684, -0.011, -0.1242), (-0.0684, 0.0205, -0.1242), (-0.0599, 0.0427, -0.1429), (-0.0478, 0.0427, -0.1693), (0.0182, 0.0205, -0.1617), (0.0182, -0.011, -0.1617), (0.0096, -0.0333, -0.143), (-0.0025, -0.0333, -0.1166), (-0.0111, -0.011, -0.0979), (-0.0111, 0.0205, -0.0979), (-0.0025, 0.0427, -0.1166), (0.0096, 0.0427, -0.143), (0.0643, 0.0047, -0.1019), (0.0036, 0.0047, -0.1298), (-0.0563, 0.0483, -0.0211), (-0.0563, 0.0483, -0.0001), (0.0757, 0.0483, -0.0211), (0.0757, 0.0483, -0.0001), (-0.0563, -0.0388, -0.0211), (-0.0563, -0.0388, -0.0001), (0.0757, -0.0388, -0.0211), (0.0757, -0.0388, -0.0001)]
        faces = [(0, 1, 3, 2), (2, 3, 7, 6), (6, 7, 5, 4), (4, 5, 1, 0), (2, 6, 4, 0), (7, 3, 1, 5), (8, 9, 11, 10), (10, 11, 13, 12), (12, 13, 15, 14), (14, 15, 17, 16), (16, 17, 19, 18), (18, 19, 21, 20), (9, 23, 40, 11), (20, 21, 23, 22), (22, 23, 9, 8), (12, 14, 27, 26), (31, 24, 32, 39), (18, 20, 30, 29), (14, 16, 28, 27), (20, 22, 31, 30), (10, 12, 26, 25), (16, 18, 29, 28), (22, 8, 24, 31), (8, 10, 25, 24), (36, 37, 41, 35), (29, 30, 38, 37), (27, 28, 36, 35), (25, 26, 34, 33), (30, 31, 39, 38), (28, 29, 37, 36), (26, 27, 35, 34), (24, 25, 33, 32), (23, 21, 19, 40), (11, 40, 15, 13), (40, 19, 17, 15), (37, 38, 39, 41), (35, 41, 33, 34), (41, 39, 32, 33), (42, 43, 45, 44), (44, 45, 49, 48), (48, 49, 47, 46), (46, 47, 43, 42), (44, 48, 46, 42), (49, 45, 43, 47)]
        
    return verts, faces

def update_ceilingelement_count(self, context):
    props = context.scene.generative_booth_props
    if getattr(props, "programmatic_update", False):
        return

    col = get_or_create_collection("Booth_CeilingElements")
    current_objects = list(col.objects)
    
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_ceilingelement_"):
        target_type = active_obj.individual_ceilingelement_type
        target_color = active_obj.individual_ceilingelement_color
    else:
        target_type = props.ceilingelement_type
        target_color = props.ceilingelement_color

    matching_objs = [o for o in current_objects if getattr(o, "individual_ceilingelement_type", "") == target_type]
    count_needed = props.ceilingelement_count
    target_z = props.booth_master_height - props.roof_height

    while len(matching_objs) > count_needed:
        obj_to_remove = matching_objs[-1]
        
        if context.active_object == obj_to_remove:
            remaining_companions = [o for o in matching_objs if o != obj_to_remove]
            if remaining_companions:
                context.view_layer.objects.active = remaining_companions[-1]
                remaining_companions[-1].select_set(True)
            else:
                context.view_layer.objects.active = None
                
        matching_objs.remove(obj_to_remove)
        bpy.data.objects.remove(obj_to_remove, do_unlink=True)

    while len(matching_objs) < count_needed:
        new_index = len(col.objects)
        
        new_obj = add_ceilingelement_booth(
            target_type, 
            props.floor_width, 
            props.floor_length, 
            target_z,
            props.ceilingelement_rotation_random,
            new_index
        )
        
        new_obj.individual_ceilingelement_type = target_type
        new_obj.individual_ceilingelement_color = target_color
        
        mat = add_emission_material("Booth_Ceiling_Emission_Mat", target_color, strength=10.0)
        if not new_obj.data.materials:
            new_obj.data.materials.append(mat)
        else:
            new_obj.data.materials[0] = mat
            
        matching_objs.append(new_obj)

def update_ceilingelement_style(self, context):
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_CeilingElements")
    
    verts, faces = create_ceilingelement_mesh(props.ceilingelement_type)
    mat = add_emission_material("Booth_Ceiling_Emission_Mat", props.ceilingelement_color, strength=10.0)
    
    for obj in col.objects:
        obj.data.clear_geometry()
        obj.data.from_pydata(verts, [], faces)
        obj.data.update()
        obj.location.z = props.booth_master_height - props.roof_height
        if not obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

def add_ceilingelement_booth(ceilingelement_type, floor_width, floor_length, target_z, rot_random, index):
    verts, faces = create_ceilingelement_mesh(ceilingelement_type)
    mesh_data = bpy.data.meshes.new(f"ceilingelement_Mesh_{index}")
    mesh_data.from_pydata(verts, [], faces)
    mesh_data.update()
    
    obj = bpy.data.objects.new(f"Booth_ceilingelement_{index}", mesh_data)
    col = get_or_create_collection("Booth_CeilingElements")
    col.objects.link(obj)

    props = bpy.context.scene.generative_booth_props
    obj.individual_ceilingelement_type = ceilingelement_type
    obj.individual_ceilingelement_color = props.ceilingelement_color
    
    bpy.context.view_layer.update()

    margin = 0.5
    x_max = (floor_width / 2.0) - margin
    y_max = (floor_length / 2.0) - margin
    
    for _ in range(100):
        new_x = random.uniform(-x_max, x_max)
        new_y = random.uniform(-y_max, y_max)
        if not is_overlapping(new_x, new_y, obj, bpy.context, safety_margin=0.8):
            obj.location.x = new_x
            obj.location.y = new_y
            break
    else:
        obj.location.x = random.uniform(-x_max, x_max)
        obj.location.y = random.uniform(-y_max, y_max)
        
    obj.location.z = target_z
    
    rotation_intensity = rot_random * 5.0
    random.seed(index + 1200) 
    rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
    obj.rotation_euler.z = math.radians(rand_angle)
    
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj

def update_ceilingelement_rotation(self, context):
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_CeilingElements")
    
    rotation_intensity = props.ceilingelement_rotation_random * 5.0
    
    for i, obj in enumerate(col.objects):
        random.seed(i + 1200)
        rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
        obj.rotation_euler.z = math.radians(rand_angle)
        
def update_individual_ceilingelement_style(self, context):
    """Fires immediately when a single selected ceiling object modifies its own variant or color parameters."""
    if not self or self.type != 'MESH':
        return
        
    props = context.scene.generative_booth_props
        
    verts, faces = create_ceilingelement_mesh(self.individual_ceilingelement_type)
    self.data.clear_geometry()
    self.data.from_pydata(verts, [], faces)
    self.data.update()
    
    current_type = self.individual_ceilingelement_type
    matching_count = sum(
        1 for o in context.scene.objects 
        if o.name.startswith("Booth_ceilingelement_") 
        and getattr(o, "individual_ceilingelement_type", "") == current_type
    )
    
    props.programmatic_update = True
    props.ceilingelement_count = matching_count
    props.programmatic_update = False
    
    mat_name = f"Mat_{self.name}_Unique"
    color_tuple = (
        self.individual_ceilingelement_color[0],
        self.individual_ceilingelement_color[1],
        self.individual_ceilingelement_color[2],
        self.individual_ceilingelement_color[3]
    )
    
    mat = add_emission_material(mat_name, color_tuple, strength=10.0)
    if not self.data.materials:
        self.data.materials.append(mat)
    else:
        self.data.materials[0] = mat
        
def sync_ui_on_ceilingelement_selection_change(scene):
    """Keeps property context count dynamically synchronized on simple viewport selection change."""
    context = bpy.context
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_ceilingelement_"):
        props = context.scene.generative_booth_props
        current_type = getattr(active_obj, "individual_ceilingelement_type", "")
        
        matching_count = sum(
            1 for o in context.scene.objects 
            if o.name.startswith("Booth_ceilingelement_") 
            and getattr(o, "individual_ceilingelement_type", "") == current_type
        )
        
        if props.ceilingelement_count != matching_count:
            props.programmatic_update = True
            props.ceilingelement_count = matching_count
            props.programmatic_update = False

#_____POLE_____

def update_pole_count(self, context):
    props = context.scene.generative_booth_props
    if getattr(props, "programmatic_update", False):
        return

    col = get_or_create_collection("Booth_Poles")
    current_objects = list(col.objects)
    
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_Pole_"):
        target_color = active_obj.individual_pole_color
    else:
        target_color = props.pole_color

    count_needed = props.pole_count

    while len(current_objects) > count_needed:
        obj_to_remove = current_objects[-1]
        
        if context.active_object == obj_to_remove:
            remaining_companions = [o for o in current_objects if o != obj_to_remove]
            if remaining_companions:
                context.view_layer.objects.active = remaining_companions[-1]
                remaining_companions[-1].select_set(True)
            else:
                context.view_layer.objects.active = None
                
        current_objects.remove(obj_to_remove)
        bpy.data.objects.remove(obj_to_remove, do_unlink=True)

    while len(current_objects) < count_needed:
        new_index = len(col.objects)
        
        new_obj = add_pole_booth(
            props.floor_width, 
            props.floor_length, 
            props.floor_height, 
            props.booth_master_height, 
            props.roof_height,
            new_index
        )
        
        new_obj.individual_pole_color = target_color
        
        mat = add_material("Booth_Pole_Mat", target_color)
        if not new_obj.data.materials:
            new_obj.data.materials.append(mat)
        else:
            new_obj.data.materials[0] = mat
            
        current_objects.append(new_obj)

def update_pole_color(self, context):
    props = context.scene.generative_booth_props
    col = bpy.data.collections.get("Booth_Poles")
    if col:
        mat = add_material("Booth_Pole_Mat", props.pole_color)
        for obj in col.objects:
            if obj.type == 'MESH':
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat

def add_pole_booth(floor_width, floor_length, floor_height, master_height, roof_height, index):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = f"Booth_Pole_{index}"
    
    target_col_name = "Booth_Poles"
    col = get_or_create_collection(target_col_name)
    
    if obj.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(obj)
        
    for other_col in bpy.data.collections:
        if other_col.name != target_col_name and obj.name in other_col.objects:
            other_col.objects.unlink(obj)
            
    if obj.name not in col.objects:
        col.objects.link(obj)

    dynamic_gap = master_height - floor_height - roof_height
    obj.scale = (0.1, 0.1, dynamic_gap)
    
    props = bpy.context.scene.generative_booth_props
    obj.individual_pole_color = props.pole_color
    
    bpy.context.view_layer.update()

    margin = 0.2
    
    for _ in range(100):
        new_x = random.uniform(-(floor_width / 2) + margin, (floor_width / 2) - margin)
        new_y = random.uniform(-(floor_length / 2) + margin, (floor_length / 2) - margin)
        if not is_overlapping(new_x, new_y, obj, bpy.context, safety_margin=0.6):
            obj.location.x = new_x
            obj.location.y = new_y
            break
    else:
        obj.location.x = random.uniform(-(floor_width / 2) + margin, (floor_width / 2) - margin)
        obj.location.y = random.uniform(-(floor_length / 2) + margin, (floor_length / 2) - margin)
        
    obj.location.z = floor_height + (dynamic_gap / 2.0)
    
    return obj

def update_individual_pole_style(self, context):
    """Triggers whenever a clicked individual pole instance modifies its color tint parameters."""
    if not self or self.type != 'MESH':
        return
        
    mat_name = f"Mat_{self.name}_Unique"
    color_tuple = (
        self.individual_pole_color[0],
        self.individual_pole_color[1],
        self.individual_pole_color[2],
        self.individual_pole_color[3]
    )
    
    mat = add_material(mat_name, color_tuple)
    if not self.data.materials:
        self.data.materials.append(mat)
    else:
        self.data.materials[0] = mat
        
def sync_ui_on_pole_selection_change(scene):
    """Ensures UI panel sync behaviors when switching selection profiles."""
    context = bpy.context
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_Pole_"):
        props = context.scene.generative_booth_props
        
        matching_count = sum(
            1 for o in context.scene.objects 
            if o.name.startswith("Booth_Pole_")
        )
        
        if props.pole_count != matching_count:
            props.programmatic_update = True
            props.pole_count = matching_count
            props.programmatic_update = False
        
# ______________LIGHTS______________

def toggle_light_visibility(light_name, visible):
    try:
        light_obj = bpy.data.objects[light_name]
        light_obj.hide_set(not visible) 
        light_obj.hide_render = not visible 
    except KeyError:
        pass

def add_top_area_light():
    bpy.ops.object.light_add(type='AREA', radius=5, align='WORLD', location=(0, 0, 6), scale=(1, 1, 1))
    light = bpy.context.object
    light.name = "Area_Light_Top"
    light.data.energy = 200
    
    col = get_or_create_collection("Booth_Lights")
    if light.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(light)
    if light.name not in col.objects:
        col.objects.link(light)

def add_back_area_light():
    bpy.ops.object.light_add(type='AREA', radius=3.5, align='WORLD', location=(0, -4, 3), rotation=(math.radians(60), 0, 0), scale=(1, 1, 1))
    light = bpy.context.object
    light.name = "Area_Light_Back"
    light.data.energy = 200
    
    col = get_or_create_collection("Booth_Lights")
    if light.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(light)
    if light.name not in col.objects:
        col.objects.link(light)

def add_front_area_light():
    bpy.ops.object.light_add(type='AREA', radius=3.5, align='WORLD', location=(0, 4, 3), rotation=(math.radians(-60), 0, 0), scale=(1, 1, 1))
    light = bpy.context.object
    light.name = "Area_Light_Front"
    light.data.energy = 200 
    
    col = get_or_create_collection("Booth_Lights")
    if light.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(light)
    if light.name not in col.objects:
        col.objects.link(light)

def add_left_area_light():
    bpy.ops.object.light_add(type='AREA', radius=3.5, align='WORLD', location=(4, 0, 3), rotation=(0, math.radians(60), 0), scale=(1, 1, 1))
    light = bpy.context.object
    light.name = "Area_Light_Left"
    light.data.energy = 200 
    
    col = get_or_create_collection("Booth_Lights")
    if light.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(light)
    if light.name not in col.objects:
        col.objects.link(light)
    
def add_right_area_light():
    bpy.ops.object.light_add(type='AREA', radius=3.5, align='WORLD', location=(-4, 0, 3), rotation=(0, math.radians(-60), 0), scale=(1, 1, 1))
    light = bpy.context.object
    light.name = "Area_Light_Right"
    light.data.energy = 200 
    
    col = get_or_create_collection("Booth_Lights")
    if light.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(light)
    if light.name not in col.objects:
        col.objects.link(light)

def add_all_lights():
    light_funcs = [
        add_top_area_light, 
        add_back_area_light, 
        add_front_area_light, 
        add_left_area_light, 
        add_right_area_light
    ]
    
    col = get_or_create_collection("Booth_Lights")
    
    for func in light_funcs:
        func()
        light = bpy.context.object
        
        if light.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(light)
        if light.name not in col.objects:
            col.objects.link(light)
    
    
def create_human_mesh(gender_type, target_height):
    if gender_type == 'WOMAN':
        verts = [(0.1412, -0.2294, 1.4349), (0.113, -0.1984, 1.4428), (-0.0225, -0.2325, 1.4099), (-0.0686, -0.2199, 1.4147), (-0.1129, -0.1489, 1.3672), (0.1986, 0.154, 1.5336), (-0.2584, 0.0935, 1.3018), (-0.2472, 0.084, 1.3699), (-0.258, 0.0911, 1.401), (-0.2005, 0.1117, 1.2897), (-0.1077, 0.1031, 1.3259), (0.045, -0.0508, 1.9138), (-0.0399, -0.0044, 1.7285), (0.2149, 0.1073, 1.5306), (0.0568, 0.0581, 1.972), (-0.1473, 0.034, 1.5883), (-0.2083, 0.1136, 1.6529), (-0.1608, 0.1062, 0.8721), (0.1956, 0.0889, 1.6644), (0.1765, 0.2063, 0.4904), (-0.0365, 0.2236, 1.5694), (0.1214, 0.1809, 1.6792), (-0.0806, 0.1936, 1.6655), (-0.1501, -0.0394, 0.8721), (-0.0793, -0.248, 1.3683), (-0.1475, 0.1031, 0.2202), (-0.0912, -0.1029, 1.3691), (0.1541, 0.0941, 1.3123), (-0.1785, 0.142, 1.4066), (-0.0144, -0.0595, 1.8354), (-0.0509, -0.059, 1.5359), (0.0139, 0.1537, 1.3182), (-0.0898, 0.114, 1.9034), (0.017, 0.2191, 0.8663), (-0.1322, 0.1031, 1.8357), (0.0734, 0.1416, 0.6474), (0.1305, -0.2119, 1.3822), (0.211, 0.1715, 0.0801), (0.0457, 0.0589, 1.774), (0.1499, 0.0702, 0.5765), (-0.0677, 0.0349, 0.6125), (-0.0902, 0.2008, 1.5703), (0.2211, 0.1654, 0.5013), (-0.1726, 0.0389, 0.2379), (0.1403, 0.1541, 0.698), (-0.0764, 0.0495, 1.9721), (-0.1191, 0.0244, 1.3244), (0.0211, -0.28, 1.4061), (-0.1178, 0.107, 0.6651), (-0.1193, 0.0527, 1.8353), (0.18, 0.1243, 0.6682), (-0.1113, -0.0178, 0.6337), (0.216, 0.0846, 1.2791), (0.1208, 0.0425, 0.6312), (-0.1699, 0.0679, 0.659), (0.126, 0.1149, 1.6984), (0.0085, 0.0209, 2.0), (0.0082, -0.0052, 1.7269), (0.1819, -0.0804, 1.3879), (0.1902, 0.1166, 0.1952), (-0.1338, 0.1857, 1.5544), (-0.053, -0.2907, 1.3864), (-0.129, 0.1375, 0.4982), (0.1941, 0.1989, 0.2205), (-0.1285, 0.0366, 0.2457), (-0.0237, 0.0681, 1.6933), (-0.1395, 0.0956, -0.0), (0.2202, 0.1549, 0.2127), (-0.1585, 0.0264, -0.0), (-0.1146, 0.033, 0.0998), (-0.0371, -0.1533, 1.3696), (-0.1438, 0.1477, 0.1309), (-0.1477, 0.0942, 1.3927), (0.2393, 0.0978, -0.0), (0.1569, 0.0941, 0.0643), (0.1352, 0.0019, 1.536), (-0.0288, 0.1401, 1.9119), (0.1587, 0.1374, 0.2131), (0.0512, 0.2299, 1.5508), (-0.0384, -0.2129, 1.4254), (0.1711, -0.2372, 1.4711), (0.0127, 0.1862, 1.4946), (0.0451, -0.052, 1.3262), (-0.1894, 0.1054, 0.5041), (-0.0979, -0.0419, 0.8721), (0.1792, 0.1479, 1.6544), (-0.1493, 0.0015, 1.2889), (-0.0825, 0.0921, 0.4566), (0.2199, -0.0156, 1.3484), (-0.0153, 0.0322, 1.7346), (0.1965, 0.1356, 1.3537), (-0.0864, -0.0361, 1.8992), (-0.2097, 0.0059, -0.0), (0.2208, 0.2395, 0.1308), (-0.1453, 0.0698, 1.4904), (0.1432, 0.0616, 1.4488), (0.1086, 0.0478, 1.8346), (0.1895, -0.0435, -0.0), (-0.1793, 0.0223, 0.8721), (-0.1096, -0.0332, -0.0), (0.0395, 0.0933, 1.7092), (0.1627, 0.091, -0.0), (-0.0147, -0.0598, 1.7885), (0.0926, 0.1159, 1.7278), (0.1042, 0.1004, 1.3119), (0.1053, -0.0181, 0.8726), (0.1684, 0.2029, 0.1296), (-0.0406, -0.2522, 1.3784), (-0.112, 0.0607, 1.7483), (0.1605, 0.0572, 0.6522), (-0.0101, -0.0747, 1.88), (0.1287, -0.2804, 1.4756), (0.1458, 0.0402, 1.313), (0.1086, 0.1586, 0.5998), (0.1892, 0.0522, 0.0581), (-0.0543, 0.2194, 1.6579), (-0.1546, -0.0373, 0.0491), (-0.0377, -0.2692, 1.4186), (0.0585, 0.0577, 1.7409), (-0.1891, 0.0429, 1.3591), (-0.099, 0.0047, 1.9422), (-0.1199, -0.0171, 1.513), (0.0324, 0.2188, 1.6738), (0.1209, 0.1724, 0.4544), (0.1508, -0.2577, 1.4013), (-0.0297, -0.1959, 1.3739), (-0.2008, 0.0576, 1.4736), (-0.0235, -0.1972, 1.4027), (-0.0707, 0.1679, 1.7566), (-0.0053, 0.1095, 1.9645), (-0.1982, 0.0716, 1.6464), (0.1235, -0.2318, 1.4051), (-0.1021, -0.1688, 1.3554), (-0.0742, -0.0306, 1.8395), (0.0982, 0.105, 0.5686), (-0.1809, -0.1317, -0.0), (-0.1315, 0.0086, 0.576), (-0.1897, 0.0562, 0.0856), (0.1769, 0.0049, 1.2931), (0.1601, -0.0542, 1.3756), (0.0452, -0.0278, 1.8415), (0.1975, 0.0902, 0.4522), (-0.1276, 0.1008, 0.2039), (-0.0562, 0.1935, 1.5758), (0.0892, 0.2075, 1.5925), (0.0932, -0.0581, 1.5349), (-0.2341, 0.0911, 1.4903), (-0.131, 0.004, 0.1137), (0.1527, -0.1769, 1.3745), (-0.0573, 0.1753, 1.8146), (0.1709, 0.1632, 1.5481), (-0.0061, -0.2941, 1.3886), (-0.0743, 0.1042, 1.7026), (-0.153, 0.0844, 0.0717), (0.249, 0.0954, 0.0526), (-0.2344, 0.1388, 1.3912), (-0.1023, 0.1074, 0.1171), (0.1077, -0.2642, 1.4766), (0.1419, 0.1135, 1.3685), (0.1951, 0.1962, 0.0728), (-0.1101, 0.1099, 1.7008), (-0.1231, 0.1246, 1.416), (-0.0105, -0.2606, 1.391), (-0.0967, -0.0172, 1.3213), (0.0622, 0.0574, 1.8241), (0.0231, 0.2102, 1.724), (0.1963, 0.0211, 1.3863), (0.0387, -0.0285, 1.801), (0.0844, 0.1361, 1.7907), (-0.0732, 0.0691, 0.5844), (-0.0778, -0.1339, 1.3924), (-0.0362, -0.0535, 1.3256), (-0.0561, 0.0752, 0.6441), (-0.2258, 0.0055, 1.3066), (0.1842, 0.0439, 1.4121), (0.1578, 0.0304, -0.0), (-0.2115, 0.1488, 1.5344), (0.1249, -0.211, 1.4716), (-0.1562, 0.1414, 1.4683), (-0.1787, 0.087, 1.3214), (-0.2057, 0.0077, 0.032), (0.0982, 0.0151, 1.8305), (-0.1323, 0.0804, 0.0636), (-0.0283, 0.1851, 1.7317), (-0.0691, 0.0535, 1.7722), (-0.1297, 0.1055, 0.0596), (0.0103, -0.0476, 1.5114), (-0.09, -0.1529, 1.3406), (-0.0046, -0.0403, 1.9709), (-0.1553, 0.006, 0.6275), (-0.1538, 0.0773, 1.3789), (0.1776, -0.2529, 1.4385), (0.1956, 0.1578, 0.0717), (0.1485, -0.2461, 1.4841), (-0.128, 0.1215, 1.7448), (0.1672, 0.015, 0.8726), (-0.2136, 0.0042, 1.3454), (0.1873, 0.1883, -0.0), (-0.0656, 0.1322, 0.8721), (-0.144, 0.0398, 0.0467), (0.2098, 0.1804, -0.0), (0.2157, 0.133, 0.1849), (0.2307, 0.0931, 1.3542), (-0.223, 0.0474, 1.3652), (-0.1865, 0.1609, 1.595), (-0.1742, 0.0751, 0.2018), (0.0107, -0.236, 1.3943), (-0.0853, 0.087, 1.69), (0.1419, -0.1017, 1.3536), (-0.087, 0.1804, 1.6929), (0.1503, -0.1623, 1.4273), (-0.2337, 0.0848, 1.2608), (0.0937, 0.0713, 1.7615), (-0.1786, 0.0239, 0.1499), (0.0154, 0.1697, 1.8287), (0.1751, 0.1086, 0.8726), (-0.0789, -0.1381, 0.8663), (-0.166, -0.1209, 0.8663), (-0.2481, 0.1674, 0.8663), (0.1309, 0.1838, 1.6275), (-0.0204, 0.0501, 0.8721), (0.0984, -0.0303, 1.3234), (-0.2377, -0.1153, 0.8663), (0.0449, -0.1271, 0.8663), (0.1186, -0.0816, 0.8663), (0.2107, -0.0582, 0.8663), (-0.2596, 0.0086, 0.8663), (-0.0219, -0.0768, 1.9295), (0.1265, 0.155, 0.8726), (0.0191, 0.1351, 0.8726), (0.0682, 0.0974, 0.6564), (0.008, 0.0909, 0.8726), (0.2536, 0.1502, 0.8663), (0.2241, 0.1844, 0.8663), (-0.0504, -0.0678, 1.8889), (-0.0227, -0.2777, 1.5162), (0.115, -0.2777, 1.5162), (-0.0227, -0.1732, 1.3354), (0.115, -0.1732, 1.3354)]
        faces = [(0, 1, 36), (127, 79, 2), (2, 24, 125), (3, 4, 24), (31, 104, 233, 33), (58, 148, 88), (58, 88, 166), (46, 163, 121, 94), (208, 27, 138), (100, 89, 65), (173, 187, 4), (18, 95, 174), (112, 75, 145, 221), (7, 203, 8), (21, 144, 122, 165), (57, 89, 38), (184, 12, 133), (11, 227, 110), (14, 96, 168), (227, 11, 188), (150, 90, 158), (158, 90, 27), (75, 95, 18), (112, 225, 232), (8, 126, 146), (204, 16, 22), (126, 130, 146), (145, 75, 18, 55), (60, 22, 41), (112, 104, 158), (151, 117, 61), (81, 143, 20), (132, 187, 24), (187, 125, 24), (26, 179, 119), (187, 86, 26), (110, 234, 133), (119, 179, 72), (155, 28, 9), (15, 121, 160), (144, 104, 31, 81), (162, 2, 47), (2, 107, 24), (21, 165, 214, 168), (209, 16, 160), (130, 15, 160), (109, 50, 215, 195), (134, 123, 77), (168, 96, 212), (18, 85, 55), (173, 4, 196), (39, 134, 59), (19, 42, 67, 63), (40, 136, 64), (39, 59, 201, 141, 109), (201, 67, 42, 141), (25, 62, 87, 142), (142, 87, 64), (134, 113, 123), (56, 129, 45), (194, 128, 209, 160), (155, 9, 6), (109, 141, 42, 50), (51, 136, 40), (148, 138, 88), (53, 134, 39), (19, 123, 113, 44), (89, 100, 38), (102, 57, 167), (210, 177, 80), (210, 191, 148), (106, 77, 63), (8, 146, 176, 155), (61, 24, 107), (61, 3, 24), (48, 172, 169, 87, 62), (166, 112, 139), (139, 58, 166), (83, 43, 189), (205, 71, 137), (64, 69, 142), (64, 43, 147), (63, 67, 93), (201, 59, 114), (139, 112, 27), (27, 112, 158), (143, 81, 31, 10), (135, 99, 116), (69, 156, 142), (187, 26, 70), (127, 170, 79), (71, 205, 25), (179, 28, 72), (14, 56, 11), (11, 164, 181), (201, 154, 93), (77, 106, 74), (192, 73, 101), (12, 89, 57), (12, 57, 102), (59, 77, 114), (77, 59, 134), (20, 78, 81), (47, 79, 117), (170, 4, 3), (80, 191, 210), (191, 80, 111), (10, 161, 41, 143), (80, 177, 193), (221, 145, 186, 82), (85, 21, 55), (219, 21, 85), (73, 37, 154), (211, 9, 86), (26, 86, 179), (40, 64, 169), (88, 202, 166), (202, 88, 52), (65, 89, 184), (184, 89, 12), (27, 90, 52), (90, 202, 52), (92, 68, 99), (137, 71, 153), (37, 93, 154), (106, 192, 74), (15, 94, 121), (95, 75, 112), (154, 97, 73), (175, 73, 97), (68, 199, 99), (147, 69, 64), (145, 55, 100), (101, 74, 192), (175, 97, 74), (102, 29, 133), (118, 55, 103), (212, 181, 118), (91, 234, 227, 120), (106, 63, 93), (184, 152, 65), (109, 53, 39), (133, 29, 110), (97, 154, 114), (154, 201, 114), (143, 115, 20), (213, 180, 116), (116, 147, 213), (3, 61, 117), (3, 117, 79), (118, 100, 55), (38, 100, 118), (119, 203, 26), (56, 45, 188), (188, 11, 56), (122, 20, 115), (124, 148, 191), (187, 70, 125), (2, 125, 127), (183, 214, 165), (94, 119, 190), (128, 183, 209), (76, 149, 34, 32), (130, 16, 146), (16, 130, 160), (124, 131, 36), (76, 32, 45, 129), (120, 32, 34), (134, 35, 113), (230, 134, 53), (135, 116, 180), (99, 135, 92), (136, 51, 189), (180, 92, 135), (138, 27, 52), (88, 138, 52), (1, 208, 36), (139, 210, 58), (140, 29, 167), (24, 4, 132), (71, 25, 142), (41, 22, 143), (115, 143, 22), (11, 110, 140), (110, 29, 140), (148, 124, 36), (208, 138, 148), (128, 149, 183), (34, 149, 128), (85, 5, 150), (5, 90, 150), (70, 170, 127), (47, 117, 151), (184, 108, 207), (194, 160, 108), (29, 102, 167), (65, 186, 145, 100), (144, 150, 158, 104), (156, 182, 185), (106, 93, 159), (160, 207, 108), (71, 142, 156), (185, 71, 156), (178, 161, 72), (111, 80, 193), (2, 162, 107), (35, 134, 230), (53, 109, 195, 105), (167, 57, 38), (209, 183, 122, 115), (183, 165, 122), (103, 21, 168), (147, 99, 69), (99, 147, 116), (48, 62, 83, 54), (169, 64, 87), (19, 63, 77, 123), (40, 169, 172), (144, 81, 78), (6, 173, 196), (173, 6, 211), (174, 13, 18), (74, 101, 175), (175, 101, 73), (74, 114, 77), (114, 74, 97), (193, 177, 157), (28, 155, 176, 178), (72, 28, 178), (79, 170, 3), (21, 103, 55), (9, 28, 179), (9, 179, 86), (213, 137, 180), (137, 153, 180), (212, 96, 181), (153, 199, 68), (49, 184, 133), (182, 153, 66), (71, 185, 153), (184, 49, 108), (182, 66, 185), (153, 185, 66), (86, 187, 211), (187, 173, 211), (188, 120, 227), (45, 120, 188), (220, 84, 51, 40), (119, 72, 190), (32, 120, 45), (15, 130, 126), (15, 126, 94), (157, 0, 36, 131), (73, 192, 37), (0, 157, 1), (187, 132, 4), (159, 93, 37), (106, 159, 192), (22, 16, 209), (37, 192, 200), (26, 203, 196), (192, 159, 197), (159, 37, 200), (125, 206, 127), (206, 125, 70), (197, 159, 200), (200, 192, 197), (67, 201, 93), (13, 174, 202), (203, 126, 8), (78, 20, 144), (20, 122, 144), (164, 167, 38), (140, 164, 11), (204, 22, 60), (43, 83, 205), (213, 205, 137), (70, 127, 206), (220, 40, 172), (207, 65, 152), (184, 207, 152), (208, 139, 27), (208, 210, 139), (47, 2, 79), (209, 115, 22), (189, 43, 64, 136), (1, 210, 208), (1, 177, 210), (189, 54, 83), (21, 219, 144), (6, 9, 211), (133, 12, 102), (118, 103, 212), (103, 168, 212), (156, 199, 182), (153, 182, 199), (196, 4, 170), (26, 196, 170), (147, 43, 213), (157, 177, 1), (16, 204, 176, 146), (76, 214, 149), (112, 174, 95), (166, 174, 112), (54, 98, 17), (180, 153, 92), (153, 68, 92), (58, 210, 148), (213, 43, 205), (70, 26, 170), (36, 208, 148), (214, 76, 129), (140, 167, 164), (230, 53, 105, 231), (166, 202, 174), (85, 150, 219), (144, 219, 150), (119, 94, 126), (119, 126, 203), (194, 34, 128), (156, 69, 199), (199, 69, 99), (14, 129, 56), (172, 48, 198, 220), (224, 221, 82, 223), (19, 44, 50, 42), (10, 218, 226, 46), (229, 35, 230, 231), (31, 33, 218, 10), (98, 54, 189, 23), (198, 48, 54, 17), (112, 232, 233, 104), (163, 222, 217), (228, 215, 50, 44), (171, 163, 217, 216), (112, 221, 224, 225), (226, 222, 163, 46), (186, 65, 207, 30), (46, 94, 190), (216, 223, 82, 171), (30, 207, 160, 121), (234, 110, 227), (186, 30, 171, 82), (41, 161, 178, 60), (13, 202, 90, 5), (85, 18, 13, 5), (204, 60, 178, 176), (8, 155, 6, 7), (196, 203, 7, 6), (189, 51, 84, 23), (44, 113, 35, 229, 228), (83, 62, 25, 205), (163, 171, 30, 121), (224, 223, 216, 217, 222, 226, 218, 33, 233, 232, 225), (161, 10, 46, 190, 72), (181, 164, 38, 118), (234, 91, 49, 133), (108, 49, 34, 194), (120, 34, 49, 91), (214, 129, 14, 168), (181, 96, 14, 11), (214, 183, 149), (151, 61, 107, 162), (151, 162, 47), (193, 157, 111), (111, 157, 131, 124), (111, 124, 191), (235, 236, 238, 237)]
    else:
        verts = [(0.1455, 0.065, 1.7832), (0.0458, 0.0724, 1.8142), (0.1011, 0.0255, 1.8205), (0.1754, -0.0393, 1.7266), (0.338, 0.0909, 1.6316), (0.3084, 0.008, 1.6629), (0.429, 0.0813, 1.4083), (0.1478, -0.0875, 1.634), (0.1041, -0.1389, 1.5334), (-0.2282, 0.1293, 1.5682), (-0.2631, 0.0626, 1.4394), (-0.2198, 0.0119, 1.6245), (0.2551, -0.0165, 1.4436), (0.2636, 0.0717, 1.3749), (0.3134, -0.0078, 1.4127), (0.4042, 0.0103, 1.3849), (0.343, -0.0071, 1.4495), (0.2334, -0.0008, 1.3108), (0.3066, 0.1191, 1.3249), (0.2915, 0.0428, 1.3435), (0.2894, 0.0359, 1.3869), (0.3464, -0.0072, 1.358), (0.2521, 0.0106, 1.2966), (0.2752, -0.0535, 1.3066), (0.2964, 0.078, 1.2756), (0.2571, 0.0401, 1.2695), (0.2675, 0.0267, 1.2062), (0.2475, 0.0999, 1.2364), (0.3577, -0.0472, 1.2415), (0.3095, -0.0016, 1.1817), (0.4159, 0.1046, 1.2843), (-0.1501, 0.1019, 1.2827), (-0.1969, 0.0585, 1.1051), (-0.2304, 0.1157, 1.2617), (0.2266, -0.1062, 1.1498), (-0.1609, -0.0131, 1.2206), (-0.0686, -0.1722, 1.0988), (-0.0345, -0.1699, 1.2054), (-0.082, -0.1549, 1.2513), (-0.0078, -0.1365, 1.0098), (0.006, -0.1226, 1.0088), (-0.0561, 0.1691, 0.9482), (0.0827, 0.1456, 0.9447), (0.0336, 0.1276, 0.9452), (-0.2608, -0.0686, 0.9173), (-0.2415, -0.1253, 0.9469), (-0.1548, -0.0935, 0.9506), (-0.1795, -0.1269, 0.9399), (-0.1512, -0.123, 0.8645), (-0.2329, -0.0512, 0.9051), (-0.1756, -0.0652, 0.9326), (-0.2119, -0.094, 0.9168), (-0.1839, -0.1215, 0.9014), (-0.179, -0.1353, 0.8468), (-0.164, -0.1017, 0.9003), (-0.1734, -0.1203, 0.8661), (-0.1928, -0.1218, 0.8753), (-0.219, -0.0762, 0.8772), (-0.174, -0.0645, 0.8603), (-0.1568, -0.1007, 0.8404), (-0.2086, -0.1049, 0.8384), (-0.2068, -0.0503, 0.8539), (0.019, 0.0958, 0.5684), (-0.0283, 0.1318, 0.599), (-0.1027, 0.1909, 1.1001), (-0.1042, 0.206, 1.2652), (-0.016, 0.216, 1.1119), (0.2877, 0.1236, 1.5016), (0.3087, 0.1357, 1.4311), (0.2553, 0.1274, 1.4487), (0.262, 0.0367, 1.1185), (0.1992, 0.1467, 1.1117), (0.2024, 0.1872, 1.5233), (0.2165, 0.1498, 1.2726), (-0.0061, -0.0423, 1.6617), (-0.0399, -0.0558, 1.625), (-0.0128, -0.1097, 1.4672), (-0.0049, 0.0574, 1.8356), (-0.047, 0.0172, 1.8148), (-0.0514, 0.0344, 1.8941), (-0.2556, -0.032, 0.9657), (-0.2401, 0.0539, 1.1069), (-0.1829, -0.0233, 0.9919), (-0.1064, 0.0628, 0.5424), (-0.071, -0.049, 0.5716), (-0.1541, -0.0374, 0.9031), (-0.1641, -0.0629, 1.0724), (-0.0937, -0.154, 1.034), (-0.1008, -0.1567, 1.0965), (0.2334, 0.0441, 0.8936), (0.1503, 0.1361, 0.9431), (0.0742, -0.1801, 1.0139), (0.063, -0.1335, 1.0154), (0.1473, -0.1519, 0.9427), (0.1462, 0.0065, 0.6811), (0.1384, -0.1203, 0.8519), (0.2021, -0.1796, 0.5848), (0.1688, -0.1207, 0.9255), (0.0474, 0.0536, 0.8586), (0.0465, -0.0077, 0.8512), (0.0719, 0.0392, 1.9038), (0.1009, -0.0156, 1.8384), (0.0498, 0.0517, 1.8442), (0.0302, -0.0885, 1.5047), (0.0447, -0.1169, 1.386), (0.0586, -0.0906, 1.4637), (-0.185, -0.0459, 1.5731), (-0.1287, -0.0953, 1.5134), (-0.0315, -0.1311, 1.5396), (0.0472, 0.2056, 1.6122), (0.1091, 0.2251, 1.6593), (0.1845, 0.1504, 1.6913), (-0.0462, 0.2487, 1.6696), (-0.0464, 0.2051, 1.6156), (-0.1318, 0.1693, 1.6915), (-0.2348, -0.0254, 1.2889), (-0.2257, -0.0777, 1.1273), (0.0798, -0.1292, 1.469), (0.0921, -0.0826, 1.5704), (0.1124, -0.1415, 1.4841), (0.196, -0.097, 1.5564), (0.06, -0.1735, 1.1428), (0.0566, -0.165, 1.3941), (0.0426, -0.1425, 1.3215), (0.0224, -0.2095, 1.2614), (-0.1491, 0.0495, 0.843), (-0.1497, 0.1467, 1.236), (-0.1636, 0.1401, 1.0857), (0.0926, -0.2161, 1.1234), (0.2367, -0.0815, 1.1033), (0.1819, -0.1726, 1.1408), (0.1561, -0.2109, 1.1877), (0.0666, -0.2243, 1.176), (-0.0281, -0.1469, 1.9284), (-0.0404, -0.0932, 1.97), (-0.0735, -0.1031, 1.9041), (0.1051, -0.0327, 1.8961), (0.0648, 0.1837, 0.9906), (-0.2678, 0.0895, 1.2914), (-0.244, 0.1107, 1.4369), (-0.2732, -0.0533, 1.1101), (0.2213, -0.0824, 0.9952), (0.1701, -0.1387, 0.9997), (0.2215, -0.1068, 0.9361), (0.2537, 0.003, 0.9292), (-0.0485, 0.0502, 1.8047), (-0.1012, -0.0255, 1.7287), (-0.0886, -0.0355, 1.7545), (-0.0932, 0.0973, 0.3119), (-0.0038, 0.1557, 0.278), (0.0283, 0.0505, 0.5181), (-0.1425, 0.0013, 1.7301), (-0.1734, 0.0961, 1.6793), (-0.282, -0.0141, 1.0533), (-0.1535, -0.0998, 0.9748), (-0.1132, -0.0979, 0.9597), (-0.0838, -0.1814, 0.9678), (-0.0269, -0.1365, 1.1513), (-0.1757, 0.1688, 1.5919), (-0.1381, 0.1388, 1.6704), (0.2692, -0.1656, 0.576), (0.1328, -0.1044, 0.6077), (0.3114, -0.0069, 0.3329), (0.2344, -0.0195, 0.6915), (0.1804, 0.0227, 0.6811), (0.1014, -0.0609, 1.8012), (0.0843, -0.112, 1.8543), (0.0641, -0.0988, 1.7223), (-0.0055, -0.1289, 1.7984), (0.0139, -0.143, 1.8497), (-0.0509, -0.1109, 1.84), (-0.1547, -0.07, 0.9506), (0.1784, -0.0927, 0.4323), (0.2268, -0.0597, 0.1863), (0.1664, -0.0109, 0.5034), (0.1915, 0.0499, 0.1941), (-0.0532, -0.0067, 1.7959), (-0.0343, -0.0232, 1.7411), (-0.0681, -0.0136, 1.8202), (-0.0769, -0.0201, 1.8603), (-0.1408, 0.1184, 1.0371), (-0.156, 0.1186, 0.9746), (-0.0632, 0.1823, 0.9861), (0.23, -0.0169, 1.698), (0.2618, -0.0472, 1.6213), (-0.0823, -0.1026, 1.6142), (-0.1497, -0.0455, 1.641), (-0.0817, -0.0884, 1.5881), (-0.1526, -0.0944, 1.6301), (0.0095, 0.1463, 0.4591), (-0.0693, 0.1393, 0.4761), (-0.1242, 0.1107, 0.8846), (-0.0521, -0.1557, 1.3855), (-0.0153, -0.1489, 1.3847), (0.0505, -0.0186, 0.0549), (0.068, 0.085, -0.0004), (0.0879, 0.0611, 0.1083), (0.2383, 0.0047, 1.0622), (0.2195, 0.0949, 0.9928), (0.2214, 0.0801, 1.0656), (0.072, -0.0554, 1.7261), (-0.0333, -0.0764, 1.7461), (-0.044, -0.1094, 1.7979), (0.0925, 0.0553, 0.2073), (-0.077, 0.0443, 0.3276), (0.001, -0.0025, 0.339), (-0.2039, -0.0207, 1.4233), (-0.1587, -0.0343, 1.3949), (-0.0828, 0.1402, 0.9204), (0.0328, -0.1502, 1.1839), (0.0073, -0.1103, 1.3349), (0.2776, -0.0384, 1.553), (0.3206, -0.0116, 1.6002), (0.4055, 0.0299, 1.4282), (0.0552, -0.2127, 1.1521), (0.0161, -0.2325, 1.1565), (0.3108, 0.0693, 0.1568), (0.236, 0.0841, 0.2558), (0.1781, -0.0152, 0.3072), (0.1675, 0.2036, 1.5858), (0.2968, 0.0607, 0.0661), (0.2542, 0.1262, 0.0395), (0.0524, -0.2248, 1.0566), (0.2376, 0.0674, 1.7139), (0.3025, 0.0777, 1.6917), (0.288, 0.1449, 1.6294), (0.1602, -0.0556, 0.4524), (0.1119, -0.0098, 0.6811), (0.0931, -0.0653, 0.8123), (0.1178, -0.0033, 1.7283), (0.1475, -0.0229, 1.7838), (0.0375, -0.0189, 0.7888), (0.0916, 0.1145, 1.8033), (0.2021, 0.1439, 1.7322), (0.0547, 0.2272, 1.7401), (-0.0028, 0.1313, 1.8094), (-0.0683, 0.196, 1.743), (-0.1146, 0.0815, 1.7757), (0.0537, -0.0985, 0.9056), (-0.2388, -0.0597, 0.8646), (-0.2418, -0.121, 0.8983), (0.1696, -0.1516, 1.3287), (-0.1821, 0.1715, 1.5414), (-0.0056, -0.098, 1.3953), (0.0598, -0.0311, 1.9893), (0.0633, -0.1343, 1.9271), (0.0983, -0.0372, 1.9338), (0.0256, -0.1434, 1.7875), (0.2299, -0.0234, 0.5291), (0.1819, -0.0216, 0.6014), (0.2741, -0.0767, 0.6426), (-0.0274, 0.0849, 0.0619), (-0.01, 0.1191, 0.1159), (0.0011, 0.1509, -0.0005), (0.0665, 0.0399, 0.344), (0.444, 0.0583, 1.3438), (0.0667, -0.1776, 1.2448), (-0.0099, -0.0646, 0.0682), (-0.0301, -0.0074, 0.0779), (0.0407, -0.0403, 0.0812), (0.0601, 0.192, 0.943), (-0.1318, 0.2003, 1.4243), (-0.1584, 0.1348, 1.4323), (-0.1647, 0.1228, 1.3493), (-0.2089, 0.15, 1.487), (0.0238, -0.1098, 1.9741), (-0.0192, -0.0243, 1.9988), (0.0133, 0.0598, 1.9164), (0.2318, -0.0336, 0.0531), (0.2612, -0.1247, 0.0044), (0.2513, -0.0603, 0.0798), (0.0437, 0.1407, 0.0003), (0.0646, 0.1264, 0.1574), (0.0314, 0.153, 0.1565), (0.2285, -0.0834, 1.6024), (0.1363, -0.1555, 1.5039), (0.0326, -0.13, 1.1037), (-0.1166, -0.0521, 1.7161), (-0.048, -0.0029, 1.7051), (-0.0128, 0.1167, 0.8611), (-0.075, 0.1092, 0.6863), (0.1105, 0.1969, 1.1098), (0.2569, -0.0094, 0.0003), (0.0558, -0.1884, 1.4279), (0.143, 0.158, 0.9876), (0.3584, -0.1735, 0.037), (0.316, -0.2026, 0.0001), (-0.1024, 0.1021, 0.5813), (0.0402, 0.2603, 1.6493), (-0.2017, -0.1304, 1.0137), (-0.0307, 0.0371, 0.0009), (0.0398, -0.1061, -0.0006), (-0.052, -0.1802, 0.0003), (-0.1912, 0.0425, 0.9773), (-0.1804, 0.0345, 1.0575), (0.2155, 0.0049, 1.7323), (0.2119, -0.0616, 1.6555), (0.1282, -0.0471, 1.66), (0.0343, 0.0167, 0.0061), (-0.0643, 0.0866, 1.7883), (-0.1684, 0.0081, 1.6745), (-0.1766, 0.0135, 1.7079), (-0.1581, 0.104, 1.728), (0.2, 0.0949, 0.0768), (0.2177, 0.1291, 0.0002), (0.1985, 0.0615, 0.0002), (0.2856, 0.0904, 0.0005), (0.2353, -0.1889, 0.5777), (0.2356, -0.1543, 1.2243), (0.2198, -0.1211, 1.2799), (-0.063, -0.1149, 0.9262), (-0.025, -0.1016, 0.9589), (-0.0606, -0.1594, 1.0179), (0.0979, -0.0253, 1.7678), (0.0911, -0.0399, 1.6611), (0.3612, 0.1431, 1.3062), (0.4071, 0.133, 1.3645), (0.049, -0.1507, 1.8736), (0.0673, -0.2137, 0.9994), (0.2258, -0.0755, 1.0501), (-0.2374, 0.0036, 1.455), (-0.0338, -0.1798, 0.0425), (0.0347, -0.1288, 0.0248), (0.0153, -0.1007, 0.053), (-0.2065, -0.1499, 0.905), (-0.0428, -0.1248, 1.0249), (-0.0804, -0.0688, 0.006), (-0.0292, -0.1489, 1.8677), (0.0941, 0.2326, 1.7081), (-0.0005, -0.0556, 1.7056), (0.0263, -0.1026, 1.7105), (0.054, -0.0802, 1.6297), (0.1772, 0.0232, 0.1113), (0.2691, -0.1039, 0.3128), (-0.0714, -0.0599, 1.8589), (-0.1372, -0.0693, 1.0396), (0.0813, -0.1767, 1.4611), (0.0427, 0.0239, 1.9788), (-0.043, 0.0256, 1.952), (-0.0754, -0.0282, 1.9494), (-0.0028, -0.1857, 0.0002), (0.1986, 0.0693, 1.7741), (-0.0962, -0.0934, 0.9126), (-0.0792, 0.0739, 0.2242), (-0.02, -0.0082, 0.2065), (-0.1438, -0.0759, 1.6457), (0.3663, -0.1784, 0.0008), (0.3695, -0.0585, 0.0002), (0.0725, -0.198, 1.2762), (0.0206, -0.2441, 1.1768), (0.0112, -0.2459, 1.0706), (0.033, -0.0078, 0.229), (0.2696, -0.0498, 0.1317), (-0.1951, -0.1407, 0.8549), (0.0149, -0.2555, 1.0064), (0.2221, 0.083, 0.9569), (0.2553, -0.0127, 0.9918), (0.1897, -0.06, 1.7222), (-0.2847, 0.0217, 1.2969), (0.2064, 0.036, 0.0493), (-0.1337, -0.0458, 1.668), (0.0627, -0.0575, 1.6868), (0.2118, -0.1129, 1.4414), (0.0906, -0.1501, 1.4435), (0.0764, -0.1373, 1.4018), (-0.2822, 0.0422, 1.2203), (-0.2654, 0.0846, 1.2163), (0.2283, -0.1433, 1.1772), (0.0185, -0.1684, 1.7984), (-0.1345, 0.1862, 1.3358), (0.1171, -0.0225, 1.8637), (0.1666, -0.1469, 1.1131), (0.163, -0.1347, 1.0537), (0.0629, 0.1727, 1.4998), (0.0917, 0.1716, 1.2697), (-0.042, 0.1722, 1.5176), (-0.0263, 0.1923, 1.267), (0.0174, 0.2026, 1.0618), (-0.0855, 0.1872, 1.0505), (0.1213, 0.184, 1.0691), (0.313, -0.0506, 1.2767), (0.3756, 0.0017, 1.3716)]
        faces = [(88, 87, 312, 36), (2, 3, 0), (120, 274, 296, 7, 8, 275), (272, 271, 253, 273), (12, 13, 14), (313, 361, 314, 229), (12, 17, 13), (186, 106, 107, 187), (18, 19, 20), (130, 367, 308, 131), (267, 100, 102, 77), (25, 24, 26), (27, 25, 26), (236, 114, 302, 237), (31, 32, 33), (233, 111, 110, 328), (90, 260, 137, 284), (41, 42, 43), (46, 47, 48), (49, 50, 51), (52, 47, 53), (48, 59, 54, 46), (52, 55, 47), (55, 48, 47), (100, 136, 101, 102), (56, 52, 53), (317, 245, 133, 327), (56, 53, 55), (48, 55, 53), (174, 175, 218, 226), (59, 48, 53), (63, 279, 98, 62), (67, 6, 316, 68), (217, 303, 332, 175), (189, 62, 150, 254), (305, 359, 303, 304), (339, 338, 79, 179), (113, 159, 114, 112), (155, 171, 85, 342), (68, 18, 13, 69), (91, 92, 93), (94, 227, 99, 98), (95, 96, 97), (112, 236, 234, 288), (103, 104, 105), (76, 75, 108), (109, 110, 111), (247, 167, 165, 166), (302, 152, 300, 301), (117, 8, 118), (362, 211, 184, 120), (18, 68, 316, 315), (122, 123, 124), (126, 127, 32), (128, 371, 130), (90, 163, 164, 42), (71, 281, 374, 73), (198, 355, 90, 284), (14, 20, 19, 21), (148, 149, 273, 343), (161, 226, 172, 96), (289, 116, 140, 45), (154, 155, 156), (36, 157, 37), (31, 126, 32), (113, 158, 159), (89, 144, 160, 250), (128, 130, 131, 132), (206, 320, 358, 115), (196, 195, 271, 272), (47, 46, 154), (154, 171, 155), (172, 173, 96), (176, 177, 178), (229, 297, 357, 230), (207, 107, 106, 206), (75, 185, 108), (186, 187, 188), (109, 113, 112, 288), (108, 192, 193), (52, 51, 50, 54), (142, 93, 143, 141), (319, 197, 70, 129), (167, 200, 165), (221, 217, 216, 220), (207, 206, 115, 35), (208, 181, 182, 41), (193, 192, 38, 37), (76, 104, 103), (157, 209, 210), (212, 16, 213), (180, 378, 182, 181), (142, 91, 93), (298, 195, 196, 194), (219, 109, 111), (295, 341, 0, 3), (46, 171, 154), (154, 335, 86, 289), (76, 103, 74, 75), (132, 222, 128), (131, 308, 309, 241), (219, 111, 225), (147, 185, 75, 278), (99, 227, 228), (2, 229, 230), (99, 228, 95), (17, 241, 309), (235, 236, 237), (282, 268, 359, 305), (95, 238, 99), (51, 57, 49), (326, 292, 321, 257), (243, 108, 193), (37, 157, 210), (247, 166, 169), (248, 249, 250), (258, 251, 290, 326), (124, 123, 256), (210, 209, 104), (260, 42, 41), (242, 261, 262), (263, 33, 264), (82, 80, 81, 32), (267, 77, 79), (268, 269, 270), (152, 159, 158, 9), (276, 40, 92), (278, 177, 176), (63, 280, 191, 279), (287, 280, 63, 190), (282, 269, 268), (117, 283, 8), (119, 120, 275), (205, 254, 150, 84), (282, 306, 269), (287, 83, 85, 125), (165, 313, 2, 101), (97, 92, 238, 95), (43, 279, 208, 41), (155, 342, 310, 39, 325), (154, 289, 47), (45, 47, 289), (290, 291, 292), (251, 258, 257), (226, 218, 173, 172), (293, 294, 180, 181), (184, 183, 296, 274), (70, 26, 34, 129), (263, 262, 261, 369), (123, 209, 121), (276, 92, 121), (306, 282, 305, 304), (290, 298, 291), (138, 358, 10, 139), (134, 339, 135, 133), (165, 246, 166), (246, 245, 166), (316, 6, 255, 30), (5, 213, 6, 4), (52, 56, 57, 51), (358, 138, 366, 365), (22, 19, 24, 25), (23, 17, 309), (310, 311, 39), (312, 156, 155), (2, 313, 229), (23, 21, 19, 22), (321, 340, 322, 323), (30, 29, 315), (288, 234, 328, 110), (175, 174, 248), (166, 317, 169), (194, 322, 291, 298), (297, 314, 118), (118, 8, 7), (91, 214, 121, 92), (108, 185, 188), (82, 294, 293), (215, 124, 256, 214), (111, 223, 224, 225), (91, 215, 214), (125, 181, 208, 191), (240, 60, 353, 324), (59, 55, 52, 54), (143, 97, 307, 160), (133, 245, 265, 134), (228, 161, 96, 95), (323, 257, 321), (257, 323, 194, 259), (78, 145, 146, 147), (69, 73, 72), (88, 36, 37, 38), (40, 311, 238, 92), (314, 361, 331, 118), (166, 245, 317), (173, 218, 175, 332), (194, 196, 259), (312, 87, 156), (336, 275, 8), (268, 173, 332, 359), (367, 28, 380, 308), (4, 6, 225), (157, 36, 325), (325, 39, 157), (116, 86, 35, 115), (292, 340, 321), (143, 160, 144), (327, 169, 317), (327, 170, 169), (189, 254, 203, 149), (137, 260, 41, 182), (24, 29, 26), (130, 371, 129, 34), (76, 108, 243), (76, 243, 104), (279, 191, 208), (223, 111, 233), (343, 251, 344), (138, 264, 33), (153, 81, 80), (320, 206, 106, 11), (12, 362, 241, 17), (174, 226, 161, 227), (235, 232, 234, 236), (77, 102, 2, 1), (342, 238, 311, 310), (266, 244, 337), (220, 270, 286, 285, 347), (346, 347, 285), (231, 150, 62, 98, 99), (162, 216, 217, 248), (114, 236, 112), (220, 306, 221), (216, 352, 270, 220), (91, 142, 318), (28, 255, 15), (363, 283, 124, 348), (215, 350, 349), (247, 330, 167), (12, 14, 211), (349, 350, 222, 132), (336, 119, 275), (344, 251, 257, 351), (324, 47, 45), (335, 87, 88, 86), (104, 118, 105), (354, 350, 91), (318, 222, 350, 354), (183, 295, 3, 296), (324, 353, 53, 47), (303, 217, 304), (34, 26, 29), (290, 253, 195, 298), (201, 202, 334, 178), (316, 30, 315), (239, 60, 240, 44), (27, 26, 70, 71), (85, 171, 82, 293), (273, 252, 251, 343), (13, 73, 69), (337, 267, 338, 266), (355, 89, 90), (296, 357, 7), (351, 203, 254, 205), (260, 90, 42), (244, 265, 245, 246), (277, 345, 185), (205, 84, 83, 204), (249, 227, 94, 164), (326, 290, 292), (325, 36, 312), (155, 325, 312), (307, 333, 162, 160), (350, 215, 91), (74, 278, 75), (135, 170, 327, 133), (14, 21, 381, 16), (5, 224, 223, 183), (74, 103, 331), (239, 44, 49), (181, 125, 85, 293), (355, 198, 356, 144), (330, 247, 202, 201), (188, 187, 108), (262, 264, 242), (332, 303, 359), (339, 179, 135), (287, 125, 191, 280), (97, 96, 307), (232, 299, 145, 1), (78, 179, 79, 77), (98, 43, 42, 164, 94), (117, 118, 104), (104, 209, 123), (320, 11, 9, 10), (154, 156, 87, 335), (145, 299, 151, 146), (301, 345, 360), (146, 151, 360), (213, 5, 212), (213, 15, 255, 6), (231, 342, 84, 150), (233, 328, 234, 232), (207, 192, 107), (62, 189, 190, 63), (116, 289, 86), (361, 200, 329), (313, 200, 361), (58, 59, 60, 61), (193, 37, 210), (61, 239, 58), (144, 356, 141, 143), (329, 74, 331, 361), (241, 362, 363, 348), (177, 278, 74, 329), (285, 286, 346), (269, 306, 346), (235, 237, 299, 232), (300, 186, 345, 301), (25, 13, 17), (22, 17, 23), (269, 346, 286), (270, 269, 286), (229, 314, 297), (120, 184, 274), (291, 340, 292), (184, 212, 5, 183), (253, 271, 195), (49, 80, 82, 50), (104, 123, 364), (122, 364, 123), (358, 320, 10), (127, 126, 65, 64), (232, 0, 341), (122, 117, 364), (104, 364, 117), (115, 358, 140, 116), (84, 342, 85, 83), (369, 65, 126, 31), (173, 352, 333, 96), (6, 67, 225), (345, 186, 188), (188, 185, 345), (199, 71, 70, 197), (366, 153, 365), (279, 43, 98), (283, 117, 122), (59, 53, 60), (313, 165, 200), (210, 104, 243), (210, 243, 193), (266, 134, 265, 244), (255, 28, 29, 30), (257, 258, 326), (237, 302, 301), (25, 27, 73, 13), (347, 346, 306), (306, 220, 347), (251, 253, 290), (49, 44, 80), (99, 238, 342, 231), (176, 147, 278), (130, 34, 367), (267, 337, 100), (221, 304, 217), (306, 304, 221), (59, 58, 55), (352, 173, 268, 270), (233, 232, 341, 223), (202, 168, 169, 170), (97, 143, 93), (93, 92, 97), (89, 250, 163), (89, 163, 90), (227, 161, 228), (357, 296, 3), (7, 357, 297), (197, 356, 198, 199), (169, 368, 247), (230, 357, 3), (230, 3, 2), (256, 121, 214), (123, 121, 256), (79, 338, 267), (343, 344, 204, 148), (89, 355, 144), (207, 35, 38, 192), (367, 34, 29, 28), (46, 54, 50), (105, 118, 331, 103), (124, 215, 349), (200, 167, 330, 329), (39, 40, 276), (209, 276, 121), (7, 297, 118), (91, 318, 354), (363, 119, 336), (77, 1, 145, 78), (100, 337, 244, 246), (127, 180, 294, 32), (19, 18, 24), (248, 217, 175), (224, 4, 225), (67, 72, 219, 225), (101, 2, 102), (295, 183, 223, 341), (288, 110, 109), (164, 163, 250, 249), (151, 301, 360), (168, 368, 169), (12, 211, 362), (329, 330, 201), (369, 31, 263), (31, 33, 263), (46, 50, 171), (171, 50, 82), (262, 263, 264), (322, 194, 323), (73, 27, 71), (114, 152, 302), (291, 322, 340), (39, 311, 40), (107, 192, 108, 187), (4, 224, 5), (174, 227, 249, 248), (153, 366, 81), (81, 366, 32), (159, 152, 114), (168, 247, 368), (138, 139, 264), (148, 287, 190, 189, 149), (11, 106, 186, 300), (0, 232, 1, 2), (372, 142, 141, 319), (142, 372, 222, 318), (32, 366, 33), (25, 17, 22), (353, 60, 53), (360, 345, 277), (147, 146, 360, 277), (283, 363, 336), (336, 8, 283), (185, 147, 277), (20, 13, 18), (13, 20, 14), (369, 261, 65), (61, 60, 239), (264, 9, 158), (9, 139, 10), (113, 242, 158), (242, 264, 158), (176, 78, 147), (212, 184, 211), (179, 334, 135), (100, 246, 136), (334, 170, 135), (57, 58, 239), (49, 57, 239), (157, 39, 209), (39, 276, 209), (202, 170, 334), (56, 55, 58, 57), (250, 160, 162, 248), (11, 300, 152, 9), (179, 78, 176), (176, 178, 179), (216, 162, 333, 352), (96, 333, 307), (201, 178, 177), (201, 177, 329), (283, 122, 124), (299, 237, 301, 151), (138, 33, 366), (179, 178, 334), (339, 134, 266, 338), (139, 9, 264), (294, 82, 32), (168, 202, 247), (165, 101, 370), (101, 136, 370), (370, 136, 165), (165, 136, 246), (205, 204, 344, 351), (287, 148, 204, 83), (45, 140, 153, 80, 44), (140, 358, 365, 153), (349, 132, 348, 124), (128, 222, 372, 371), (371, 372, 319, 129), (319, 141, 356, 197), (24, 18, 315, 29), (272, 203, 259, 196), (252, 273, 253, 251), (351, 257, 259, 203), (72, 373, 109, 219), (73, 374, 373, 72), (373, 374, 376, 375), (109, 373, 375, 113), (374, 281, 66, 376), (113, 375, 242), (375, 376, 65, 261, 242), (182, 378, 377, 137), (137, 377, 379, 284), (284, 379, 199, 198), (199, 379, 281, 71), (377, 378, 64, 66), (379, 377, 66, 281), (378, 180, 127, 64), (376, 66, 64, 65), (38, 35, 86, 88), (348, 132, 131, 241), (69, 72, 67, 68), (272, 273, 149, 203), (324, 45, 44, 240), (16, 381, 15, 213), (23, 380, 381, 21), (308, 380, 23, 309), (381, 380, 28, 15), (16, 212, 211, 14), (119, 363, 362, 120)]
    
    scale_factor = target_height / 2.0
    
    scaled_verts = [(v[0] * scale_factor, v[1] * scale_factor, v[2] * scale_factor) for v in verts]
    
    return scaled_verts, faces

def add_human_booth(gender_type, human_height, floor_width, floor_length, floor_height, rotation_intensity, index):
    """Generates an individual human object following the exact table design pattern."""
    verts, faces = create_human_mesh(gender_type, human_height)
    mesh_data = bpy.data.meshes.new(f"Human_Mesh_{index}")
    mesh_data.from_pydata(verts, [], faces)
    mesh_data.update()
    
    obj = bpy.data.objects.new(f"Booth_Human_{index}", mesh_data)
    col = get_or_create_collection("Booth_Humans")
    col.objects.link(obj)

    props = bpy.context.scene.generative_booth_props
    
    obj.individual_human_gender = gender_type
    obj.individual_human_height = human_height
    obj.individual_human_color = props.human_color
    
    bpy.context.view_layer.update()

    margin = 0.2
    x_max = (floor_width / 2.0) - (obj.dimensions.x / 2.0) - margin
    y_max = (floor_length / 2.0) - (obj.dimensions.y / 2.0) - margin
    
    x_max = max(0.0, x_max)
    y_max = max(0.0, y_max)
    
    obj.location.z = floor_height
    
    random.seed(props.human_seed + index)
    for _ in range(100):
        new_x = random.uniform(-x_max, x_max)
        new_y = random.uniform(-y_max, y_max)
        if not is_overlapping(new_x, new_y, obj, bpy.context, safety_margin=0.15):
            obj.location.x = new_x
            obj.location.y = new_y
            break
    else:
        obj.location.x = random.uniform(-x_max, x_max)
        obj.location.y = random.uniform(-y_max, y_max)
        
    obj.rotation_euler.z = math.radians(props.human_rotation)
    
    mat_name = f"Mat_{obj.name}_Unique"
    mat = add_material(mat_name, props.human_color)
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
        
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def update_human_count(self, context):
    """Manages absolute instance counts dynamically using strict python hardcoding."""
    props = context.scene.generative_booth_props
    if getattr(props, "programmatic_update", False):
        return

    col = get_or_create_collection("Booth_Humans")
    current_humans = list(col.objects)
    count_needed = props.human_count

    while len(current_humans) > count_needed:
        obj_to_remove = current_humans[-1]
        
        if context.active_object == obj_to_remove:
            remaining = [o for o in current_humans if o != obj_to_remove]
            context.view_layer.objects.active = remaining[-1] if remaining else None
            
        current_humans.remove(obj_to_remove)
        bpy.data.objects.remove(obj_to_remove, do_unlink=True)

    while len(current_humans) < count_needed:
        new_index = len(col.objects)
        
        new_obj = add_human_booth(
            props.human_gender, 
            props.human_height,
            props.floor_width, 
            props.floor_length, 
            props.floor_height,
            props.human_rotation,
            new_index
        )
        current_humans.append(new_obj)

def update_human_style(self, context):
    """Global styling fallback."""
    props = context.scene.generative_booth_props
    col = get_or_create_collection("Booth_Humans")
    
    verts, faces = create_human_mesh(props.human_gender, props.human_height)
    mat = add_material("Booth_Human_Mat", props.human_color)
    
    for obj in col.objects:
        obj.data.clear_geometry()
        obj.data.from_pydata(verts, [], faces)
        obj.data.update()
        obj.location.z = props.floor_height
        if not obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat


def update_individual_human_style(self, context):
    """Updates only the selected human instance when tweaked directly."""
    if not self or self.type != 'MESH':
        return
        
    props = context.scene.generative_booth_props
        
    verts, faces = create_human_mesh(self.individual_human_gender, self.individual_human_height)
    self.data.clear_geometry()
    self.data.from_pydata(verts, [], faces)
    self.data.update()
    
    current_gender = self.individual_human_gender
    matching_count = sum(
        1 for o in context.scene.objects 
        if o.name.startswith("Booth_Human_") 
        and getattr(o, "individual_human_gender", "") == current_gender
    )
    
    props.programmatic_update = True
    props.human_count = matching_count
    props.programmatic_update = False
    
    mat_name = f"Mat_{self.name}_Unique"
    color_tuple = (
        self.individual_human_color[0],
        self.individual_human_color[1],
        self.individual_human_color[2],
        self.individual_human_color[3]
    )
    
    mat = add_material(mat_name, color_tuple)
    if not self.data.materials:
        self.data.materials.append(mat)
    else:
        self.data.materials[0] = mat


def sync_ui_on_human_selection_change(scene):
    """Updates properties panel dynamically based on viewport item click."""
    context = bpy.context
    active_obj = context.active_object
    if active_obj and active_obj.name.startswith("Booth_Human_"):
        props = context.scene.generative_booth_props
        current_gender = getattr(active_obj, "individual_human_gender", "")
        
        matching_count = sum(
            1 for o in context.scene.objects 
            if o.name.startswith("Booth_Human_") 
            and getattr(o, "individual_human_gender", "") == current_gender
        )
        
        if props.human_count != matching_count:
            props.programmatic_update = True
            props.human_count = matching_count
            props.programmatic_update = False


def update_human_rotation_clean(self, context):
    """Applies indexed random rotation variance based on intensity, matching the ceiling logic."""
    props = context.scene.generative_booth_props
    col = bpy.data.collections.get("Booth_Humans")
    if not col:
        return
        
    rotation_intensity = props.human_rotation * 5.0
    
    for i, obj in enumerate(col.objects):
        random.seed(i + 1200) 
        rand_angle = random.uniform(-rotation_intensity, rotation_intensity)
        obj.rotation_euler.z = math.radians(rand_angle)
    
def remove_existing_object(obj_name):
    if obj_name in bpy.data.objects:
        obj = bpy.data.objects[obj_name]
        bpy.data.objects.remove(obj, do_unlink=True)

# ______________CAMERA______________

def add_keyframed_camera():
    loc_c = (0, 12.3529, 1.50987)
    rot_c = (math.radians(90), math.radians(0), math.radians(180)) 

    loc_d = (-12.3529, 0, 1.50987)
    rot_d = (math.radians(90), math.radians(0), math.radians(270)) 
    
    loc_a = (0, -12.3529, 1.50987)
    rot_a = (math.radians(90), math.radians(0), math.radians(360))
    
    loc_b = (12.3529, 0, 1.50987)
    rot_b = (math.radians(90), math.radians(0), math.radians(90)) 

    loc_g = (8.73485, 8.73485, 1.50987)
    rot_g = (math.radians(90), math.radians(0), math.radians(135)) 

    loc_h = (-8.73485, 8.73485, 1.50987)
    rot_h = (math.radians(90), math.radians(0), math.radians(225)) 
    
    loc_e = (-8.73485, -8.73485, 1.50987)
    rot_e = (math.radians(90), math.radians(0), math.radians(315))
    
    loc_f = (8.73485, -8.73485, 1.50987)
    rot_f = (math.radians(90), math.radians(0), math.radians(405)) 

    loc_k = (8.73485, 8.73485, 6.00185)
    rot_k = (math.radians(67.5), math.radians(0), math.radians(135)) 

    loc_l = (-8.73485, 8.73485, 6.00185)
    rot_l = (math.radians(67.5), math.radians(0), math.radians(225)) 
    
    loc_i = (-8.73485, -8.73485, 6.00185)
    rot_i = (math.radians(67.5), math.radians(0), math.radians(315))
    
    loc_j = (8.73485, -8.73485, 6.00185)
    rot_j = (math.radians(67.5), math.radians(0), math.radians(405)) 
    
    loc_m = (0, 0, 20)
    rot_m = (math.radians(0), math.radians(0), math.radians(0)) 
    
    old_cam = bpy.data.objects.get("Keyframed_Booth_Camera")
    if old_cam:
        bpy.data.objects.remove(old_cam, do_unlink=True)

    bpy.ops.object.camera_add(
        enter_editmode=False,
        align='WORLD',
        location=loc_a,
        rotation=rot_a
    )
    cam_obj = bpy.context.active_object
    cam_obj.name = "Keyframed_Booth_Camera"
    
    for col in bpy.data.collections:
        if cam_obj.name in col.objects:
            col.objects.unlink(cam_obj)
            
    if cam_obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(cam_obj)
    
    bpy.context.scene.camera = cam_obj
    bpy.context.scene.frame_end = 13

    bpy.context.scene.frame_set(1)
    cam_obj.location = loc_a
    cam_obj.rotation_euler = rot_a
    cam_obj.keyframe_insert(data_path="location", frame=1)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=1)
    
    bpy.context.scene.frame_set(2)
    cam_obj.location = loc_b
    cam_obj.rotation_euler = rot_b
    cam_obj.keyframe_insert(data_path="location", frame=2)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=2)
    
    bpy.context.scene.frame_set(3)
    cam_obj.location = loc_c
    cam_obj.rotation_euler = rot_c
    cam_obj.keyframe_insert(data_path="location", frame=3)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=3)
    
    bpy.context.scene.frame_set(4)
    cam_obj.location = loc_d
    cam_obj.rotation_euler = rot_d
    cam_obj.keyframe_insert(data_path="location", frame=4)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=4)

    bpy.context.scene.frame_set(5)
    cam_obj.location = loc_e
    cam_obj.rotation_euler = rot_e
    cam_obj.keyframe_insert(data_path="location", frame=5)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=5)
    
    bpy.context.scene.frame_set(6)
    cam_obj.location = loc_f
    cam_obj.rotation_euler = rot_f
    cam_obj.keyframe_insert(data_path="location", frame=6)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=6)
    
    bpy.context.scene.frame_set(7)
    cam_obj.location = loc_g
    cam_obj.rotation_euler = rot_g
    cam_obj.keyframe_insert(data_path="location", frame=7)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=7)
    
    bpy.context.scene.frame_set(8)
    cam_obj.location = loc_h
    cam_obj.rotation_euler = rot_h
    cam_obj.keyframe_insert(data_path="location", frame=8)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=8)    
    
    bpy.context.scene.frame_set(9)
    cam_obj.location = loc_i
    cam_obj.rotation_euler = rot_i
    cam_obj.keyframe_insert(data_path="location", frame=9)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=9)
    
    bpy.context.scene.frame_set(10)
    cam_obj.location = loc_j
    cam_obj.rotation_euler = rot_j
    cam_obj.keyframe_insert(data_path="location", frame=10)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=10)
    
    bpy.context.scene.frame_set(11)
    cam_obj.location = loc_k
    cam_obj.rotation_euler = rot_k
    cam_obj.keyframe_insert(data_path="location", frame=11)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=11)
    
    bpy.context.scene.frame_set(12)
    cam_obj.location = loc_l
    cam_obj.rotation_euler = rot_l
    cam_obj.keyframe_insert(data_path="location", frame=12)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=12)    
    
    bpy.context.scene.frame_set(13)
    cam_obj.location = loc_m
    cam_obj.rotation_euler = rot_m
    cam_obj.keyframe_insert(data_path="location", frame=13)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=13)    
        
    bpy.context.scene.frame_set(1)
    
    return cam_obj

def hide_ceiling_on_frame_13(scene):
    should_hide = (scene.frame_current == 13)
    
    roof = bpy.data.objects.get("Booth_Roof")
    if roof:
        roof.hide_viewport = should_hide
        roof.hide_render = should_hide

    col_name = "Booth_CeilingElements"
    
    if col_name in bpy.data.collections:
        bpy.data.collections[col_name].hide_render = should_hide
        
    if col_name in bpy.context.view_layer.layer_collection.children:
        bpy.context.view_layer.layer_collection.children[col_name].hide_viewport = should_hide
bpy.app.handlers.frame_change_pre.clear()

bpy.app.handlers.frame_change_pre.append(hide_ceiling_on_frame_13)

def update_booth_heights(self, context):
    dynamic_height = self.booth_master_height - self.floor_height - self.roof_height
    wall_z_pos = self.floor_height + (dynamic_height / 2.0)
    booth_exists = bpy.data.objects.get("Booth_Wall_Back") is not None

    floor_obj = bpy.data.objects.get("Booth_Floor")
    if floor_obj:
        floor_obj.scale.z = self.floor_height
        floor_obj.location.z = self.floor_height / 2.0
        if self.floor_height <= 0.001:
            bpy.data.objects.remove(floor_obj, do_unlink=True)
            
    elif booth_exists and self.floor_height > 0.001:
        add_floor_booth(self.floor_width, self.floor_length, self.floor_height, self.floor_color)

    roof_obj = bpy.data.objects.get("Booth_Roof")
    ceil_coll = bpy.data.collections.get("Booth_CeilingElements")

    if roof_obj:
        roof_obj.scale.z = self.roof_height
        roof_obj.location.z = self.booth_master_height - (self.roof_height / 2.0)
        
        if self.roof_height <= 0.001:
            if ceil_coll:
                ceil_coll.hide_viewport = True
                ceil_coll.hide_render = True
            
            bpy.data.objects.remove(roof_obj, do_unlink=True)
        else:
            if ceil_coll:
                ceil_coll.hide_viewport = False
                ceil_coll.hide_render = False
            
    elif booth_exists and self.roof_height > 0.001:
        if ceil_coll:
            ceil_coll.hide_viewport = False
            ceil_coll.hide_render = False
            
        add_roof_booth(self.floor_width, self.floor_length, self.roof_height, self.booth_master_height, self.roof_color)

    table_col = bpy.data.collections.get("Booth_Tables")
    if table_col:
        for obj in table_col.objects:
            obj.location.z = self.floor_height

    chair_col = bpy.data.collections.get("Booth_Chairs")
    if chair_col:
        for obj in chair_col.objects:
            obj.location.z = self.floor_height
            
    floorelement_col = bpy.data.collections.get("Booth_floorelement")
    if floorelement_col:
        for obj in floorelement_col.objects:
            obj.location.z = self.floor_height
            
    ceiling_z = self.booth_master_height - self.roof_height
    ceilingelement_col = bpy.data.collections.get("Booth_CeilingElements")
    if ceilingelement_col:
        for obj in ceilingelement_col.objects:
            obj.location.z = ceiling_z
    
    props = self
    dynamic_gap = props.booth_master_height - props.floor_height - props.roof_height
    pole_col = bpy.data.collections.get("Booth_Poles")
    if pole_col:
        for obj in pole_col.objects:
            obj.scale.z = dynamic_gap
            obj.location.z = props.floor_height + (dynamic_gap / 2.0)
    
    dynamic_height = self.booth_master_height - self.floor_height - self.roof_height 
    wall_z_pos = self.floor_height + (dynamic_height / 2.0) 
            
    wall_col = bpy.data.collections.get("Booth_Walls")
    if wall_col:
        for obj in wall_col.objects:
            obj.scale.z = dynamic_height
            obj.location.z = wall_z_pos

    self.back_wall_height = dynamic_height
    self.left_wall_height = dynamic_height
    self.right_wall_height = dynamic_height

    self.update_back_wall_dimensions(context)
    self.update_left_wall_dimensions(context)
    self.update_right_wall_dimensions(context)

    

# ----------------------------------CLASSES-----------------------------------

class MESH_OT_generate_full_booth(bpy.types.Operator):
    bl_idname = "mesh.generate_full_booth"
    bl_label = "Generate Full Booth"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        clear_previous_booth_elements()
        props = context.scene.generative_booth_props
        
        add_floor_booth(props.floor_width, props.floor_length, props.floor_height, props.floor_color)
        
        props.roof_width = props.floor_width
        props.roof_length = props.floor_length
        
        add_roof_booth(props.roof_width, props.roof_length, props.roof_height, props.booth_master_height, props.roof_color)
        
        props.back_wall_length = props.floor_width
        props.left_wall_length = props.floor_length
        props.right_wall_length = props.floor_length
        add_all_walls(props)
        
        for i in range(props.table_count):
            table_obj = add_table_booth(props.table_type, props.floor_width, props.floor_length, props.floor_height, props.table_rotation_random, i)

            mat = add_material(f"table_mat", props.table_color)
            if table_obj.data.materials:
                table_obj.data.materials[0] = mat
            else:
                table_obj.data.materials.append(mat)
        bpy.ops.object.modify_table_booth_position()
        
        for i in range(props.chair_count):
            chair_obj = add_chair_booth(props.chair_type, props.floor_width, props.floor_length, props.floor_height, props.chair_rotation_random, i)

            mat = add_material(f"chair_mat", props.chair_color)
            if chair_obj.data.materials:
                chair_obj.data.materials[0] = mat
            else:
                chair_obj.data.materials.append(mat)
        bpy.ops.object.modify_chair_booth_position()
        
        for i in range(props.floorelement_count):
            floorelement_obj = add_floorelement_booth(props.floorelement_type, props.floor_width, props.floor_length, props.floor_height, props.floorelement_rotation_random, i)

            mat = add_material(f"floorelement_mat", props.floorelement_color)
            if floorelement_obj.data.materials:
                floorelement_obj.data.materials[0] = mat
            else:
                floorelement_obj.data.materials.append(mat)
        bpy.ops.object.modify_floorelement_booth_position()
        
        
        ceiling_z = props.booth_master_height - props.roof_height

        for i in range(props.ceilingelement_count):
            ceilingelement_obj = add_ceilingelement_booth(props.ceilingelement_type, props.floor_width, props.floor_length, ceiling_z, props.ceilingelement_rotation_random, i)
            
            mat = add_material("ceilingelement_mat", props.ceilingelement_color)
            if ceilingelement_obj.data.materials:
                ceilingelement_obj.data.materials[0] = mat
            else:
                ceilingelement_obj.data.materials.append(mat)
        bpy.ops.object.modify_ceilingelement_booth_position()
        
        for i in range(props.pole_count):
            pole_obj = add_pole_booth(props.floor_width, props.floor_length, props.floor_height, props.booth_master_height, props.roof_height, i)
            mat = add_material("Booth_Pole_Mat", props.pole_color)
            if pole_obj.data.materials:
                pole_obj.data.materials[0] = mat
            else:
                pole_obj.data.materials.append(mat)
        
        self.report({'INFO'}, "Full Booth Generated!")
        return {"FINISHED"}

# ______________BOOTH BASE______________

#________FLOOR__________

class MESH_OT_add_floor(bpy.types.Operator):
    bl_idname = "mesh.add_floor_booth"
    bl_label = "Add Floor for the Booth"
    bl_options = {"UNDO"}

    def execute(self, context):
        props = context.scene.generative_booth_props
        
        add_floor_booth(props.floor_width, props.floor_length, props.floor_height)
        add_material("floor_mat", props.floor_color)
        return {"FINISHED"}

#________ROOF__________
class MESH_OT_add_roof(bpy.types.Operator):
    bl_idname = "mesh.add_roof_booth"
    bl_label = "Add Roof for the Booth"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.generative_booth_props
        
        add_roof_booth(props.roof_width, props.roof_length, props.roof_height)
        add_material("roof_mat", props.roof_color)
        return {"FINISHED"}

#________WALLS__________
class MESH_OT_add_all_walls(bpy.types.Operator):
    bl_idname = "mesh.add_all_walls"
    bl_label = "Add ALL Walls"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.generative_booth_props
        add_all_walls(props) 
        return {"FINISHED"}

# ______________BOOTH ELEMENTS______________

#________TABLE__________

class OBJECT_OT_modify_table_booth_position(bpy.types.Operator):
    bl_idname = "object.modify_table_booth_position"
    bl_label = "Generate Random Table Positions"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        props = context.scene.generative_booth_props
        col = get_or_create_collection("Booth_Tables")
        
        wall_padding = 0.1 

        for obj in col.objects:
            obj.location.z = props.floor_height
            
            x_max = (props.floor_width / 2.0) - (obj.dimensions.x / 2.0) - wall_padding
            y_max = (props.floor_length / 2.0) - (obj.dimensions.y / 2.0) - wall_padding
            
            x_max = max(0.0, x_max)
            y_max = max(0.0, y_max)
            
            orig_x = obj.location.x
            orig_y = obj.location.y
            
            obj.location.x = -9999.0
            obj.location.y = -9999.0
            
            success = False
            for _ in range(150):
                new_x = random.uniform(-x_max, x_max)
                new_y = random.uniform(-y_max, y_max)
                
                if not is_overlapping(new_x, new_y, obj, context, safety_margin=0.2):
                    obj.location.x = new_x
                    obj.location.y = new_y
                    success = True
                    break
            
            if not success:
                obj.location.x = orig_x
                obj.location.y = orig_y
                self.report({'INFO'}, f"Could not fit '{obj.name}'. Kept original position.")
                
        return {'FINISHED'}

#________CHAIR__________
    
class OBJECT_OT_modify_chair_booth_position(bpy.types.Operator):
    bl_idname = "object.modify_chair_booth_position"
    bl_label = "Generate Random Chair Positions"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        props = context.scene.generative_booth_props
        col = get_or_create_collection("Booth_Chairs")
        
        wall_padding = 0.05 

        for obj in col.objects:
            obj.location.z = props.floor_height
            
            x_max = (props.floor_width / 2.0) - (obj.dimensions.x / 2.0) - wall_padding
            y_max = (props.floor_length / 2.0) - (obj.dimensions.y / 2.0) - wall_padding
            
            x_max = max(0.0, x_max)
            y_max = max(0.0, y_max)
            
            orig_x = obj.location.x
            orig_y = obj.location.y
            
            obj.location.x = -9999.0
            obj.location.y = -9999.0
            
            success = False
            for _ in range(150):
                new_x = random.uniform(-x_max, x_max)
                new_y = random.uniform(-y_max, y_max)
                
                if not is_overlapping(new_x, new_y, obj, context, safety_margin=0.15):
                    obj.location.x = new_x
                    obj.location.y = new_y
                    success = True
                    break
            
            if not success:
                obj.location.x = orig_x
                obj.location.y = orig_y
                self.report({'INFO'}, f"Could not fit '{obj.name}'. Kept original position.")
                
        return {'FINISHED'}
#________floorelement__________

class OBJECT_OT_modify_floorelement_booth_position(bpy.types.Operator):
    bl_idname = "object.modify_floorelement_booth_position"
    bl_label = "Generate Random Floor Element Positions"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        props = context.scene.generative_booth_props
        col = get_or_create_collection("Booth_floorelement")

        wall_padding = 0.1

        for obj in col.objects:
            obj.location.z = props.floor_height
            
            x_max = (props.floor_width / 2.0) - (obj.dimensions.x / 2.0) - wall_padding
            y_max = (props.floor_length / 2.0) - (obj.dimensions.y / 2.0) - wall_padding
            
            x_max = max(0.0, x_max)
            y_max = max(0.0, y_max)
            
            orig_x = obj.location.x
            orig_y = obj.location.y
            
            obj.location.x = -9999.0
            obj.location.y = -9999.0
            
            success = False
            for _ in range(150):
                new_x = random.uniform(-x_max, x_max)
                new_y = random.uniform(-y_max, y_max)
                
                if not is_overlapping(new_x, new_y, obj, context, safety_margin=0.2):
                    obj.location.x = new_x
                    obj.location.y = new_y
                    success = True
                    break
            
            if not success:
                obj.location.x = orig_x
                obj.location.y = orig_y
                self.report({'INFO'}, f"Could not fit '{obj.name}'. Kept original position.")
                
        return {'FINISHED'}
    
class OBJECT_OT_modify_ceilingelement_booth_position(bpy.types.Operator):
    bl_idname = "object.modify_ceilingelement_booth_position"
    bl_label = "Generate Random Ceiling Element Positions"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        props = context.scene.generative_booth_props
        col = get_or_create_collection("Booth_CeilingElements")
        ceiling_z = props.booth_master_height - props.roof_height

        wall_padding = 0.1

        for obj in col.objects:
            obj.location.z = ceiling_z
            
            x_max = (props.floor_width / 2.0) - (obj.dimensions.x / 2.0) - wall_padding
            y_max = (props.floor_length / 2.0) - (obj.dimensions.y / 2.0) - wall_padding
            
            x_max = max(0.0, x_max)
            y_max = max(0.0, y_max)
            
            orig_x = obj.location.x
            orig_y = obj.location.y
            
            obj.location.x = -9999.0
            obj.location.y = -9999.0
            
            success = False
            for _ in range(150):
                new_x = random.uniform(-x_max, x_max)
                new_y = random.uniform(-y_max, y_max)
                
                if not is_overlapping(new_x, new_y, obj, context, safety_margin=0.2):
                    obj.location.x = new_x
                    obj.location.y = new_y
                    success = True
                    break
            
            if not success:
                obj.location.x = orig_x
                obj.location.y = orig_y
                self.report({'INFO'}, f"Could not fit '{obj.name}'. Kept original position.")
                
        return {'FINISHED'}

class OBJECT_OT_modify_pole_booth_position(bpy.types.Operator):
    bl_idname = "object.modify_pole_booth_position"
    bl_label = "Generate Random Poles Positions"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        props = context.scene.generative_booth_props
        col = get_or_create_collection("Booth_Poles")
        
        dynamic_gap = props.booth_master_height - props.floor_height - props.roof_height
        
        wall_padding = 0.05 
        
        for obj in col.objects:
            obj.location.z = props.floor_height + (dynamic_gap / 2.0)
            
            x_max = (props.floor_width / 2.0) - (obj.dimensions.x / 2.0) - wall_padding
            y_max = (props.floor_length / 2.0) - (obj.dimensions.y / 2.0) - wall_padding
            
            x_max = max(0.0, x_max)
            y_max = max(0.0, y_max)
            
            orig_x = obj.location.x
            orig_y = obj.location.y
            
            obj.location.x = -9999.0
            obj.location.y = -9999.0
            
            success = False
            for _ in range(150):
                new_x = random.uniform(-x_max, x_max)
                new_y = random.uniform(-y_max, y_max)
                
                if not is_overlapping(new_x, new_y, obj, context, safety_margin=0.1):
                    obj.location.x = new_x
                    obj.location.y = new_y
                    success = True
                    break
            
            if not success:
                obj.location.x = orig_x
                obj.location.y = orig_y
                self.report({'INFO'}, f"Could not fit '{obj.name}'. Kept original position.")
                
        return {'FINISHED'}


# _____________LIGHTS AND CAMERA______________

#________LIGHTS__________

class OBJECT_OT_add_all_lights(bpy.types.Operator):
    bl_idname = "object.add_all_lights"
    bl_label = "Add ALL Lights"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        add_all_lights()
        props = context.scene.generative_booth_props
        props.light_top_visible = True
        props.light_back_visible = True
        props.light_front_visible = True
        props.light_left_visible = True
        props.light_right_visible = True
        return {"FINISHED"}

#________CAMERA__________
    
class OBJECT_OT_add_keyframed_camera(bpy.types.Operator):
    bl_idname = "object.add_keyframed_camera"
    bl_label = "Add Keyframed Camera"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        add_keyframed_camera()
        self.report({'INFO'}, "Keyframed Camera Added!")
        return {"FINISHED"}


# ------------------------------------PROPERTIES GROUP-----------------------------------

class OBJECT_OT_add_human_booth(bpy.types.Operator):
    bl_idname = "object.add_human_booth"
    bl_label = "Add Human"
    bl_options = {"UNDO"}

    def execute(self, context):
        props = context.scene.generative_booth_props
        if props.human_count < 10:
            props.human_count += 1
            self.report({'INFO'}, f"Added human. Total count: {props.human_count}")
        else:
            self.report({'WARNING'}, "Maximum human count reached!")
        return {'FINISHED'}


class OBJECT_OT_modify_human_booth_position(bpy.types.Operator):
    """Zero-lag positioning system that leaves rotations untouched, matching your element assets."""
    bl_idname = "object.modify_human_booth_position"
    bl_label = "Generate Random Human Positions"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        props = context.scene.generative_booth_props
        col = bpy.data.collections.get("Booth_Humans")
        
        if not col or not col.objects:
            return {'FINISHED'}
            
        wall_padding = 0.2
        random.seed(random.randint(0, 10000))

        for obj in col.objects:
            obj.location.z = props.floor_height
            
            x_max = (props.floor_width / 2.0) - (obj.dimensions.x / 2.0) - wall_padding
            y_max = (props.floor_length / 2.0) - (obj.dimensions.y / 2.0) - wall_padding
            
            x_max = max(0.0, x_max)
            y_max = max(0.0, y_max)
            
            orig_x = obj.location.x
            orig_y = obj.location.y
            
            obj.location.x = -9999.0
            obj.location.y = -9999.0
            
            success = False
            for _ in range(150):
                new_x = random.uniform(-x_max, x_max)
                new_y = random.uniform(-y_max, y_max)
                
                if not is_overlapping(new_x, new_y, obj, context, safety_margin=0.15):
                    obj.location.x = new_x
                    obj.location.y = new_y
                    success = True
                    break
            
            if not success:
                obj.location.x = orig_x
                obj.location.y = orig_y
                self.report({'INFO'}, f"Could not fit '{obj.name}'. Kept original position.")
                
        context.view_layer.update()
        return {'FINISHED'}
    
class GenerativeBoothProperties(bpy.types.PropertyGroup):
    
    programmatic_update: bpy.props.BoolProperty(default=False)
    
    def update_master_height(self, context):
        self.update_roof_dimensions(context)

        wall_height = self.booth_master_height - self.floor_height - self.roof_height
        self.back_wall_height = wall_height
        self.left_wall_height = wall_height
        self.right_wall_height = wall_height
        
        self.update_back_wall_dimensions(context)
        self.update_left_wall_dimensions(context)
        self.update_right_wall_dimensions(context)
        self.update_table_dimensions(context)

    booth_master_height: bpy.props.FloatProperty(
        name="Total Height",
        default=2.8,
        min=2.0,
        max=3.0,
        description="Total height from the bottom of the floor to the top of the roof",
        update=update_booth_heights
    )
    
    #____________FLOOR_______________
    def update_floor_dimensions(self, context):
        obj = bpy.data.objects.get("Booth_Floor")
        if obj and obj.type == 'MESH':
            obj.scale.x = self.floor_width
            obj.scale.y = self.floor_length
            obj.scale.z = self.floor_height
            obj.location.z = self.floor_height / 2.0
            
        new_wall_height = self.booth_master_height - self.floor_height - self.roof_height    
        
        self.back_wall_height = new_wall_height
        self.left_wall_height = new_wall_height
        self.right_wall_height = new_wall_height
        self.roof_width = self.floor_width
        self.roof_length = self.floor_length
        
        self.update_back_wall_dimensions(context)
        self.update_left_wall_dimensions(context)
        self.update_right_wall_dimensions(context)
        self.update_roof_dimensions(context)
        self.update_table_dimensions(context)
                                
    #____________ROOF______________
    def update_roof_dimensions(self, context):
        obj = bpy.data.objects.get("Booth_Roof")
        if obj and obj.type == 'MESH':
            obj.scale.x = self.roof_width
            obj.scale.y = self.roof_length
            obj.scale.z = self.roof_height

            obj.location.z = self.booth_master_height - (self.roof_height / 2.0)
            
            new_wall_height = self.booth_master_height - self.floor_height - self.roof_height
        self.back_wall_height = new_wall_height
        self.left_wall_height = new_wall_height
        self.right_wall_height = new_wall_height

        self.update_back_wall_dimensions(context)
        self.update_left_wall_dimensions(context)
        self.update_right_wall_dimensions(context)

    #___________WALL_______________
    def update_back_wall_visibility(self, context):
        toggle_wall_visibility("Booth_Wall_Back", self.back_wall_visible)
        
    def update_left_wall_visibility(self, context):
        toggle_wall_visibility("Booth_Wall_Left", self.left_wall_visible)

    def update_right_wall_visibility(self, context):
        toggle_wall_visibility("Booth_Wall_Right", self.right_wall_visible)
    
    
    def update_back_wall_dimensions(self, context):
        try:
            obj = bpy.data.objects["Booth_Wall_Back"]
            actual_height = self.booth_master_height - self.floor_height - self.roof_height
            
            obj.scale = (self.back_wall_length, self.back_wall_width, actual_height)
            obj.location.x = self.back_wall_offset 
            obj.location.y = self.floor_length / 2.0 - self.back_wall_width / 2.0
            obj.location.z = self.floor_height + (actual_height / 2.0)
        except KeyError: pass

    def update_back_wall_color(self, context):
        obj = bpy.data.objects.get("Booth_Wall_Back")
        if obj:
            mat = add_material("Booth_Wall_Back_mat", self.back_wall_color)
            if not obj.data.materials:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat

    def update_left_wall_dimensions(self, context):
        try:
            obj = bpy.data.objects["Booth_Wall_Left"]
            actual_height = self.booth_master_height - self.floor_height - self.roof_height

            obj.scale = (self.left_wall_width, self.left_wall_length, actual_height)
            obj.location.x = self.floor_width / 2.0 - self.left_wall_width / 2.0
            obj.location.y = self.left_wall_offset 
            obj.location.z = self.floor_height + (actual_height / 2.0)
        except KeyError: pass
    
    def update_left_wall_color(self, context):
        obj = bpy.data.objects.get("Booth_Wall_Left")
        if obj:
            mat = add_material("Booth_Wall_Left_mat", self.left_wall_color)
            if not obj.data.materials:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat

    def update_right_wall_dimensions(self, context):
        try:
            obj = bpy.data.objects["Booth_Wall_Right"]
            actual_height = self.booth_master_height - self.floor_height - self.roof_height

            obj.scale = (self.right_wall_width, self.right_wall_length, actual_height)
            obj.location.x = -self.floor_width / 2.0 + self.right_wall_width / 2.0
            obj.location.y = self.right_wall_offset 
            obj.location.z = self.floor_height + (actual_height / 2.0)
        except KeyError: pass

    def update_right_wall_color(self, context):
        obj = bpy.data.objects.get("Booth_Wall_Right")
        if obj:
            mat = add_material("Booth_Wall_Right_mat", self.right_wall_color)
            if not obj.data.materials:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat

    #____________FLOOR_______________

    floor_color: bpy.props.FloatVectorProperty(
        name="Floor Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        update=update_floor_color
    )
    floor_width: bpy.props.FloatProperty(name="Width", default=3.0, min=3.0, max=6.0, description="The width of the floor (X-axis)", update=update_floor_dimensions)
    floor_length: bpy.props.FloatProperty(name="Length", default=3.0, min=3.0, max=6.0, description="The length of the floor (Y-axis)", update=update_floor_dimensions)
    floor_height: bpy.props.FloatProperty(
        name="Floor Height",
        min=0.0,
        max=0.1,
        default=0.1,
        update=update_booth_heights
    )    
    #____________ROOF_______________
    roof_color: bpy.props.FloatVectorProperty(
        name="Roof Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        update=update_roof_color
    )
    roof_width: bpy.props.FloatProperty(name="Width", default=3.0, min=3.0, max=6.0, description="The width of the roof", update=update_roof_dimensions)
    roof_length: bpy.props.FloatProperty(name="Length", default=3.0, min=3.0, max=6.0, description="The length of the roof", update=update_roof_dimensions)
    roof_height: bpy.props.FloatProperty(name="Height", default=0.1, min=0.0, max=0.1,  description="The height of the roof", update=update_booth_heights)

    #____________WALL_____________
    
    back_wall_offset: bpy.props.FloatProperty(name="Slide", default=0.0, min=-2.0, max=2.0, update=update_back_wall_dimensions)
    left_wall_offset: bpy.props.FloatProperty(name="Slide", default=0.0, min=-2.0, max=2.0, update=update_left_wall_dimensions)
    right_wall_offset: bpy.props.FloatProperty(name="Slide", default=0.0, min=-2.0, max=2.0, update=update_right_wall_dimensions)
    
    back_wall_length: bpy.props.FloatProperty(name="Length", default=3.0, min=1.0, max=6.0, update=update_back_wall_dimensions) 
    back_wall_width: bpy.props.FloatProperty(name="Thickness", default=0.1, min=0.01, max=0.1, update=update_back_wall_dimensions)
    back_wall_height: bpy.props.FloatProperty(name="Height", default=2.7, min=1.0, max=2.8, update=update_back_wall_dimensions)
    back_wall_visible: bpy.props.BoolProperty(name="Visible", default=True, update=update_back_wall_visibility)
    back_wall_color: bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', size=4, min=0.0, max=1.0, default=(1.0, 1.0, 1.0, 1.0), update=update_back_wall_color)

    left_wall_length: bpy.props.FloatProperty(name="Length", default=3.0, min=1.0, max=6.0, update=update_left_wall_dimensions)
    left_wall_width: bpy.props.FloatProperty(name="Thickness", default=0.1, min=0.01, max=0.1, update=update_left_wall_dimensions)
    left_wall_height: bpy.props.FloatProperty(name="Height", default=2.7, min=1.0, max=2.8, update=update_left_wall_dimensions)
    left_wall_visible: bpy.props.BoolProperty(name="Visible", default=True, update=update_left_wall_visibility)
    left_wall_color: bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', size=4, min=0.0, max=1.0, default=(1.0, 1.0, 1.0, 1.0), update=update_left_wall_color)

    right_wall_length: bpy.props.FloatProperty(name="Length", default=3.0, min=1.0, max=6.0, update=update_right_wall_dimensions)
    right_wall_width: bpy.props.FloatProperty(name="Thickness", default=0.1, min=0.01, max=0.1, update=update_right_wall_dimensions)
    right_wall_height: bpy.props.FloatProperty(name="Height", default=2.7, min=1.0, max=2.8, update=update_right_wall_dimensions)
    right_wall_visible: bpy.props.BoolProperty(name="Visible", default=True, update=update_right_wall_visibility)
    right_wall_color: bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', size=4, min=0.0, max=1.0, default=(1.0, 1.0, 1.0, 1.0), update=update_right_wall_color)

    #____________CHAIR_______________
    chair_type: bpy.props.EnumProperty(
        name="Chair Type",
        items=[
        ('CHAIR_A', "Bar stool", ""), 
        ('CHAIR_B', "Uncovered Futura Chair", ""),
        ('CHAIR_C', "Covered Futura Chair", ""), 
        ('CHAIR_D', "Folded Futura Chair", ""),
        ('CHAIR_E', "Tiffany Chair", ""),
        ],
        update=update_chair_style
    )
    chair_color: bpy.props.FloatVectorProperty(
        name="Chair Color", subtype='COLOR', default=(1.0, 1.0, 1.0, 1.0), size=4, min=0.0,
        max=1.0, update=update_chair_style
    )
    chair_count: bpy.props.IntProperty(
        name="Chair Count", 
        default=2, min=0, max=8, 
        update=update_chair_count
    )
    chair_rotation_random: bpy.props.FloatProperty(
        name="Rotation Randomness",
        description="Randomly rotates each chair differently",
        default=0.0,
        min=0.0,
        max=360.0,
        precision=1,
        update=update_chair_rotation
    )
    
    #____________TABLE_______________

    table_type: bpy.props.EnumProperty(
        name="Table Type",
        items=[
        ('TABLE_A', "IBM Table", ""), 
        ('TABLE_B', "R8 Table", ""),
        ('TABLE_C', "Round Coffee Table", ""),
        ('TABLE_D', "Square Coffee Table", "")
        ],
        update=update_table_style
    )
    table_color: bpy.props.FloatVectorProperty(
        name="Table Color", subtype='COLOR', default=(1.0, 1.0, 1.0, 1.0), size=4, min=0.0,
        max=1.0, update=update_table_style
    )
    table_count: bpy.props.IntProperty(
        name="Table Count", 
        default=1, min=0, max=8, 
        update=update_table_count
    )
    table_rotation_random: bpy.props.FloatProperty(
        name="Rotation Randomness",
        description="Randomly rotates each table differently",
        default=0.0,
        min=0.0,
        max=360.0,
        precision=1,
        update=update_table_rotation
    )

    
    #____________FLOOR ELEMENT_______________

    floorelement_type: bpy.props.EnumProperty(
        name="floorelement Type",
        items=[
        ('floorelement_A', "Clothing Rack", ""), 
        ('floorelement_B', "Standing Mirror", ""),
        ('floorelement_C', "TV Stand", "")
        ],
        update=update_floorelement_style
    )
    floorelement_color: bpy.props.FloatVectorProperty(
        name="floorelement Color", subtype='COLOR', default=(1.0, 1.0, 1.0, 1.0), size=4, min=0.0,
        max=1.0, update=update_floorelement_style
    )
    floorelement_count: bpy.props.IntProperty(
        name="floorelement Count", 
        default=2, min=0, max=8, 
        update=update_floorelement_count
    )
    floorelement_rotation_random: bpy.props.FloatProperty(
        name="Floor Element Rotation",
        description="Randomly rotates each Floor Element differently",
        default=0.0,
        min=0.0,
        max=360.0,
        precision=1,
        update=update_floorelement_rotation
    )
    
    #____________CEILING ELEMENT_______________
    
    ceilingelement_type: bpy.props.EnumProperty(
        name="ceilingelement Type",
        items=[
        ('CEILINGELEMENT_A', "Flushed Lamp", ""), 
        ('CEILINGELEMENT_B', "LED Lamp", ""),  
        ('CEILINGELEMENT_C', "Track Light", "")
        ],
        update=update_ceilingelement_style
    )
    ceilingelement_color: bpy.props.FloatVectorProperty(
        name="ceilingelement Color", subtype='COLOR', default=(1.0, 1.0, 1.0, 1.0), size=4, min=0.0, max=1.0, update=update_ceilingelement_style
    )
    ceilingelement_count: bpy.props.IntProperty(
        name="ceilingelement Count", 
        default=4, min=0, max=8, 
        update=update_ceilingelement_count
    )
    ceilingelement_rotation_random: bpy.props.FloatProperty(
        name="Ceiling Rotation Intensity",
        description="Randomly rotates each Floor Element differently",
        default=0.0,
        min=0.0,
        max=360.0,
        precision=1,
        update=update_ceilingelement_rotation
    )
    
    #____________POLE______________
    
    pole_count: bpy.props.IntProperty(
        name="Pole Count", 
        default=4, min=0, max=8, 
        update=update_pole_count
    )
    pole_color: bpy.props.FloatVectorProperty(
        name="Pole Color", 
        subtype='COLOR', 
        default=(1.0, 1.0, 1.0, 1.0), 
        size=4, 
        min=0.0, max=1.0,
        update=update_pole_color 
    )
    
    #_____HUMAN________
    
    human_gender: bpy.props.EnumProperty(
        name="Gender",
        items=[('MAN', "Man", ""), ('WOMAN', "Woman", "")],
        update=update_human_style
    )
    human_color: bpy.props.FloatVectorProperty(
        name="Human Color", 
        subtype='COLOR', 
        default=(1.0, 1.0, 1.0, 1.0), 
        size=4, 
        min=0.0, 
        max=1.0, 
        update=update_human_style
    )
    human_count: bpy.props.IntProperty(
        name="Human Count", 
        default=0, 
        min=0, 
        max=3, 
        update=update_human_count
    )
    human_height: bpy.props.FloatProperty(
        name="Human Height", 
        default=1.70, min=1.6, 
        max=2.0, 
        update=update_human_style
    )
    human_seed: bpy.props.IntProperty(
        name="Human Seed", 
        default=1, 
        update=lambda self, 
        ctx: bpy.ops.object.modify_human_booth_position()
    )
    human_rotation: bpy.props.FloatProperty(
        name="Human Rotation", 
        default=0.0, 
        min=0.0, 
        max=360.0, 
        precision=1,
        update=update_human_rotation_clean
    )
    
    #____________LIGHT______________
    
    def update_light_visibility_callback(self, context):
        light_map = {
            'light_top_visible': "Area_Light_Top",
            'light_back_visible': "Area_Light_Back",
            'light_front_visible': "Area_Light_Front",
            'light_left_visible': "Area_Light_Left",
            'light_right_visible': "Area_Light_Right",
        }
        for prop_name, light_name in light_map.items():
            if hasattr(self, prop_name):
                visible = getattr(self, prop_name)
                toggle_light_visibility(light_name, visible)
                
    show_chair_settings: bpy.props.BoolProperty(name="Chairs", default=False)
    show_table_settings: bpy.props.BoolProperty(name="Tables", default=False)
    show_floorelement_settings: bpy.props.BoolProperty(name="Floor Elements", default=False)
    show_ceiling_settings: bpy.props.BoolProperty(name="Ceiling Elements", default=False)
    show_pole_settings: bpy.props.BoolProperty(name="Poles", default=False)
    
    show_floor_settings: bpy.props.BoolProperty(name="Show Floor Settings", default=False)
    show_roof_settings: bpy.props.BoolProperty(name="Show Roof Settings", default=False)
    show_walls_settings: bpy.props.BoolProperty(name="Show Wall Settings", default=False)
    
    show_human_settings: bpy.props.BoolProperty(name="Show Human Settings", default=False)
    show_lights_settings: bpy.props.BoolProperty(name="Show Lights Settings", default=False)
    show_camera_settings: bpy.props.BoolProperty(name="Show Camera Settings", default=False)
    
    light_top_visible: bpy.props.BoolProperty(name="Top Light", default=True, description="Toggle visibility of the Top Area Light", update=update_light_visibility_callback)
    light_back_visible: bpy.props.BoolProperty(name="Back Light", default=True, description="Toggle visibility of the Back Area Light", update=update_light_visibility_callback)
    light_front_visible: bpy.props.BoolProperty(name="Front Light", default=True, description="Toggle visibility of the Front Area Light", update=update_light_visibility_callback)
    light_left_visible: bpy.props.BoolProperty(name="Left Light", default=True, description="Toggle visibility of the Left Area Light", update=update_light_visibility_callback)
    light_right_visible: bpy.props.BoolProperty(name="Right Light", default=True, description="Toggle visibility of the Right Area Light", update=update_light_visibility_callback)


# ------------------------------------DRAWS-----------------------------------

class GENERATE_Booth(bpy.types.Panel):
    bl_label = "Generate Booth"
    bl_category = "Generative Booth"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.generative_booth_props
        
        box = layout.box()
        box.label(text="Generate Full Booth", icon='CUBE')
        col = box.column(align=True)
        col.prop(props, "floor_width", text="Width")
        col.prop(props, "floor_length", text="Length")
        col.prop(props, "booth_master_height", text="Height")
        
        box.operator("mesh.generate_full_booth", icon='STICKY_UVS_DISABLE')

class GENERATE_Base(bpy.types.Panel):
    bl_label = "Generate Base"
    bl_category = "Generative Booth"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.generative_booth_props
        
        # ------------------------------------FLOOR-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_floor = 'TRIA_DOWN' if getattr(props, "show_floor_settings", False) else 'TRIA_RIGHT'
        row.prop(props, "show_floor_settings", text="", icon=icon_floor, emboss=False)
        row.label(text="Floor", icon='AXIS_TOP')
        
        if getattr(props, "show_floor_settings", False):
            col_layout = box.column(align=False)
            
            row = col_layout.row()
            row.label(text="    Height:")
            row.prop(props, "floor_height", text="")
            
            col_layout.separator(factor=0.5)
            
            row = col_layout.row()
            row.label(text="    Color:")
            row.prop(props, "floor_color", text="")

        # ------------------------------------ROOF-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_roof = 'TRIA_DOWN' if getattr(props, "show_roof_settings", False) else 'TRIA_RIGHT'
        row.prop(props, "show_roof_settings", text="", icon=icon_roof, emboss=False)
        row.label(text="Roof", icon='GRID')
        
        if getattr(props, "show_roof_settings", False):
            col_layout = box.column(align=False)
            
            row = col_layout.row()
            row.label(text="    Height:")
            row.prop(props, "roof_height", text="")
            
            col_layout.separator(factor=0.5)
            
            row = col_layout.row()
            row.label(text="    Color:")
            row.prop(props, "roof_color", text="")
            

        # ------------------------------------WALLS-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_walls = 'TRIA_DOWN' if getattr(props, "show_walls_settings", False) else 'TRIA_RIGHT'
        row.prop(props, "show_walls_settings", text="", icon=icon_walls, emboss=False)
        row.label(text="Walls", icon='AXIS_SIDE')
        
        if getattr(props, "show_walls_settings", False):
            col_layout = box.column(align=False)
        
            subbox = col_layout.box()
            row = subbox.row(align=True)
            row.prop(props, "back_wall_visible", icon='HIDE_OFF' if props.back_wall_visible else 'HIDE_ON', text="")
            row.label(text=" Back Wall") 
            
            if props.back_wall_visible:
                wall_col = subbox.column(align=True)
                wall_col.prop(props, "back_wall_length", text="Length")
                wall_col.prop(props, "back_wall_width", text="Width")
                
                row = subbox.row(align=True)
                row.label(text='     Position:')
                row.prop(props, "back_wall_offset", text="")
                
                color_row = subbox.row(align=True)
                color_row.label(text="     Color:")
                color_row.prop(props, "back_wall_color", text="")
            
            subbox = col_layout.box()
            row = subbox.row(align=True)
            row.prop(props, "left_wall_visible", icon='HIDE_OFF' if props.left_wall_visible else 'HIDE_ON', text="")
            row.label(text=" Left Wall")
            
            if props.left_wall_visible:
                wall_col = subbox.column(align=True)
                wall_col.prop(props, "left_wall_length", text="Length")
                wall_col.prop(props, "left_wall_width", text="Width")
                
                row = subbox.row(align=True)
                row.label(text='     Position:')
                row.prop(props, "left_wall_offset", text="")
                
                
                color_row = subbox.row(align=True)
                color_row.label(text="     Color:")
                color_row.prop(props, "left_wall_color", text="")
                
            subbox = col_layout.box()
            row = subbox.row(align=True)
            row.prop(props, "right_wall_visible", icon='HIDE_OFF' if props.right_wall_visible else 'HIDE_ON', text="")
            row.label(text=" Right Wall")
            
            if props.right_wall_visible:
                wall_col = subbox.column(align=True)
                wall_col.prop(props, "right_wall_length", text="Length")
                wall_col.prop(props, "right_wall_width", text="Width")
                
                row = subbox.row(align=True)
                row.label(text='     Position:')
                row.prop(props, "right_wall_offset", text="")
                
                color_row = subbox.row(align=True)
                color_row.label(text="     Color:")
                color_row.prop(props, "right_wall_color", text="")
                

class GENERATE_Booth_Elements(bpy.types.Panel):
    bl_label = "Generate Booth Elements"
    bl_category = "Generative Booth"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.generative_booth_props
        active_obj = context.active_object
        
        # ------------------------------------TABLE-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_table = 'TRIA_DOWN' if props.show_table_settings else 'TRIA_RIGHT'
        
        row.prop(props, "show_table_settings", text="", icon=icon_table, emboss=False)
        row.label(text="Table", icon='NOCURVE')
        
        if props.show_table_settings:
            col_layout = box.column(align=False)
            
            if active_obj and active_obj.name.startswith("Booth_Table_"):
                row = col_layout.row()
                row.label(text="    Type:")
                row.prop(active_obj, "individual_table_type", text="")
                
                col_layout.separator(factor=0.5)
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "table_count", text="")
                
                col_layout.separator(factor=0.5)
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(active_obj, "individual_table_color", text="")
            else:
                row = col_layout.row()
                row.label(text="    Type:")
                row.prop(props, "table_type", text="")
                
                col_layout.separator(factor=0.5)
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "table_count", text="")
                
                col_layout.separator(factor=0.5)
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(props, "table_color", text="")
                
            col_layout.separator(factor=0.5)
            
            row = col_layout.row()
            row.label(text="    Rotation:")
            row.prop(props, "table_rotation_random", text="")
            
            col_layout.separator(factor=0.5)
            col_layout.operator("object.modify_table_booth_position", text="Generate Position", icon='STICKY_UVS_DISABLE')
        
        # ------------------------------------CHAIR-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_chair = 'TRIA_DOWN' if props.show_chair_settings else 'TRIA_RIGHT'
        
        row.prop(props, "show_chair_settings", text="", icon=icon_chair, emboss=False)
        row.label(text="Chair", icon='CON_SAMEVOL')
        
        if props.show_chair_settings:
            col_layout = box.column(align=False)
            
            active_obj = context.active_object
            if active_obj and active_obj.name.startswith("Booth_Chair_"):
                row = col_layout.row()
                row.label(text="    Type:")
                row.prop(active_obj, "individual_chair_type", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "chair_count", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(active_obj, "individual_chair_color", text="")
            else:
                row = col_layout.row()
                row.label(text="    Type:")
                row.prop(props, "chair_type", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "chair_count", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(props, "chair_color", text="")
                
            col_layout.separator(factor=0.5) 
            
            row = col_layout.row()
            row.label(text="    Rotation:")
            row.prop(props, "chair_rotation_random", text="")
            
            col_layout.separator(factor=0.5) 
            col_layout.operator("object.modify_chair_booth_position", text="Generate Position", icon='STICKY_UVS_DISABLE')

        # ------------------------------------FLOOR ELEMENT-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_floor = 'TRIA_DOWN' if props.show_floorelement_settings else 'TRIA_RIGHT'
        
        row.prop(props, "show_floorelement_settings", text="", icon=icon_floor, emboss=False)
        
        row.label(text="Floor Decor", icon='ASSET_MANAGER')
        
        if props.show_floorelement_settings:
            col_layout = box.column(align=False)
            
            if active_obj and active_obj.name.startswith("Booth_floorelement_"):
                row = col_layout.row()
                row.label(text="    Type:")
                row.prop(active_obj, "individual_floorelement_type", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "floorelement_count", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(active_obj, "individual_floorelement_color", text="")
            else:
                row = col_layout.row()
                row.label(text="    Type:")
                row.prop(props, "floorelement_type", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "floorelement_count", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(props, "floorelement_color", text="")
                
            col_layout.separator(factor=0.5) 
            
            row = col_layout.row()
            row.label(text="    Rotation:")
            row.prop(props, "floorelement_rotation_random", text="")
            
            col_layout.separator(factor=0.5) 
            col_layout.operator("object.modify_floorelement_booth_position", text="Generate Position", icon='STICKY_UVS_DISABLE')
        
        
        # ------------------------------------CEILING ELEMENT-----------------------------------
        
        box = layout.box()
        row = box.row(align=True)
        
        icon_ceiling = 'TRIA_DOWN' if props.show_ceiling_settings else 'TRIA_RIGHT'
        
        row.prop(props, "show_ceiling_settings", text="", icon=icon_ceiling, emboss=False)
        row.label(text="Lamp", icon='ALIGN_TOP')
        
        if props.show_ceiling_settings:
            col_layout = box.column(align=False)
            
            active_obj = context.active_object
            if active_obj and active_obj.name.startswith("Booth_ceilingelement_"):
                row = col_layout.row()
                row.label(text="    Type:")
                row.prop(active_obj, "individual_ceilingelement_type", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "ceilingelement_count", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(active_obj, "individual_ceilingelement_color", text="")
            else:
                row = col_layout.row()
                row.label(text="    Type:")
                row.prop(props, "ceilingelement_type", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "ceilingelement_count", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(props, "ceilingelement_color", text="")
                
            col_layout.separator(factor=0.5) 
            
            row = col_layout.row()
            row.label(text="    Rotation:")
            row.prop(props, "ceilingelement_rotation_random", text="")
            
            col_layout.separator(factor=0.5) 
            col_layout.operator("object.modify_ceilingelement_booth_position", text="Generate Position", icon='STICKY_UVS_DISABLE')
        
        # ------------------------------------POLES-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_pole = 'TRIA_DOWN' if props.show_pole_settings else 'TRIA_RIGHT'
        
        row.prop(props, "show_pole_settings", text="", icon=icon_pole, emboss=False)
        row.label(text="Poles", icon='MOD_ARRAY')
        
        if props.show_pole_settings:
            col_layout = box.column(align=False)
            
            active_obj = context.active_object
            if active_obj and active_obj.name.startswith("Booth_Pole_"):
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "pole_count", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(active_obj, "individual_pole_color", text="")
            else:
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "pole_count", text="")
                
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(props, "pole_color", text="")
                
            col_layout.separator(factor=0.5) 
            col_layout.operator("object.modify_pole_booth_position", text="Generate Position", icon='STICKY_UVS_DISABLE')

class GENERATE_Lights(bpy.types.Panel):
    bl_label = "Generate Human, Lights, and Camera"
    bl_category = "Generative Booth"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.generative_booth_props
        
        # ------------------------------------HUMAN-----------------------------------
        box = layout.box()
        row = box.row(align=True)

        icon_human = 'TRIA_DOWN' if props.show_human_settings else 'TRIA_RIGHT'
        row.prop(props, "show_human_settings", text="", icon=icon_human, emboss=False)
        row.label(text="Human", icon='USER')

        if props.show_human_settings:
            col_layout = box.column(align=False)
            active_obj = context.active_object
            
            col_layout.operator("object.add_human_booth", text="Add Human", icon='ADD')
            col_layout.separator()
            
            if active_obj and active_obj.name.startswith("Booth_Human_"):
                row = col_layout.row()
                row.label(text="    Gender:")
                row.prop(active_obj, "individual_human_gender", expand=True)
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "human_count", text="")
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Height:")
                row.prop(active_obj, "individual_human_height", text="")
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(active_obj, "individual_human_color", text="")
                
            else:
                row = col_layout.row()
                row.label(text="    Gender:")
                row.prop(props, "human_gender", expand=True)
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Count:")
                row.prop(props, "human_count", text="")
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Height:")
                row.prop(props, "human_height", text="")
                col_layout.separator(factor=0.5) 
                
                row = col_layout.row()
                row.label(text="    Color:")
                row.prop(props, "human_color", text="")
            
            col_layout.separator(factor=0.5) 
            
            row = col_layout.row()
            row.label(text="    Rotation:")
            row.prop(props, "human_rotation", text="")
            
            col_layout.separator(factor=0.5) 
            col_layout.operator("object.modify_human_booth_position", text="Generate Position", icon='STICKY_UVS_DISABLE')
            
        # ------------------------------------LIGHTS-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_lights = 'TRIA_DOWN' if getattr(props, "show_lights_settings", False) else 'TRIA_RIGHT'
        row.prop(props, "show_lights_settings", text="", icon=icon_lights, emboss=False)
        row.label(text="Lights", icon='LIGHT_AREA')

        if getattr(props, "show_lights_settings", False):
            col_layout = box.column(align=False)
            
            col_layout.operator("object.add_all_lights", text="Add Lights", icon='ADD')
            col_layout.separator(factor=0.5) 
            
            subbox = col_layout.box()
            subbox.label(text="Lights Visibility:", icon='RESTRICT_VIEW_OFF')
            
            col_visibility = subbox.column(align=True)
            
            lights_list = [
                ("light_top_visible", " Top Light"),
                ("light_back_visible", " Back Light"),
                ("light_front_visible", " Front Light"),
                ("light_left_visible", " Left Light"),
                ("light_right_visible", " Right Light"),
            ]

            for prop_name, label in lights_list:
                row = col_visibility.row(align=True)
                is_visible = getattr(props, prop_name, True)
                row.prop(props, prop_name, icon='HIDE_OFF' if is_visible else 'HIDE_ON', text="")
                row.label(text=label)
                

        # ------------------------------------CAMERA-----------------------------------
        box = layout.box()
        row = box.row(align=True)
        
        icon_camera = 'TRIA_DOWN' if getattr(props, "show_camera_settings", False) else 'TRIA_RIGHT'
        row.prop(props, "show_camera_settings", text="", icon=icon_camera, emboss=False)
        row.label(text="Camera", icon='OUTLINER_OB_CAMERA')
        
        if getattr(props, "show_camera_settings", False):
            col_layout = box.column(align=False)
            
            col_layout.operator("object.add_keyframed_camera", text="Add Keyframed Camera", icon='ADD')


classes = (
    MESH_OT_generate_full_booth,
    OBJECT_OT_add_all_lights, 
    MESH_OT_add_floor, 
    MESH_OT_add_roof, 
    MESH_OT_add_all_walls, 
    OBJECT_OT_modify_chair_booth_position,
    OBJECT_OT_modify_table_booth_position,
    OBJECT_OT_modify_floorelement_booth_position,
    OBJECT_OT_modify_ceilingelement_booth_position,
    OBJECT_OT_modify_pole_booth_position,
    OBJECT_OT_add_human_booth,
    OBJECT_OT_modify_human_booth_position,
    OBJECT_OT_add_keyframed_camera,
    GenerativeBoothProperties,
    GENERATE_Booth,
    GENERATE_Base, 
    GENERATE_Booth_Elements, 
    GENERATE_Lights
)

#------------------------------------REGISTER/UNREGISTER-----------------------------------

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.generative_booth_props = bpy.props.PointerProperty(
        type=GenerativeBoothProperties
    )
    
    bpy.types.Object.individual_floorelement_type = bpy.props.EnumProperty(
        name="Type",
        items=[
            ('floorelement_A', "Clothing Rack", ""), 
            ('floorelement_B', "Standing Mirror", ""),
            ('floorelement_C', "TV Stand", "")
        ],
        default='floorelement_A',
        update=update_individual_element_style
    )
    
    bpy.types.Object.individual_floorelement_color = bpy.props.FloatVectorProperty(
        name="Color", 
        subtype='COLOR', 
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=update_individual_element_style
    )

    if sync_ui_on_selection_change not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(sync_ui_on_selection_change)
        
    bpy.types.Object.individual_table_type = bpy.props.EnumProperty(
        name="Type",
        items=[
            ('TABLE_A', "IBM Table", ""), 
            ('TABLE_B', "R8 Table", ""),
            ('TABLE_C', "Round Coffee Table", ""),
            ('TABLE_D', "Square Coffee Table", "")
        ],
        default='TABLE_A',
        update=update_individual_table_style
    )
    
    bpy.types.Object.individual_table_color = bpy.props.FloatVectorProperty(
        name="Color", 
        subtype='COLOR', 
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=update_individual_table_style
    )

    if sync_ui_on_table_selection_change not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(sync_ui_on_table_selection_change)
        
    bpy.types.Object.individual_chair_type = bpy.props.EnumProperty(
        name="Type",
        items=[
            ('CHAIR_A', "Bar stool", ""), 
            ('CHAIR_B', "Uncovered Futura Chair", ""),
            ('CHAIR_C', "Covered Futura Chair", ""), 
            ('CHAIR_D', "Folded Futura Chair", ""),
            ('CHAIR_E', "Tiffany Chair", ""),
        ],
        default='CHAIR_A',
        update=update_individual_chair_style
    )
    
    bpy.types.Object.individual_chair_color = bpy.props.FloatVectorProperty(
        name="Color", 
        subtype='COLOR', 
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=update_individual_chair_style
    )

    if sync_ui_on_chair_selection_change not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(sync_ui_on_chair_selection_change)
        
    bpy.types.Object.individual_ceilingelement_type = bpy.props.EnumProperty(
        name="Type",
        items=[
            ('CEILINGELEMENT_A', "Flushed Lamp", ""), 
            ('CEILINGELEMENT_B', "LED Lamp", ""),  
            ('CEILINGELEMENT_C', "Track Light", "")
        ],
        default='CEILINGELEMENT_A',
        update=update_individual_ceilingelement_style
    )
    
    bpy.types.Object.individual_ceilingelement_color = bpy.props.FloatVectorProperty(
        name="Color", 
        subtype='COLOR', 
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=update_individual_ceilingelement_style
    )

    if sync_ui_on_ceilingelement_selection_change not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(sync_ui_on_ceilingelement_selection_change)
        
    bpy.types.Object.individual_pole_color = bpy.props.FloatVectorProperty(
        name="Color", 
        subtype='COLOR', 
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=update_individual_pole_style
    )

    if sync_ui_on_pole_selection_change not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(sync_ui_on_pole_selection_change)
    
    bpy.types.Object.individual_human_gender = bpy.props.EnumProperty(
        items=[('MAN', "Man", ""), ('WOMAN', "Woman", "")],
        default='MAN',
        update=update_individual_human_style
    )
    
    bpy.types.Object.individual_human_height = bpy.props.FloatProperty(
        default=1.70, min=1.6, max=2.0,
        update=update_individual_human_style
    )
    
    bpy.types.Object.individual_human_color = bpy.props.FloatVectorProperty(
        subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0),
        update=update_individual_human_style
    )

    bpy.app.handlers.depsgraph_update_post.append(sync_ui_on_human_selection_change)


def unregister():
    if sync_ui_on_selection_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_ui_on_selection_change)

    del bpy.types.Object.individual_floorelement_type
    del bpy.types.Object.individual_floorelement_color
    
    if sync_ui_on_chair_selection_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_ui_on_chair_selection_change)

    del bpy.types.Object.individual_chair_type
    del bpy.types.Object.individual_chair_color
    
    if sync_ui_on_table_selection_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_ui_on_table_selection_change)

    del bpy.types.Object.individual_table_type
    del bpy.types.Object.individual_table_color
    
    if sync_ui_on_ceilingelement_selection_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_ui_on_ceilingelement_selection_change)

    del bpy.types.Object.individual_ceilingelement_type
    del bpy.types.Object.individual_ceilingelement_color
    
    if sync_ui_on_pole_selection_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_ui_on_pole_selection_change)

    del bpy.types.Object.individual_pole_color
    
    if sync_ui_on_human_selection_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_ui_on_human_selection_change)
        
    del bpy.types.Object.individual_human_gender
    del bpy.types.Object.individual_human_height
    del bpy.types.Object.individual_human_color

    del bpy.types.Scene.generative_booth_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
if __name__ == "__main__":
    register()