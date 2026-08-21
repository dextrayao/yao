"""HDRE 大型導覽系統 — 總高 195 cm"""
import bpy, bmesh, math, sys, os
from mathutils import Vector

TAU = math.tau
OUT = "/home/user/yao/out"
LOD = float(os.environ.get("HDRE_LOD", "1.0"))
def L(n, lo=8): return max(lo, int(round(n*LOD/4))*4)

def srgb(hexstr, a=1.0):
    h = hexstr.lstrip('#')
    def lin(c):
        c /= 255.0
        return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    return (lin(int(h[0:2],16)), lin(int(h[2:4],16)), lin(int(h[4:6],16)), a)

def mat(name, color, rough=0.45, metal=0.0, emit=None, emit_str=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = emit_str
    return m

# ---------- 機身輪廓 ----------
KEYS = [
    (0.000, 0.406, 0.3540,  0.0980), (0.055, 0.425, 0.3461,  0.0950),
    (0.160, 0.434, 0.3310,  0.0892), (0.400, 0.438, 0.2965,  0.0759),
    (0.700, 0.438, 0.2534,  0.0593), (1.050, 0.437, 0.2031,  0.0400),
    (1.350, 0.433, 0.1599,  0.0234), (1.550, 0.426, 0.1312,  0.0124),
    (1.700, 0.412, 0.1096,  0.0041), (1.800, 0.386, 0.0953, -0.0015),
    (1.855, 0.330, 0.0874, -0.0045), (1.882, 0.245, 0.0835, -0.0060),
]
N_POW, Z_TOP = 5.2, KEYS[-1][0]

def _interp(z, idx):
    z = max(0.0, min(Z_TOP, z))
    for i in range(len(KEYS)-1):
        z0, z1 = KEYS[i][0], KEYS[i+1][0]
        if z0 <= z <= z1:
            t = 0.0 if z1 == z0 else (z-z0)/(z1-z0)
            t = t*t*(3-2*t)
            return KEYS[i][idx]*(1-t) + KEYS[i+1][idx]*t
    return KEYS[-1][idx]

half_w = lambda z: _interp(z, 1)
half_d = lambda z: _interp(z, 2)
y_off  = lambda z: _interp(z, 3)

def se(t):
    ct, st = math.cos(t), math.sin(t)
    return (math.copysign(abs(ct)**(2.0/N_POW), ct),
            math.copysign(abs(st)**(2.0/N_POW), st))

def sect_pt(t, z):
    ex, ey = se(t)
    return Vector((half_w(z)*ex, y_off(z) + half_d(z)*ey, z))

def surf_y(x, z, front=True):
    a, b = half_w(z), half_d(z)
    r = min(1.0, abs(x)/a) if a > 1e-9 else 1.0
    d = b * max(0.0, 1.0 - r**N_POW)**(1.0/N_POW)
    return y_off(z) - d if front else y_off(z) + d

def smooth_obj(ob, angle=52.0):
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))
    except Exception:
        bpy.ops.object.shade_smooth()

# =========================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

M_BODY = mat("Body",     srgb("A5D362"), rough=0.40)
M_BACK = mat("BodyBack", srgb("7CAD3E"), rough=0.50)
M_TEAL = mat("Teal",     srgb("1AA5BE"), rough=0.34)
M_BEZL = mat("Bezel",    srgb("14859B"), rough=0.30)
M_GLOW = mat("Glow",     srgb("2BE9E4"), rough=0.25, emit=srgb("3BF4EF"), emit_str=5.0)
M_DOT  = mat("Dot",      srgb("24282A"), rough=0.18)

# 螢幕（發光 UI 貼圖）
M_SCR = bpy.data.materials.new("ScreenUI"); M_SCR.use_nodes = True
nt = M_SCR.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = srgb("0E1114")
bsdf.inputs["Roughness"].default_value = 0.26
if "Specular IOR Level" in bsdf.inputs:
    bsdf.inputs["Specular IOR Level"].default_value = 0.22
tex = nt.nodes.new("ShaderNodeTexImage")
SCREEN_TEX = os.environ.get("HDRE_SCREEN", "screen_glass.png")
tex.image = bpy.data.images.load(os.path.join(OUT, SCREEN_TEX))
tex.location = (-420, 120)
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
bsdf.inputs["Emission Strength"].default_value = 0.18

