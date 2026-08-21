import bpy, math

# 清場
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# 地板
bpy.ops.mesh.primitive_plane_add(size=12)
floor = bpy.context.object; floor.name = "Floor"
m = bpy.data.materials.new("FloorMat"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.82,0.80,0.76,1)
m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
floor.data.materials.append(m)

# 主體
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0,0,1))
ball = bpy.context.object; ball.name = "Ball"
bpy.ops.object.shade_smooth()
m2 = bpy.data.materials.new("BallMat"); m2.use_nodes = True
b = m2.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.90,0.35,0.20,1)
b.inputs["Roughness"].default_value = 0.35
ball.data.materials.append(m2)

# 燈光：主燈 + 補光
bpy.ops.object.light_add(type='AREA', location=(4,-4,6))
key = bpy.context.object; key.data.energy = 800; key.data.size = 5
key.rotation_euler = (math.radians(50), 0, math.radians(45))
bpy.ops.object.light_add(type='AREA', location=(-5,-2,3))
fill = bpy.context.object; fill.data.energy = 200; fill.data.size = 6
fill.rotation_euler = (math.radians(70), 0, math.radians(-60))

# 相機
bpy.ops.object.camera_add(location=(7,-7,4.5))
cam = bpy.context.object
cam.rotation_euler = (math.radians(68), 0, math.radians(45))
sc.camera = cam

# 渲染設定
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1200, 950
sc.render.film_transparent = False

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath="/home/user/yao/out/smoke_test.blend")

print("OK objects:", [o.name for o in sc.objects])
print("engine:", sc.render.engine, "camera:", sc.camera.name)
