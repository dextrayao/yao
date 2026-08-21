"""把 three.js + GLB 打包成單一自帶檔案的檢視頁"""
import base64, pathlib, subprocess, tarfile, shutil, tempfile, os

OUT = pathlib.Path(__file__).resolve().parent.parent
VENDOR = OUT/"vendor/three-0.137.5"
THREE_VER = "three@0.137.5"


def ensure_three():
    """首次執行時從 npm registry 取得 three.js（r137 仍提供 UMD 版）"""
    if (VENDOR/"build/three.min.js").exists():
        return VENDOR
    VENDOR.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["npm", "pack", THREE_VER, "--silent"],
                       cwd=td, check=True)
        tgz = next(pathlib.Path(td).glob("three-*.tgz"))
        with tarfile.open(tgz) as t:
            t.extractall(td)
        shutil.move(str(pathlib.Path(td)/"package"), str(VENDOR))
    return VENDOR


SP = ensure_three()

three = (SP/"build/three.min.js").read_text()
libs  = "\n".join((SP/f"examples/js/{f}").read_text() for f in (
    "controls/OrbitControls.js",
    "loaders/GLTFLoader.js",
    "environments/RoomEnvironment.js"))
glb64 = base64.b64encode((OUT/"out/hdre_kiosk_web.glb").read_bytes()).decode()

SPECS = [("總高", "195.0", "cm"), ("寬", "89.9", "cm"), ("深", "69.5", "cm"),
         ("螢幕", "68.8 × 106.4", "cm"), ("螢幕對角", "49.9", "in"),
         ("螢幕中心高", "112.6", "cm"), ("正面傾角", "5.0", "°"),
         ("背面傾角", "10.2", "°")]
spec_rows = "\n".join(
    f'<div class="spec"><dt>{k}</dt><dd>{v}<span class="u">{u}</span></dd></div>'
    for k, v, u in SPECS)

VIEWS = [("iso", "45°"), ("front", "正面"), ("side", "側面"),
         ("back", "背面"), ("top", "頂視")]
view_btns = "\n".join(
    f'<button class="vbtn{" is-on" if k=="iso" else ""}" data-view="{k}" '
    f'type="button">{lab}</button>' for k, lab in VIEWS)

