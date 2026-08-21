"""草圖上的螢幕：深灰玻璃 + 兩道斜向反光"""
from PIL import Image, ImageDraw, ImageFilter
W, H = 900, 1390                      # 依實際螢幕比例
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img)
# 上亮下暗的底
for y in range(H):
    t = y / H
    v = int(116 - 74*t)
    d.line([(0, y), (W, y)], fill=(v, v+2, v+4))
# 兩道斜向反光（左下往右上）
band = Image.new("RGB", (W, H), (0, 0, 0))
bd = ImageDraw.Draw(band)
for x0, wdt in ((-260, 96), (-40, 46)):
    bd.polygon([(x0, H), (x0+wdt, H), (x0+wdt+H*0.72, 0), (x0+H*0.72, 0)],
               fill=(150, 154, 158))
band = band.filter(ImageFilter.GaussianBlur(7))
img = Image.blend(img, Image.blend(img, band, 1.0), 0.0)
px, bx = img.load(), band.load()
for y in range(H):
    for x in range(W):
        b = bx[x, y][0]
        if b:
            p = px[x, y]
            k = b / 255.0 * 0.62
            px[x, y] = (min(255, int(p[0]+ (200-p[0])*k)),
                        min(255, int(p[1]+ (204-p[1])*k)),
                        min(255, int(p[2]+ (208-p[2])*k)))
img.save("/home/user/yao/out/screen_glass.png")
print("GLASS OK", img.size)
