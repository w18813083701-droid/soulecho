from PIL import Image, ImageDraw, ImageFont
import io, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(os.path.join(BASE_DIR, "assets")):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(BASE_DIR, "assets")):
        BASE_DIR = os.getcwd()
FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "NotoSerifSC-Regular.ttf")
ITALIC_SHEAR = 0.22

def wrap_text(text, font, max_width, draw):
    lines, current = [], ""
    for char in text:
        test = current + char
        if draw.textbbox((0,0), test, font=font)[2] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines

def draw_italic_line(bg, text, font, x, y, color):
    d0 = ImageDraw.Draw(bg)
    bbox = d0.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    ew = int(th * ITALIC_SHEAR) + 4
    layer = Image.new("RGBA", (tw+ew+4, th+4), (0,0,0,0))
    ImageDraw.Draw(layer).text((-bbox[0]+2, -bbox[1]+2), text, font=font, fill=color)
    layer = layer.transform((tw+ew+4, th+4), Image.AFFINE,
        (1, -ITALIC_SHEAR, 0, 0, 1, 0), resample=Image.BICUBIC)
    bg.alpha_composite(layer, dest=(max(0,x-2), max(0,y-2)))

def _hint(draw, w, h, pad, username, font, color):
    text = "Soul Echo" + (f"  · {username}" if username else "")
    bw = draw.textbbox((0,0), text, font=font)[2]
    draw.text((w-pad-bw, h-int(h*0.05)), text, font=font, fill=color)

def _obsidian(bg, draw, w, h, pad, amber, user, uname):
    fq = ImageFont.truetype(FONT_PATH, int(w*0.030))
    fm = ImageFont.truetype(FONT_PATH, int(w*0.052))
    fh = ImageFont.truetype(FONT_PATH, int(w*0.024))
    lhq, lhm = int(w*0.030*2.0), int(w*0.052*1.85)
    ql = wrap_text(amber, fq, int(w*0.52), draw) if amber else []
    ml = wrap_text(user, fm, w-pad*2, draw)
    mt = len(ml)*lhm
    lt = 3; glb = int(h*0.022)
    bc = int(h*0.54) + (h-int(h*0.54))//2
    my = bc - mt//2
    ly = my + mt + glb
    if ql:
        y = int(h*0.44)
        for line in ql:
            bw = draw.textbbox((0,0), line, font=fq)[2]
            draw_italic_line(bg, line, fq, w-pad-bw, y, (210,210,210,160))
            draw = ImageDraw.Draw(bg); y += lhq
    y = my
    for line in ml:
        bw = draw.textbbox((0,0), line, font=fm)[2]
        draw.text(((w-bw)//2, y), line, font=fm, fill=(240,240,240,255)); y += lhm
    cx=w//2; lx0=cx-int(w*0.11); lx1=cx+int(w*0.11); r=lt//2
    draw.line([(lx0,ly),(lx1,ly)], fill=(140,20,20,255), width=lt)
    draw.ellipse([(lx0-r,ly-r),(lx0+r,ly+r)], fill=(140,20,20,255))
    draw.ellipse([(lx1-r,ly-r),(lx1+r,ly+r)], fill=(140,20,20,255))
    _hint(draw, w, h, pad, uname, fh, (255,255,255,50))

def _white(bg, draw, w, h, pad, amber, user, uname):
    fq = ImageFont.truetype(FONT_PATH, int(w*0.030))
    fm = ImageFont.truetype(FONT_PATH, int(w*0.048))
    fh = ImageFont.truetype(FONT_PATH, int(w*0.024))
    lhq, lhm = int(w*0.030*2.0), int(w*0.048*1.85)
    mw = w - pad*2
    ql = wrap_text(amber, fq, mw, draw) if amber else []
    ml = wrap_text(user, fm, mw, draw)
    if ql:
        y = int(h*0.38)
        for line in ql:
            bw = draw.textbbox((0,0), line, font=fq)[2]
            draw_italic_line(bg, line, fq, (w-bw)//2, y, (60,60,60,170))
            draw = ImageDraw.Draw(bg); y += lhq
    y = int(h*0.72)
    for line in ml:
        bw = draw.textbbox((0,0), line, font=fm)[2]
        draw.text(((w-bw)//2, y), line, font=fm, fill=(30,30,30,255)); y += lhm
    _hint(draw, w, h, pad, uname, fh, (20,20,20,255))

def _cinema(bg, draw, w, h, pad, amber, user, uname):
    lo       = int(w * 0.22)
    mw_quote = int(w * 0.50)
    mw_main  = int(w * 0.52)
    right_edge = w - int(w * 0.08)

    fq = ImageFont.truetype(FONT_PATH, int(w*0.028))
    fm = ImageFont.truetype(FONT_PATH, int(w*0.044))
    fh = ImageFont.truetype(FONT_PATH, int(w*0.024))
    lhq = int(w*0.028*2.0)
    lhm = int(w*0.044*1.85)

    ql = wrap_text(amber, fq, mw_quote, draw) if amber else []
    ml = wrap_text(user,  fm, mw_main,  draw)

    quote_start = int(h * 0.54)
    main_y = quote_start + len(ql)*lhq + int(h*0.07)

    if ql:
        y = quote_start
        for line in ql:
            bw = draw.textbbox((0,0), line, font=fq)[2]
            draw_italic_line(bg, line, fq, right_edge-bw, y, (200,200,200,160))
            draw = ImageDraw.Draw(bg)
            y += lhq

    y = main_y
    inner_w = w - lo - int(w*0.08)
    for line in ml:
        bw = draw.textbbox((0,0), line, font=fm)[2]
        draw.text((lo + (inner_w-bw)//2, y), line, font=fm, fill=(235,235,235,255))
        y += lhm

    _hint(draw, w, h, int(w*0.08), uname, fh, (255,255,255,50))

def generate_share_card(user_sentence, amber_sentence="", username="", template="obsidian"):
    paths = {
        "obsidian": os.path.join(BASE_DIR, "assets", "黑曜石（无字）.png"),
        "white":    os.path.join(BASE_DIR, "assets", "白（无字）.png"),
        "cinema":   os.path.join(BASE_DIR, "assets", "电影（无字）.png"),
    }
    bg = Image.open(paths[template]).convert("RGBA")
    if max(bg.size) > 800:
        r = 800/max(bg.size)
        bg = bg.resize((int(bg.width*r), int(bg.height*r)), Image.LANCZOS)
    w, h = bg.size
    draw = ImageDraw.Draw(bg)
    pad = int(w*0.11)
    {"obsidian": _obsidian, "white": _white, "cinema": _cinema}[template](
        bg, draw, w, h, pad, amber_sentence, user_sentence, username)
    buf = io.BytesIO()
    bg = bg.convert("RGB")
    bg.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()