HTML = f"""<title>HDRE 導覽系統</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700&display=swap">
<style>
:root {{
  --paper:#EFEEE8; --stage:#E4E3DB; --ink:#191D1F; --ink-2:#5C6560;
  --line:#D3D2C9; --panel:#FBFAF6; --panel-edge:#DCDBD2;
  --accent:#0F7F95; --accent-ink:#FFFFFF; --product:#7BA92F;
  --shadow:0 1px 2px rgba(25,29,31,.07), 0 8px 24px rgba(25,29,31,.10);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --paper:#101416; --stage:#171C1F; --ink:#E7EBE9; --ink-2:#93A09A;
    --line:#252C2F; --panel:#181E21; --panel-edge:#2A3236;
    --accent:#2FC3DC; --accent-ink:#08191D; --product:#A5D362;
    --shadow:0 1px 2px rgba(0,0,0,.5), 0 10px 30px rgba(0,0,0,.45);
  }}
}}
:root[data-theme="dark"] {{
  --paper:#101416; --stage:#171C1F; --ink:#E7EBE9; --ink-2:#93A09A;
  --line:#252C2F; --panel:#181E21; --panel-edge:#2A3236;
  --accent:#2FC3DC; --accent-ink:#08191D; --product:#A5D362;
  --shadow:0 1px 2px rgba(0,0,0,.5), 0 10px 30px rgba(0,0,0,.45);
}}
* {{ box-sizing:border-box; }}
html, body {{ height:100%; }}
body {{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"IBM Plex Sans","Noto Sans TC",system-ui,sans-serif;
  overflow:hidden;
}}
#app {{ position:fixed; inset:0; display:grid; grid-template-rows:auto 1fr; }}

header {{
  display:flex; align-items:baseline; gap:.85rem; flex-wrap:wrap;
  padding:.85rem clamp(.9rem,3vw,1.6rem);
  border-bottom:1px solid var(--line); background:var(--paper);
  position:relative; z-index:2;
}}
h1 {{
  margin:0; font-family:Archivo,"Noto Sans TC",system-ui,sans-serif;
  font-weight:700; font-size:clamp(1rem,2.4vw,1.2rem); letter-spacing:-.01em;
}}
.tag {{
  font-family:"IBM Plex Mono",monospace; font-size:.72rem; font-weight:500;
  letter-spacing:.06em; text-transform:uppercase;
  color:var(--accent); border:1px solid currentColor;
  padding:.16rem .45rem; border-radius:2px;
}}
.sub {{ margin:0; color:var(--ink-2); font-size:.82rem; margin-left:auto; }}

#stage {{ position:relative; background:var(--stage); min-height:0; }}
canvas {{ display:block; width:100%; height:100%; touch-action:none; }}

.rail {{
  position:absolute; left:clamp(.7rem,2.5vw,1.3rem);
  bottom:clamp(.7rem,2.5vw,1.3rem);
  display:flex; gap:.3rem; flex-wrap:wrap; align-items:center;
  background:var(--panel); border:1px solid var(--panel-edge);
  border-radius:5px; padding:.3rem; box-shadow:var(--shadow);
}}
.vbtn, .tbtn {{
  font:inherit; font-size:.8rem; font-weight:500; color:var(--ink-2);
  background:transparent; border:0; border-radius:3px;
  padding:.4rem .62rem; cursor:pointer; white-space:nowrap;
}}
.vbtn:hover, .tbtn:hover {{ background:var(--stage); color:var(--ink); }}
.vbtn.is-on {{ background:var(--accent); color:var(--accent-ink); }}
.tbtn.is-on {{ color:var(--accent); }}
.sep {{ width:1px; align-self:stretch; background:var(--panel-edge); margin:.15rem .18rem; }}
:is(.vbtn,.tbtn):focus-visible {{ outline:2px solid var(--accent); outline-offset:1px; }}

.specs {{
  position:absolute; right:clamp(.7rem,2.5vw,1.3rem);
  top:clamp(.7rem,2.5vw,1.3rem);
  margin:0; width:min(15rem,42vw); max-height:calc(100% - 2.6rem);
  overflow-y:auto;
  background:var(--panel); border:1px solid var(--panel-edge);
  border-radius:5px; padding:.55rem .7rem; box-shadow:var(--shadow);
}}
.specs h2 {{
  margin:0 0 .4rem; font-family:Archivo,sans-serif; font-size:.66rem;
  font-weight:600; letter-spacing:.1em; text-transform:uppercase;
  color:var(--ink-2);
}}
.spec {{
  display:flex; justify-content:space-between; align-items:baseline;
  gap:.6rem; padding:.24rem 0; border-top:1px solid var(--line);
}}
.spec dt {{ font-size:.78rem; color:var(--ink-2); }}
.spec dd {{
  margin:0; font-family:"IBM Plex Mono",monospace; font-size:.82rem;
  font-weight:500; font-variant-numeric:tabular-nums; text-align:right;
}}
.u {{ color:var(--ink-2); font-size:.72rem; margin-left:.15em; }}

#hint {{
  position:absolute; left:50%; bottom:clamp(.7rem,2.5vw,1.3rem);
  transform:translateX(-50%); color:var(--ink-2); font-size:.76rem;
  pointer-events:none; transition:opacity .5s;
}}
#load {{
  position:absolute; inset:0; display:grid; place-items:center;
  background:var(--stage); color:var(--ink-2); font-size:.85rem;
  font-family:"IBM Plex Mono",monospace; letter-spacing:.05em;
}}
@media (max-width:640px) {{
  .specs {{ display:none; }}
  .sub {{ display:none; }}
}}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; }} }}
</style>

<div id="app">
  <header>
    <h1>HDRE 導覽系統</h1>
    <span class="tag">195 cm</span>
    <p class="sub">拖曳旋轉 · 滾輪縮放 · 右鍵平移</p>
  </header>
  <div id="stage">
    <div id="load">載入模型…</div>
    <dl class="specs">
      <h2>尺寸</h2>
      {spec_rows}
    </dl>
    <div class="rail">
      {view_btns}
      <span class="sep"></span>
      <button class="tbtn" id="spin" type="button">自動旋轉</button>
    </div>
    <div id="hint"></div>
  </div>
</div>

<script>{three}</script>
<script>{libs}</script>
<script>
(function () {{
  var GLB = "{glb64}";
  var stage = document.getElementById('stage');
  var loadEl = document.getElementById('load');
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  var renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  stage.appendChild(renderer.domElement);

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(38, 1, 0.05, 100);
  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.075;
  controls.minDistance = 1.2;
  controls.maxDistance = 14;
  controls.maxPolarAngle = Math.PI * 0.52;
  controls.autoRotateSpeed = 1.1;

  var pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new THREE.RoomEnvironment(), 0.04).texture;

  var key = new THREE.DirectionalLight(0xffffff, 2.0);
  key.position.set(2.6, 4.2, 3.0);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -2; key.shadow.camera.right = 2;
  key.shadow.camera.top = 3; key.shadow.camera.bottom = -1;
  key.shadow.bias = -0.0009;
  scene.add(key);
  scene.add(new THREE.DirectionalLight(0xffffff, 0.5).translateX(-3));
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8f88, 0.55));

  var ground = new THREE.Mesh(
    new THREE.CircleGeometry(9, 64).rotateX(-Math.PI / 2),
    new THREE.ShadowMaterial({{ opacity: 0.17 }}));
  ground.receiveShadow = true;
  scene.add(ground);

  var css = getComputedStyle(document.documentElement);
  function paint() {{
    var c = getComputedStyle(document.documentElement)
              .getPropertyValue('--stage').trim();
    if (c) renderer.setClearColor(new THREE.Color(c), 1);
  }}
  paint();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', paint);
  new MutationObserver(paint).observe(document.documentElement,
    {{ attributes: true, attributeFilter: ['data-theme'] }});

  function resize() {{
    var w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }}
  addEventListener('resize', resize);

  var HEIGHT = 1.95, radius = 1.6, center = new THREE.Vector3(0, 0.95, 0);

  function b64ToBuf(s) {{
    var bin = atob(s), n = bin.length, u = new Uint8Array(n);
    for (var i = 0; i < n; i++) u[i] = bin.charCodeAt(i);
    return u.buffer;
  }}

  var VIEWS = {{
    iso:   [ -1.05, 0.42,  1.00 ],
    front: [  0.00, 0.05,  1.00 ],
    side:  [  1.00, 0.05,  0.00 ],
    back:  [  0.00, 0.05, -1.00 ],
    top:   [ -0.35, 1.15,  0.55 ]
  }};
  function goto(k) {{
    var v = VIEWS[k] || VIEWS.iso;
    var d = new THREE.Vector3(v[0], v[1], v[2]).normalize();
    var dist = (k === 'top') ? radius * 3.0 : radius * 3.3;
    camera.position.copy(center).addScaledVector(d, dist);
    controls.target.copy(center);
    controls.update();
  }}

  new THREE.GLTFLoader().parse(b64ToBuf(GLB), '', function (gltf) {{
    var m = gltf.scene;
    m.traverse(function (o) {{
      if (o.isMesh) {{ o.castShadow = true; o.receiveShadow = true; }}
    }});
    var box = new THREE.Box3().setFromObject(m);
    var size = box.getSize(new THREE.Vector3());
    m.scale.setScalar(HEIGHT / size.y);
    box.setFromObject(m);
    var c = box.getCenter(new THREE.Vector3());
    m.position.sub(new THREE.Vector3(c.x, box.min.y, c.z));
    box.setFromObject(m);
    box.getCenter(center);
    radius = box.getSize(new THREE.Vector3()).length() * 0.5;
    scene.add(m);
    resize(); goto('iso');
    loadEl.remove();
    var hint = document.getElementById('hint');
    hint.textContent = '拖曳即可自由檢視';
    setTimeout(function () {{ hint.style.opacity = 0; }}, 3600);
  }}, function (e) {{ loadEl.textContent = '模型載入失敗'; console.error(e); }});

  document.querySelectorAll('.vbtn').forEach(function (b) {{
    b.addEventListener('click', function () {{
      document.querySelectorAll('.vbtn').forEach(function (o) {{
        o.classList.toggle('is-on', o === b);
      }});
      goto(b.dataset.view);
    }});
  }});
  var spin = document.getElementById('spin');
  spin.addEventListener('click', function () {{
    controls.autoRotate = !controls.autoRotate;
    spin.classList.toggle('is-on', controls.autoRotate);
  }});
  controls.addEventListener('start', function () {{
    document.querySelectorAll('.vbtn').forEach(function (o) {{
      o.classList.remove('is-on');
    }});
  }});

  (function loop() {{
    requestAnimationFrame(loop);
    controls.update();
    renderer.render(scene, camera);
  }})();
  resize();
}})();
</script>
"""
dest = OUT/"viewer/hdre_viewer.html"
dest.write_text(HTML)
print("VIEWER OK  %.2f MB" % (dest.stat().st_size/1048576))
