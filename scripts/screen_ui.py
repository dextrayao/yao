"""產生導覽系統螢幕 UI 貼圖"""
from PIL import Image, ImageDraw, ImageFont
import glob, os

W, H = 1000, 2085
BG      = (18, 21, 24)
PANEL   = (28, 34, 38)
PANEL2  = (36, 44, 49)
TEAL    = (26, 165, 190)
CYAN    = (43, 233, 228)
GREEN   = (165, 211, 98)
WHITE   = (238, 242, 244)
GREY    = (126, 138, 145)

def font(paths, size):
    for p in paths:
        for f in glob.glob(p):
            if os.path.exists(f):
                try:
                    return ImageFont.truetype(f, size)
                except Exception:
                    pass
    return ImageFont.load_default()

DJ_B = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
DJ_R = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
CJK  = ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/*.tt*",
        "/usr/share/fonts/opentype/noto/NotoSansCJK*.ttc",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"]

f_logo  = font(DJ_B, 62)
f_h1    = font(DJ_B, 58)
f_h2    = font(DJ_R, 30)
f_row   = font(DJ_B, 40)
f_sub   = font(DJ_R, 26)
f_small = font(DJ_R, 28)
f_cjk   = font(CJK, 40)
f_cjk_s = font(CJK, 28)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

def rrect(box, r, fill=None, outline=None, width=3):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def spaced(draw, xy, text, fnt, fill, gap=14, anchor_mid=False):
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + gap*(len(text)-1)
    x, y = xy
    if anchor_mid:
        x -= total/2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill)
        x += w + gap
    return total

# ---- 頂欄 ----
d.rectangle([0, 0, W, 148], fill=(13, 16, 18))
spaced(d, (56, 44), "HDRE", f_logo, CYAN, gap=16)
d.text((W-56, 62), "09:42", font=f_small, fill=GREY, anchor="ra")
d.rectangle([0, 146, W, 150], fill=TEAL)

# ---- 標題 ----
d.text((56, 196), "FLOOR DIRECTORY", font=f_h1, fill=WHITE)
d.text((58, 268), "樓層導覽", font=f_cjk, fill=TEAL)

# ---- 地圖面板 ----
MX0, MY0, MX1, MY1 = 56, 350, W-56, 1180
rrect([MX0, MY0, MX1, MY1], 26, fill=PANEL)
rrect([MX0, MY0, MX1, MY1], 26, outline=(52, 62, 68), width=3)

blocks = [
    (100, 405, 330, 610, PANEL2), (350, 405, 560, 545, PANEL2),
    (580, 405, 890, 560, (34, 60, 66)), (100, 640, 300, 830, PANEL2),
    (330, 580, 560, 830, (30, 52, 58)), (600, 590, 890, 790, PANEL2),
    (100, 860, 420, 1050, PANEL2), (450, 860, 700, 1010, PANEL2),
    (730, 820, 890, 1090, (34, 60, 66)),
]
for x0, y0, x1, y1, c in blocks:
    rrect([x0, y0, x1, y1], 10, fill=c)

# 動線
route = [(215, 1090), (215, 900), (470, 900), (470, 700), (700, 700), (700, 500)]
for i in range(len(route)-1):
    d.line([route[i], route[i+1]], fill=CYAN, width=9)
for p in route[1:-1]:
    d.ellipse([p[0]-9, p[1]-9, p[0]+9, p[1]+9], fill=CYAN)

# 起點
sx, sy = route[0]
d.ellipse([sx-26, sy-26, sx+26, sy+26], outline=GREEN, width=6)
d.ellipse([sx-11, sy-11, sx+11, sy+11], fill=GREEN)
d.text((sx+42, sy-18), "YOU ARE HERE", font=f_sub, fill=GREEN)

# 終點圖釘
ex, ey = route[-1]
d.ellipse([ex-30, ey-30, ex+30, ey+30], fill=CYAN)
d.polygon([(ex-19, ey+14), (ex+19, ey+14), (ex, ey+52)], fill=CYAN)
d.ellipse([ex-11, ey-11, ex+11, ey+11], fill=PANEL)

d.text((MX0+30, MY1-58), "3F  ·  EAST WING", font=f_small, fill=GREY)

# ---- 清單 ----
rows = [("01", "INFORMATION", "服務台"), ("02", "GALLERY  A", "展覽廳 A"),
        ("03", "AUDITORIUM", "國際會議廳"), ("04", "RESTROOM", "洗手間"),
        ("05", "ELEVATOR", "電梯")]
y = 1206
for i, (num, en, zh) in enumerate(rows):
    hi = (i == 1)
    rrect([56, y, W-56, y+118], 16,
          fill=(30, 48, 54) if hi else (24, 28, 32))
    if hi:
        d.rectangle([56, y+16, 62, y+102], fill=CYAN)
    rrect([84, y+30, 148, y+88], 12, fill=TEAL if hi else (44, 52, 58))
    d.text((116, y+42), num, font=f_sub, fill=WHITE, anchor="ma")
    d.text((176, y+26), en, font=f_row, fill=WHITE if hi else (196, 204, 210))
    d.text((178, y+74), zh, font=f_cjk_s, fill=CYAN if hi else GREY)
    d.text((W-104, y+40), "›", font=f_row, fill=TEAL if hi else GREY)
    y += 128

# ---- 底部按鈕 ----
BY = H - 208
rrect([56, BY, W//2-14, BY+128], 18, fill=TEAL)
d.text((W//4+8, BY+30), "SEARCH", font=f_row, fill=(12, 20, 24), anchor="ma")
d.text((W//4+8, BY+80), "搜尋", font=f_cjk_s, fill=(16, 40, 48), anchor="ma")
rrect([W//2+14, BY, W-56, BY+128], 18, outline=TEAL, width=4)
d.text((3*W//4-8, BY+30), "LANGUAGE", font=f_row, fill=WHITE, anchor="ma")
d.text((3*W//4-8, BY+80), "語言", font=f_cjk_s, fill=TEAL, anchor="ma")

img.save("/home/user/yao/out/screen_ui.png")
print("UI OK", img.size)