# ---------- 機身 ----------
NSEG, NRING = L(160), L(130)
bm = bmesh.new()
rings = []
for i in range(NRING+1):
    z = Z_TOP * ((i/NRING)**0.92)
    rings.append([bm.verts.new(sect_pt(TAU*j/NSEG, z)) for j in range(NSEG)])
for i in range(NRING):
    lo, up = rings[i], rings[i+1]
    for j in range(NSEG):
        k = (j+1) % NSEG
        bm.faces.new((lo[j], lo[k], up[k], up[j]))
bm.faces.new(list(reversed(rings[0])))
bm.faces.new(rings[-1])
me = bpy.data.meshes.new("BodyM"); bm.to_mesh(me); bm.free()
body = bpy.data.objects.new("Body", me); sc.collection.objects.link(body)
body.data.materials.append(M_BODY)
smooth_obj(body)
bv = body.modifiers.new("Bevel", 'BEVEL')
bv.width, bv.segments, bv.limit_method = 0.014, 4, 'ANGLE'
bv.angle_limit = math.radians(28)

# ---------- 底部青綠罩（解析邊界，無鋸齒）----------
TEAL_C, TEAL_R, TEAL_YK = Vector((0.0, -0.05, -0.17)), 0.580, 0.32
def tdist(p):
    d = p - TEAL_C
    return math.sqrt(d.x*d.x + (d.y*TEAL_YK)**2 + d.z*d.z)
def teal_z(t):
    lo, hi = 0.0, 1.40
    for _ in range(40):
        mid = (lo+hi)/2
        if tdist(sect_pt(t, mid)) < TEAL_R: lo = mid
        else: hi = mid
    return lo

bm = bmesh.new()
NS, NR = L(200), L(26, 6)
cols = []
for j in range(NS):
    t = TAU*j/NS
    zb = teal_z(t)
    col = []
    for i in range(NR+1):
        z = zb * (i/NR)
        p = sect_pt(t, z)
        c = Vector((0.0, y_off(z), z))
        r = (p - c)
        if r.length > 1e-6:
            p = c + r * (1.0 + 0.0038/r.length)
        col.append(bm.verts.new(p))
    cols.append(col)
for j in range(NS):
    k = (j+1) % NS
    for i in range(NR):
        bm.faces.new((cols[j][i], cols[k][i], cols[k][i+1], cols[j][i+1]))
me = bpy.data.meshes.new("TealM"); bm.to_mesh(me); bm.free()
teal = bpy.data.objects.new("TealBase", me); sc.collection.objects.link(teal)
teal.data.materials.append(M_TEAL)
smooth_obj(teal, 80)

# ---------- 貼合曲面的貼片 ----------
def wrap(ob, offset, front):
    for v in ob.data.vertices:
        y = surf_y(v.co.x, v.co.z, front)
        v.co.y = y - offset if front else y + offset
    ob.data.update()

def superellipse(n, pw):
    for i in range(n):
        t = TAU*i/n
        ct, st = math.cos(t), math.sin(t)
        yield (math.copysign(abs(ct)**(2.0/pw), ct),
               math.copysign(abs(st)**(2.0/pw), st))

def add_uv(ob, cx, cz, sx, sz):
    me = ob.data
    me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl[li].uv = ((co.x-cx)/(2*sx)+0.5, (co.z-cz)/(2*sz)+0.5)

