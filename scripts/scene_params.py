# ============================================================
#  Blender 場景參數腳本
#  用法：Blender 上方 Scripting 分頁 → New → 貼上 → 改下面數字 → Run Script
#  每次 Run 都會重建整個場景，改壞了再 Run 一次就好
# ============================================================

P = {
    # ---- 主體 ----
    "ball_radius":    1.0,              # 球半徑
    "ball_pos":       (0.0, 0.0, 1.0),  # 球位置 X, Y, Z
    "ball_color":     (0.90, 0.35, 0.20),  # 球顏色 R, G, B（0~1）
    "ball_rough":     0.35,             # 粗糙度 0=鏡面 1=全霧

    # ---- 地板 ----
    "floor_size":     12.0,
    "floor_color":    (0.82, 0.80, 0.76),
    "floor_rough":    0.90,

    # ---- 主燈 ----
    "key_pos":        (4.0, -4.0, 6.0),
    "key_energy":     800.0,            # 亮度，數字越大越亮
    "key_size":       5.0,              # 燈面大小，越大陰影越軟
    "key_rot_deg":    (50.0, 0.0, 45.0),

    # ---- 補光 ----
    "fill_pos":       (-5.0, -2.0, 3.0),
    "fill_energy":    200.0,
    "fill_size":      6.0,
    "fill_rot_deg":   (70.0, 0.0, -60.0),

    # ---- 相機 ----
    "cam_pos":        (7.0, -7.0, 4.5),
    "cam_rot_deg":    (68.0, 0.0, 45.0),
    "cam_lens":       50.0,             # 焦距 mm，越小越廣角

    # ---- 世界背景 ----
    "world_color":    (0.05, 0.05, 0.06),
    "world_strength": 1.0,

    # ---- 出圖 ----
    "res":            (1200, 950),
    "samples":        32,
}

# ============================================================
#  以下不用改
# ============================================================
import bpy, math

def rgba(c):
    return (c[0], c[1], c[2], 1.0)

def rad3(d):
    return tuple(math.radians(v) for v in d)

def make_mat(name, color, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba(color)
    b.inputs["Roughness"].default_value = rough
    return m

# 清場
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# 世界背景
world = bpy.data.worlds.new("World")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = rgba(P["world_color"])
bg.inputs["Strength"].default_value = P["world_strength"]
sc.world = world

# 地板
bpy.ops.mesh.primitive_plane_add(size=P["floor_size"])
floor = bpy.context.object
floor.name = "Floor"
floor.data.materials.append(make_mat("FloorMat", P["floor_color"], P["floor_rough"]))

# 球
bpy.ops.mesh.primitive_uv_sphere_add(radius=P["ball_radius"], location=P["ball_pos"])
ball = bpy.context.object
ball.name = "Ball"
bpy.ops.object.shade_smooth()
ball.data.materials.append(make_mat("BallMat", P["ball_color"], P["ball_rough"]))

# 主燈
bpy.ops.object.light_add(type='AREA', location=P["key_pos"])
key = bpy.context.object
key.name = "Key"
key.data.energy = P["key_energy"]
key.data.size = P["key_size"]
key.rotation_euler = rad3(P["key_rot_deg"])

# 補光
bpy.ops.object.light_add(type='AREA', location=P["fill_pos"])
fill = bpy.context.object
fill.name = "Fill"
fill.data.energy = P["fill_energy"]
fill.data.size = P["fill_size"]
fill.rotation_euler = rad3(P["fill_rot_deg"])

# 相機
bpy.ops.object.camera_add(location=P["cam_pos"])
cam = bpy.context.object
cam.name = "Camera"
cam.rotation_euler = rad3(P["cam_rot_deg"])
cam.data.lens = P["cam_lens"]
sc.camera = cam

# 渲染設定
# EEVEE 的 enum 名稱各版不同（4.2~4.5 是 BLENDER_EEVEE_NEXT，5.0 改回 BLENDER_EEVEE）
_engines = sc.render.bl_rna.properties["engine"].enum_items.keys()
for _e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    if _e in _engines:
        sc.render.engine = _e
        break
sc.render.resolution_x, sc.render.resolution_y = P["res"]
sc.eevee.taa_render_samples = P["samples"]

print("場景重建完成：", [o.name for o in sc.objects])