def patch(name, cx, cz, sx, sz, front=True, offset=0.008,
          nseg=None, nring=None, pw=7.0, uv=False):
    nseg = L(nseg or 128); nring = L(nring or 18, 6)
    bm = bmesh.new()
    ctr = bm.verts.new((cx, 0.0, cz)); prev = None
    for r in range(1, nring+1):
        u = (r/nring)**0.72
        cur = [bm.verts.new((cx+u*sx*ex, 0.0, cz+u*sz*ez))
               for ex, ez in superellipse(nseg, pw)]
        if prev is None:
            for j in range(nseg):
                bm.faces.new((ctr, cur[j], cur[(j+1) % nseg]))
        else:
            for j in range(nseg):
                k = (j+1) % nseg
                bm.faces.new((prev[j], prev[k], cur[k], cur[j]))
        prev = cur
    me = bpy.data.meshes.new(name+"M"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    if uv: add_uv(ob, cx, cz, sx, sz)
    wrap(ob, offset, front)
    if not front: ob.data.flip_normals()
    smooth_obj(ob, 85)
    return ob

def ring_patch(name, cx, cz, sx, sz, thick, front=True, offset=0.006,
               nseg=None, pw=7.0):
    nseg = L(nseg or 160)
    bm = bmesh.new()
    inner = [bm.verts.new((cx+(sx-thick)*ex, 0.0, cz+(sz-thick)*ez))
             for ex, ez in superellipse(nseg, pw)]
    outer = [bm.verts.new((cx+sx*ex, 0.0, cz+sz*ez))
             for ex, ez in superellipse(nseg, pw)]
    for j in range(nseg):
        k = (j+1) % nseg
        bm.faces.new((inner[j], inner[k], outer[k], outer[j]))
    me = bpy.data.meshes.new(name+"M"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    wrap(ob, offset, front)
    if not front: ob.data.flip_normals()
    smooth_obj(ob, 85)
    return ob

# ---------- 螢幕 ----------
SC_CZ, SC_SX, SC_SZ = 1.160, 0.354, 0.548
bezel = patch("Bezel", 0.0, SC_CZ, SC_SX+0.022, SC_SZ+0.022,
              offset=0.006, pw=11.0, nseg=320, nring=26)
bezel.data.materials.append(M_BEZL)
screen = patch("Screen", 0.0, SC_CZ, SC_SX, SC_SZ,
               offset=0.013, pw=12.0, uv=True, nseg=320, nring=26)
screen.data.materials.append(M_SCR)

# ---------- 正面 HDRE ----------
bpy.ops.object.text_add(location=(0, 0, 0.497))
txt = bpy.context.object; txt.name = "HDRE"
txt.data.body = "HDRE"
txt.data.align_x = 'CENTER'; txt.data.align_y = 'CENTER'
txt.data.size = 0.125; txt.data.space_character = 1.80
txt.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.convert(target='MESH')
txt = bpy.context.object
bpy.ops.object.transform_apply(location=True, rotation=True)
wrap(txt, 0.010, True)
txt.data.materials.append(M_GLOW)

# ---------- 背面 ----------
up = patch("BackUpper", 0.0, 1.430, 0.330, 0.345, front=False,
           offset=0.004, pw=6.0)
up.data.materials.append(M_BACK)
lo = ring_patch("BackDoor", 0.0, 0.720, 0.330, 0.355, 0.015,
                front=False, offset=0.005, pw=6.0)
lo.data.materials.append(M_BACK)
led = patch("BackLED", 0.062, 0.700, 0.044, 0.120, front=False,
            offset=0.008, pw=5.0)
led.data.materials.append(M_GLOW)
dot = patch("BackDot", 0.066, 0.205, 0.046, 0.046, front=False,
            offset=0.010, pw=2.0)
dot.data.materials.append(M_DOT)

# ---------- 圓角方塊 ----------
def rbox(name, loc, size, bevel=0.012, seg=4):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.object; ob.name = name
    ob.scale = size; bpy.ops.object.transform_apply(scale=True)
    b = ob.modifiers.new("B", 'BEVEL')
    b.width, b.segments, b.limit_method = bevel, seg, 'ANGLE'
    b.angle_limit = math.radians(30)
    smooth_obj(ob, 45); return ob

# ---------- 頂部感測器 ----------
for nm, bx, bw, bd in (("SensL", -0.213, 0.068, 0.055),
                       ("SensR",  0.170, 0.052, 0.048)):
    rbox(nm+"Stem", (bx, -0.004, 1.900), (bw, bd, 0.076), 0.012
         ).data.materials.append(M_BODY)
    rbox(nm+"Cap", (bx, -0.004, 1.988), (bw*0.94, bd*0.94, 0.020), 0.009
         ).data.materials.append(M_TEAL)

# ---------- 側面凸片 ----------
TAB_Z, TAB_Y = 0.773, 0.240
for s in (-1, 1):
    a, b = half_w(TAB_Z), half_d(TAB_Z)
    r = min(1.0, abs(TAB_Y - y_off(TAB_Z))/b)
    xs = a * max(0.0, 1.0 - r**N_POW)**(1.0/N_POW)
    rbox("Tab%d" % s, (s*(xs+0.016), TAB_Y, TAB_Z),
         (0.028, 0.048, 0.155), 0.011).data.materials.append(M_TEAL)

# ---------- 側面喇叭 ----------
BTN_Z, BTN_Y = 0.730, 0.000
for s in (-1, 1):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=96, radius=0.104, depth=0.044,
        location=(s*(half_w(BTN_Z)-0.008), BTN_Y, BTN_Z),
        rotation=(0, math.radians(90), 0))
    cyl = bpy.context.object; cyl.name = "Speaker%d" % s
    b = cyl.modifiers.new("B", 'BEVEL')
    b.width, b.segments, b.limit_method = 0.012, 5, 'ANGLE'
    b.angle_limit = math.radians(30)
    smooth_obj(cyl, 45)
    cyl.data.materials.append(M_TEAL)

# ---------- 後仰 + 校正為 195 cm ----------
bpy.ops.object.empty_add(location=(0, 0, 0))
pivot = bpy.context.object; pivot.name = "Kiosk"
for ob in list(sc.objects):
    if ob is not pivot and ob.parent is None and ob.type == 'MESH':
        ob.parent = pivot
        ob.matrix_parent_inverse = pivot.matrix_world.inverted()
pivot.rotation_euler = (0, 0, 0)

sc.unit_settings.system = 'METRIC'
sc.unit_settings.length_unit = 'CENTIMETERS'
bpy.context.view_layer.update()

def bbox(objs):
    lo = Vector((1e9,)*3); hi = Vector((-1e9,)*3)
    for ob in objs:
        if ob.type != 'MESH': continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    return lo, hi

devs = [o for o in sc.objects if o.type == 'MESH']
lo, hi = bbox(devs)
k = 1.95 / (hi.z - lo.z)
pivot.scale = (k, k, k)
pivot.location.z = -lo.z * k
bpy.context.view_layer.update()

lo, hi = bbox(devs)
print("外框：寬 %.1f  深 %.1f  高 %.1f cm" %
      ((hi.x-lo.x)*100, (hi.y-lo.y)*100, (hi.z-lo.z)*100))
slo, shi = bbox([screen])
sw, sh = shi.x-slo.x, shi.z-slo.z
print("螢幕：%.1f x %.1f cm  對角 %.1f 吋  中心高 %.1f cm" %
      (sw*100, sh*100, math.hypot(sw, sh)/0.0254, (shi.z+slo.z)/2*100))
tlo, thi = bbox([teal])
print("青綠罩頂端高 %.1f cm | 喇叭中心高 %.1f cm" %
      (thi.z*100, (BTN_Z*k + pivot.location.z)*100))

# ---------- 人形比例尺 170 cm ----------
M_FIG = mat("Figure", srgb("70767A"), rough=0.88)
figp = []
def cap(name, loc, rad, depth, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=28, radius=rad, depth=depth,
                                        location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    b = o.modifiers.new("B", 'BEVEL')
    b.width, b.segments, b.limit_method = rad*0.72, 7, 'ANGLE'
    b.angle_limit = math.radians(30)
    smooth_obj(o, 55); figp.append(o); return o

cap("f_legL", (-0.092, 0.015, 0.430), 0.060, 0.860)
cap("f_legR", ( 0.098, -0.030, 0.430), 0.060, 0.860)
cap("f_hip",  (0, 0, 0.945), 0.138, 0.240)
cap("f_torso",(0, 0, 1.190), 0.152, 0.430)
cap("f_shldr",(0, 0, 1.372), 0.066, 0.350, rot=(0, math.radians(90), 0))
cap("f_armL", (-0.196, 0.015, 1.150), 0.047, 0.450)
cap("f_armR", ( 0.196, -0.078, 1.208), 0.047, 0.400, rot=(math.radians(30), 0, 0))
cap("f_fore", ( 0.196, -0.235, 1.262), 0.041, 0.290, rot=(math.radians(76), 0, 0))
cap("f_neck", (0, 0, 1.462), 0.051, 0.100)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24,
                                     radius=0.097, location=(0, -0.010, 1.592))
h = bpy.context.object; h.name = "f_head"
h.scale = (1.0, 1.10, 1.15); bpy.ops.object.transform_apply(scale=True)
smooth_obj(h, 60); figp.append(h)

bpy.ops.object.empty_add(location=(0.92, -1.00, 0))
figure = bpy.context.object; figure.name = "ScaleFigure"
for o in figp:
    o.data.materials.append(M_FIG)
    o.parent = figure
    o.matrix_parent_inverse = figure.matrix_world.inverted()
figure.rotation_euler = (0, 0, math.radians(-141))
bpy.context.view_layer.update()
flo, fhi = bbox(figp)
print("人形高 %.1f cm" % ((fhi.z-flo.z)*100))

# ---------- 場景 ----------
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
floor = bpy.context.object; floor.name = "Floor"
floor.data.materials.append(mat("FloorMat", srgb("DAD8D3"), rough=0.52))

world = bpy.data.worlds.new("World"); world.use_nodes = True
wn = world.node_tree.nodes["Background"]
wn.inputs["Color"].default_value = srgb("CFD5D9")
wn.inputs["Strength"].default_value = 0.38
sc.world = world

def area(name, loc, rot, energy, size, shape='SQUARE', sy=None):
    bpy.ops.object.light_add(type='AREA', location=loc, rotation=rot)
    L = bpy.context.object; L.name = name
    L.data.energy = energy; L.data.shape = shape; L.data.size = size
    if sy is not None: L.data.size_y = sy
    return L

area("Key",  ( 3.4, -4.0, 5.2), (math.radians(44), 0, math.radians(41)), 560, 4.0)
area("Fill", (-4.2, -2.4, 2.6), (math.radians(74), 0, math.radians(-58)), 210, 6.0)
area("Rim",  (-1.8,  4.2, 4.2), (math.radians(126), 0, math.radians(-158)), 300, 3.2)

def look_at(ob, tgt):
    ob.rotation_euler = (ob.location - Vector(tgt)).to_track_quat('Z', 'Y').to_euler()

def add_cam(name, loc, tgt, lens=None, ortho=None):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object; c.name = name
    if ortho is not None:
        c.data.type = 'ORTHO'; c.data.ortho_scale = ortho
    else:
        c.data.lens = lens
    look_at(c, tgt); return c

CAMS = [
    ("hero",  add_cam("CamHero",  (-2.62, -4.85, 1.72), (0.30, 0, 1.00), lens=55)),
    ("front", add_cam("CamFront", (0, -16, 0.975), (0, 0, 0.975), ortho=2.45)),
    ("side",  add_cam("CamSide",  (16, 0, 0.975), (0, 0, 0.975), ortho=2.45)),
    ("back",  add_cam("CamBack",  (0, 16, 0.975), (0, 0, 0.975), ortho=2.45)),
]

engines = sc.render.bl_rna.properties["engine"].enum_items.keys()
for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    if e in engines:
        sc.render.engine = e; break
sc.render.resolution_x, sc.render.resolution_y = 1150, 1500
sc.eevee.taa_render_samples = 64
for attr, val in (("use_raytracing", True), ("use_shadows", True)):
    try: setattr(sc.eevee, attr, val)
    except Exception: pass
sc.view_settings.view_transform = 'Standard'
try: sc.view_settings.look = 'None'
except Exception: pass
sc.view_settings.exposure = 0.0

sc.camera = CAMS[0][1]
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "hdre_kiosk.blend"))

if "--export" in sys.argv:
    # 只匯出機台本體（不含地板、人形）
    bpy.ops.object.select_all(action='DESELECT')
    for ob in sc.objects:
        if ob.type == 'MESH' and ob not in figp and ob.name != "Floor":
            ob.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, "hdre_kiosk.glb"),
        export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True)
    print("EXPORTED glb")

if "--render" in sys.argv:
    for tag, c in CAMS:
        sc.camera = c
        elev = (tag != "hero")
        for o in figp: o.hide_render = elev
        floor.hide_render = elev
        sc.render.film_transparent = elev
        sc.render.image_settings.color_mode = 'RGBA' if elev else 'RGB'
        sc.render.filepath = os.path.join(OUT, "hdre_%s.png" % tag)
        bpy.ops.render.render(write_still=True)
        print("RENDERED", tag)
print("BUILD OK | objects:", len(sc.objects))
