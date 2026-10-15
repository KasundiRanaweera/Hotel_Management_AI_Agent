import sys, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
S = 2
OUT = os.path.dirname(os.path.abspath(__file__))
FD = 'C:/Windows/Fonts/'
_fc = {}


def F(sz, w='r'):
    k = (sz, w)
    if k not in _fc:
        name = {'r': 'segoeui.ttf', 'b': 'segoeuib.ttf', 'sb': 'seguisb.ttf', 'm': 'consola.ttf'}[w]
        _fc[k] = ImageFont.truetype(FD + name, int(sz * S))
    return _fc[k]


BG = (13, 14, 18)
ORANGE = (249, 115, 22)
WHITE = (245, 245, 247)
MUTE = (148, 152, 165)
INK = (39, 39, 42)
GRID = (229, 231, 235)
# Gradio default theme bubble colours
U_FILL, U_LINE = (255, 247, 237), (253, 215, 170)
A_FILL, A_LINE = (249, 250, 251), (229, 231, 235)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def seg(t, a, b):
    return clamp((t - a) / (b - a))


_bg = None


def bg():
    global _bg
    if _bg is None:
        y, x = np.mgrid[0:H * S, 0:W * S].astype(np.float32) / S
        d1 = np.sqrt(((x - 260) / 1100) ** 2 + ((y - 1020) / 680) ** 2)
        d2 = np.sqrt(((x - 1500) / 900) ** 2 + ((y + 80) / 500) ** 2)
        g1 = np.clip(1 - d1, 0, 1) ** 2
        g2 = np.clip(1 - d2, 0, 1) ** 2
        arr = np.zeros((H * S, W * S, 3), np.float32) + np.array(BG, np.float32)
        arr += g1[..., None] * np.array([78, 32, 6], np.float32)
        arr += g2[..., None] * np.array([18, 18, 26], np.float32)
        _bg = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert('RGBA')
    return _bg.copy()


def new(w, h):
    return Image.new('RGBA', (int(round(w * S)), int(round(h * S))), (0, 0, 0, 0))


def comp(base, layer, x, y, alpha=1.0):
    if alpha <= 0.002:
        return
    l = layer
    if alpha < 0.998:
        l = layer.copy()
        l.putalpha(layer.getchannel('A').point(lambda v: int(v * alpha)))
    base.alpha_composite(l, (int(round(x * S)), int(round(y * S))))


_tl = {}


def text_layer(txt, font, fill):
    k = (txt, id(font), fill)
    if k not in _tl:
        w = font.getlength(txt) / S + 8
        im = new(w, font.size / S * 1.45)
        ImageDraw.Draw(im).text((0, 0), txt, font=font, fill=fill)
        _tl[k] = im
    return _tl[k]


def centered(base, txt, font, fill, y, a=1.0, dy=0.0):
    comp(base, text_layer(txt, font, fill), (W - font.getlength(txt) / S) / 2, y + dy, a)


# ---------- rich chat bubbles (markdown as Gradio renders it) ----------
FS, LH, PAD = 27, 40, 20


def sf(st):
    return F(FS, 'b') if st == 'b' else F(FS)


def units_of(segs):
    """Split styled segments into unbreakable word units (punctuation glued to the word before it)."""
    units, space = [], True
    for text, st in segs:
        for j, p in enumerate(text.split(' ')):
            if j > 0:
                space = True
            if p == '':
                continue
            if space or not units:
                units.append([(p, st)])
            else:
                units[-1].append((p, st))
            space = False
    return units


def uw(u):
    return sum(sf(st).getlength(w) for w, st in u) / S


SP = None


def wrap_units(units, maxw):
    sp = F(FS).getlength(' ') / S
    lines, cur, cw = [], [], 0
    for u in units:
        w = uw(u)
        if cur and cw + sp + w > maxw:
            lines.append((cur, cw))
            cur, cw = [u], w
        else:
            cw = cw + (sp if cur else 0) + w
            cur.append(u)
    if cur:
        lines.append((cur, cw))
    return lines


def draw_line(d, x, y, line):
    sp = F(FS).getlength(' ')
    xs = x * S
    for i, u in enumerate(line):
        if i:
            xs += sp
        for w, st in u:
            f = sf(st)
            d.text((xs, y * S), w, font=f, fill=INK)
            xs += f.getlength(w)


_bc = {}


def bubble(kind, content, maxw=640):
    key = (kind, repr(content), maxw)
    if key in _bc:
        return _bc[key]
    blocks = [('p', [(content, 'r')])] if isinstance(content, str) else content
    ops, y, wmax = [], PAD - 4, 0
    for b in blocks:
        t = b[0]
        if t == 'p':
            for line, lw in wrap_units(units_of(b[1]), maxw):
                ops.append(('line', PAD, y, line))
                wmax = max(wmax, PAD + lw)
                y += LH
            y += 8
        elif t in ('li', 'ol'):
            ind = 36
            if t == 'li':
                ops.append(('dot', PAD + 16, y + 21))
            else:
                ops.append(('txt', PAD + 2, y, str(b[1]) + '.', F(FS)))
            for line, lw in wrap_units(units_of(b[-1]), maxw - ind):
                ops.append(('line', PAD + ind, y, line))
                wmax = max(wmax, PAD + ind + lw)
                y += LH
            y += 6
        elif t == 'code':
            fb, fm = F(FS, 'b'), F(21, 'm')
            lw = fb.getlength(b[1] + ' ') / S
            ops.append(('txt', PAD, y, b[1], fb))
            cw = fm.getlength(b[2]) / S + 18
            ops.append(('codebox', PAD + lw, y + 4, cw, 36, b[2]))
            wmax = max(wmax, PAD + lw + cw)
            y += LH + 8
        elif t == 'table':
            ft, ftb = F(23), F(23, 'b')
            hdr, rows = b[1], b[2]
            cols = [max(ftb.getlength(hdr[c]), *(ft.getlength(r[c]) for r in rows)) / S + 28 for c in range(len(hdr))]
            ops.append(('table', PAD, y + 4, cols, hdr, rows))
            rh = 46
            wmax = max(wmax, PAD + sum(cols))
            y += rh * (len(rows) + 1) + 18
    h = y - 8 + PAD
    w = wmax + PAD
    im = new(w, h)
    d = ImageDraw.Draw(im)
    fill, line = (U_FILL, U_LINE) if kind == 'user' else (A_FILL, A_LINE)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=12 * S, fill=fill, outline=line, width=2)
    for op in ops:
        if op[0] == 'line':
            draw_line(d, op[1], op[2], op[3])
        elif op[0] == 'dot':
            cx, cy = op[1] * S, op[2] * S
            d.ellipse((cx - 5 * S, cy - 5 * S, cx + 5 * S, cy + 5 * S), outline=INK, width=int(1.6 * S))
        elif op[0] == 'txt':
            d.text((op[1] * S, op[2] * S), op[3], font=op[4], fill=INK)
        elif op[0] == 'codebox':
            _, x, yy, cw, ch, txt = op
            d.rounded_rectangle((x * S, yy * S, (x + cw) * S, (yy + ch) * S), radius=5 * S, fill=(243, 244, 246), outline=GRID, width=2)
            d.text(((x + 9) * S, (yy + 7) * S), txt, font=F(21, 'm'), fill=INK)
        elif op[0] == 'table':
            _, x0, y0, cols, hdr, rows = op
            ft, ftb = F(23), F(23, 'b')
            rh = 46
            tw = sum(cols)
            th = rh * (len(rows) + 1)
            d.rectangle((x0 * S, y0 * S, (x0 + tw) * S, (y0 + th) * S), outline=GRID, width=2)
            for r in range(1, len(rows) + 1):
                d.line((x0 * S, (y0 + r * rh) * S, (x0 + tw) * S, (y0 + r * rh) * S), fill=GRID, width=2)
            x = x0
            for c, cwid in enumerate(cols):
                if c:
                    d.line((x * S, y0 * S, x * S, (y0 + th) * S), fill=GRID, width=2)
                d.text(((x + 14) * S, (y0 + 8) * S), hdr[c], font=ftb, fill=INK)
                for r, row in enumerate(rows):
                    d.text(((x + 14) * S, (y0 + (r + 1) * rh + 8) * S), row[c], font=ft, fill=INK)
                x += cwid
    _bc[key] = im
    return im


def sys_layer(txt):
    key = ('sys', txt)
    if key not in _bc:
        w = MSG_X1 - MSG_X0
        im = new(w, 40)
        d = ImageDraw.Draw(im)
        f = F(21, 'sb')
        tw = f.getlength(txt) / S
        cx = w / 2
        d.text(((cx - tw / 2) * S, 6 * S), txt, font=f, fill=(150, 154, 165))
        for x0, x1 in ((40, cx - tw / 2 - 20), (cx + tw / 2 + 20, w - 40)):
            d.line((x0 * S, 21 * S, x1 * S, 21 * S), fill=GRID, width=2)
        _bc[key] = im
    return _bc[key]


# ---------- Gradio-style window ----------
CX0, CY0, CX1, CY1 = 800, 60, 1860, 1020
_card = None


def card_layer():
    global _card
    if _card is not None:
        return _card
    w, h = CX1 - CX0, CY1 - CY0
    pad = 60
    im = new(w + 2 * pad, h + 2 * pad)
    sh = new(w + 2 * pad, h + 2 * pad)
    ImageDraw.Draw(sh).rounded_rectangle((pad * S, (pad + 18) * S, (pad + w) * S, (pad + h + 18) * S), radius=22 * S, fill=(0, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(30 * S)))
    d = ImageDraw.Draw(im)
    o = pad
    d.rounded_rectangle((o * S, o * S, (o + w) * S, (o + h) * S), radius=22 * S, fill=(255, 255, 255))
    px0, py0, px1, py1 = o + 24, o + 24, o + w - 24, o + h - 160
    d.rounded_rectangle((px0 * S, py0 * S, px1 * S, py1 * S), radius=10 * S, fill=(255, 255, 255), outline=GRID, width=2)
    iy0, iy1 = py1 + 22, py1 + 92
    d.rounded_rectangle((px0 * S, iy0 * S, px1 * S, iy1 * S), radius=10 * S, fill=(255, 255, 255), outline=GRID, width=2)
    cx, cy = (px1 - 40) * S, (iy0 + 35) * S
    d.ellipse((cx - 22 * S, cy - 22 * S, cx + 22 * S, cy + 22 * S), fill=(243, 244, 246))
    d.polygon([(cx - 9 * S, cy - 10 * S), (cx + 11 * S, cy), (cx - 9 * S, cy + 10 * S), (cx - 5 * S, cy)], outline=(70, 74, 85), width=int(1.8 * S))
    ft = F(19)
    foot = 'Use via API   \u00b7   Built with Gradio   \u00b7   Settings'
    d.text(((o + w / 2) * S - ft.getlength(foot) / 2, (iy1 + 18) * S), foot, font=ft, fill=(156, 160, 170))
    _card = (im, pad)
    return _card


_tab = None


def tab_layer():
    # "Chatbot" label sits above the scrolling messages, as in Gradio
    global _tab
    if _tab is None:
        lt = F(21)
        tw = lt.getlength('Chatbot') / S + 58
        im = new(tw + 2, 42)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, tw * S, 40 * S), radius=8 * S, fill=(255, 255, 255), outline=GRID, width=2)
        d.rounded_rectangle((16 * S, 13 * S, 34 * S, 26 * S), radius=3 * S, outline=(120, 124, 135), width=int(1.6 * S))
        d.text((42 * S, 6 * S), 'Chatbot', font=lt, fill=(100, 104, 115))
        _tab = im
    return _tab


MSG_X0 = CX0 + 24 + 28
MSG_X1 = CX1 - 24 - 28
MSG_Y0 = CY0 + 24 + 64
CLIP0, CLIP1 = CY0 + 26, CY1 - 162
LIMIT = CLIP1 - 22


def msg_layout(msgs):
    """y position, size and appear time of every message (dots appear 0.6s before agent replies)."""
    out, y = [], MSG_Y0
    for m in msgs:
        ta, kind, content = m[:3]
        mw = m[3] if len(m) > 3 else 640
        lay = sys_layer(content) if kind == 'sys' else bubble(kind, content, mw)
        w, h = lay.width / S, lay.height / S
        x = MSG_X1 - w if kind == 'user' else MSG_X0
        out.append((ta, kind, lay, x, y, w, h))
        y += h + 20
    return out


def chat_content(layer, msgs, t):
    lay_ = msg_layout(msgs)
    off = 0.0
    for (ta, kind, lay, x, y, w, h) in lay_:
        if kind == 'agent' or kind == 'md':
            pass
        ts = ta - 0.6 if kind not in ('user', 'sys') else ta
        if t >= ts and t < ta:
            off = max(off, ease((t - ts) / 0.35) * max(0, y + 50 - LIMIT))
        if t >= ta:
            off = max(off, ease((t - ta) / 0.45) * max(0, y + h - LIMIT))
    for (ta, kind, lay, x, y, w, h) in lay_:
        yy = y - off
        if kind not in ('user', 'sys'):
            ts = ta - 0.6
            if ts <= t < ta:
                dots = new(96, 50)
                dd = ImageDraw.Draw(dots)
                dd.rounded_rectangle((0, 0, dots.width - 1, dots.height - 1), radius=12 * S, fill=A_FILL, outline=A_LINE, width=2)
                for i in range(3):
                    a = 0.5 + 0.5 * math.sin((t - ts) * 10 - i * 0.9)
                    c = int(200 - 85 * a)
                    px = (24 + i * 24) * S
                    dd.ellipse((px - 5 * S, 25 * S - 5 * S, px + 5 * S, 25 * S + 5 * S), fill=(c, c, c + 4))
                comp(layer, dots, x, yy)
        if t >= ta:
            p = ease((t - ta) / 0.32)
            comp(layer, lay, x, yy + (1 - p) * 16, p)
    # clip to the chat panel
    d = ImageDraw.Draw(layer)
    d.rectangle((CX0 * S, 0, CX1 * S, CLIP0 * S), fill=(0, 0, 0, 0))
    d.rectangle((CX0 * S, CLIP1 * S, CX1 * S, H * S), fill=(0, 0, 0, 0))


def caption(layer, t, cap, n, total):
    kick, lines, sub, chip = cap
    x = 96
    ke = ease(seg(t, 0.1, 0.5))
    fk = F(25, 'b')
    num = f'{n:02d} / {total}'
    comp(layer, text_layer(num, fk, (110, 114, 128, 255)), x, 350 + (1 - ke) * 12, ke)
    nx = x + fk.getlength(num) / S + 22
    comp(layer, text_layer(kick.upper(), fk, ORANGE + (255,)), nx, 350 + (1 - ke) * 12, ke)
    for i, l in enumerate(lines):
        e = ease(seg(t, 0.25 + i * 0.25, 0.75 + i * 0.25))
        comp(layer, text_layer(l, F(78, 'b'), WHITE + (255,)), x - 3, 392 + i * 96 + (1 - e) * 22, e)
    yb = 392 + len(lines) * 96 + 18
    e = ease(seg(t, 0.55 + len(lines) * 0.25, 1.15 + len(lines) * 0.25))
    for i, l in enumerate(sub):
        comp(layer, text_layer(l, F(30), MUTE + (255,)), x, yb + i * 42 + (1 - e) * 10, e)
    if chip:
        ta, txt = chip
        e = ease(seg(t, ta, ta + 0.35))
        fm = F(24, 'm')
        cw = fm.getlength(txt) / S + 64
        im = new(cw, 48)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=24 * S, fill=(30, 24, 20), outline=(120, 60, 20), width=2)
        d.ellipse((20 * S, 19 * S, 30 * S, 29 * S), fill=ORANGE)
        d.text((42 * S, 9 * S), txt, font=fm, fill=(253, 186, 116))
        comp(layer, im, x, yb + len(sub) * 42 + 26 + (1 - e) * 10, e)


# ---------- scenes ----------
def s_hook(t, base):
    e = ease(seg(t, 0.0, 0.45))
    centered(base, 'Check a guest in', F(118, 'b'), WHITE + (255,), 245, e, (1 - e) * 28)
    e2 = ease(seg(t, 0.25, 0.75))
    centered(base, 'by just saying so.', F(118, 'b'), ORANGE + (255,), 382, e2, (1 - e2) * 28)
    e3 = ease(seg(t, 0.55, 0.95))
    x0, x1, y0, y1 = 380, 1540, 640, 726
    pill = new(x1 - x0, y1 - y0)
    d = ImageDraw.Draw(pill)
    d.rounded_rectangle((0, 0, pill.width - 1, pill.height - 1), radius=18 * S, fill=(255, 255, 255))
    full = 'Register a new guest, Jane Smith, room 204.'
    n = int(round(len(full) * seg(t, 0.75, 2.05)))
    shown = full[:n]
    fi = F(34)
    d.text((34 * S, 20 * S), shown, font=fi, fill=INK)
    cw = fi.getlength(shown)
    if n < len(full) or int(t * 2.4) % 2 == 0:
        d.rectangle((34 * S + cw + 4, 24 * S, 34 * S + cw + 4 + 3 * S, 64 * S), fill=ORANGE)
    cx, cy = pill.width - 50 * S, pill.height / 2
    press = 1 - 0.12 * math.exp(-((t - 2.15) / 0.06) ** 2)
    r = 26 * press
    d.ellipse((cx - r * S, cy - r * S, cx + r * S, cy + r * S), fill=ORANGE)
    d.polygon([(cx - 9 * S, cy - 11 * S), (cx + 12 * S, cy), (cx - 9 * S, cy + 11 * S), (cx - 4 * S, cy)], fill=(255, 255, 255))
    comp(base, pill, x0, y0 + (1 - e3) * 18, e3)


def li(k, v):
    return ('li', [(k + ':', 'b'), (' ' + v, 'r')])


# Agent copy is taken from the demo screenshots; guests are the demo's fictional test records.
CHAT = {
    'intake': ([
        (0.35, 'user', 'Register a new guest, Jane Smith, room 204.'),
        (1.5, 'agent', "Sure! Could you please provide Jane Smith's phone number and her check-in date (YYYY-MM-DD)?"),
        (2.6, 'user', 'Her phone is 0712345678, check-in 2026-10-02, check-out 2026-10-05.'),
        (3.7, 'md', [('p', [('The new guest has been saved:', 'r')]), li('Name', 'Jane Smith'), li('Phone', '0712345678'),
                     li('Room', '204'), li('Check-in', '2026-10-02'), li('Check-out', '2026-10-05'),
                     ('p', [('Customer ID: ', 'r'), ('2', 'b'), ('. Let me know if you need anything else.', 'r')])], 720),
    ], ('Add a guest', ["Asks for what's", 'missing.'], ['Never guesses or invents a detail.'], (3.5, 'save_customer()'))),
    'view_id': ([
        (0.3, 'user', 'Show me customer 2.'),
        (1.0, 'md', [('p', [('Here are the details for customer #2:', 'r')]), li('Name', 'Jane Smith'), li('Phone', '0712345678'),
                     li('Email', '(none)'), li('Room', '204'), li('Check-in', '2026-10-02'), li('Check-out', '2026-10-05'),
                     li('Special requests', '(none)')]),
    ], ('View by ID', ['Pull up any', 'guest by ID.'], ['Every field, straight from SQLite.'], (0.9, 'view_customer()'))),
    'view_name': ([
        (0.3, 'user', 'Find Jane Smith.'),
        (1.0, 'md', [('p', [('I found two customers named ', 'r'), ('Jane Smith', 'b'), (':', 'r')]),
                     ('ol', 1, [('Customer #2', 'b'), (' \u2013 Room 204, check-in 2026-10-02, check-out 2026-10-05', 'r')]),
                     ('ol', 2, [('Customer #3', 'b'), (' \u2013 Room 310, check-in 2026-11-01, check-out 2026-11-04', 'r')]),
                     ('p', [('Which one would you like to view in more detail or work with?', 'r')])], 900),
    ], ('Find by name', ['Same name?', 'It asks which.'], ['Duplicates are listed, never guessed.'], None)),
    'not_found': ([
        (0.3, 'user', 'Find a customer called Zzz Nobody.'),
        (1.0, 'md', [('p', [("I'm sorry, but I couldn't find any customer named ", 'r'), ('Zzz Nobody', 'b'),
                            (" in the system. If you'd like to add a new record for this guest, just let me know!", 'r')])]),
    ], ('Not found', ['No match, no', 'make-believe.'], ['It offers to add the guest instead.'], None)),
    'update': ([
        (0.3, 'user', 'Change the room number for customer 1 to 118.'),
        (1.1, 'md', [('p', [('The room number for customer ', 'r'), ('ID 1', 'b'), (' has been updated to ', 'r'), ('118', 'b'),
                            ('. Let me know if you need any further changes.', 'r')])]),
    ], ('Update', ['Move a guest', 'in one line.'], ['Just say what changed.'], (1.0, 'update_customer()'))),
    'id_lock': ([
        (0.3, 'user', "Change customer 1's ID to 10."),
        (1.1, 'agent', "I'm sorry, but a customer's ID cannot be changed. The ID is a permanent identifier used by the system."),
    ], ('Protected ID', ['IDs stay', 'put.'], ['Permanent identifiers, by design.'], None)),
    'validate': ([
        (0.3, 'user', 'Register a new guest, Test User, room 5, phone 123, check-in 2026-10-02, check-out 2026-10-04.'),
        (1.45, 'agent', 'Sure! Could you please provide a valid phone number (9-15 digits, may start with +)?'),
    ], ('Phone check', ['Bad data gets', 'a polite no.'], ['Then it asks for a correction.'], None)),
    'dates': ([
        (0.3, 'user', 'Register Test Two, room 6, phone 0712345678, check-in 2026-10-10, check-out 2026-10-05.'),
        (1.45, 'agent', 'I see that the check-out date you provided (2026-10-05) is earlier than the check-in date (2026-10-10). '
                        'Could you please give a valid check-out date that is after 2026-10-10?'),
    ], ('Date check', ['Time travel', 'not supported.'], ['Check-out must come after check-in.'], None)),
    'delete_yes': ([
        (0.3, 'user', 'Delete customer 4.'),
        (1.1, 'agent', 'Do you really want to delete John Smith (room 150, customer #4)? Please reply yes or no.'),
        (2.3, 'user', 'yes'),
        (2.9, 'agent', 'Done. Customer #4 (John Smith, room 150) has been deleted.'),
    ], ('Delete', ['Gone, once', 'you say yes.'], ['It names the guest before deleting.'], (0.9, 'delete_customer()'))),
    'delete_no': ([
        (0.3, 'user', 'Delete customer 2.'),
        (1.2, 'agent', 'Do you really want to delete Jane Smith (room 204, customer #2)? Please reply yes or no.'),
        (2.45, 'user', 'no'),
        (3.0, 'agent', 'Deletion cancelled. The customer record was not changed.'),
    ], ('Safe delete', ['No delete', 'without a yes.'], ['Enforced in Python, not left to the model.'], (1.0, 'delete_customer()  waits for "yes"'))),
    'list': ([
        (0.3, 'user', 'List all customers.'),
        (1.0, 'md', [('p', [('Here are the current customers:', 'r')]),
                     ('table', ['ID', 'Full Name', 'Phone', 'Room', 'Check-in', 'Check-out'],
                      [['1', 'Amara Perera', '+94712223344', '118', '2026-11-01', '2026-11-03'],
                       ['2', 'Jane Smith', '0712345678', '204', '2026-10-02', '2026-10-05'],
                       ['3', 'Jane Smith', '0771234567', '310', '2026-11-01', '2026-11-04']]),
                     ('p', [('Let me know if you need any details or wish to update a record.', 'r')])], 900),
    ], ('List all', ['The whole', 'register.'], ['One sentence, one clean table.'], (0.9, 'list_customers()'))),
    'search': ([
        (0.3, 'user', 'Which customers are checking in on 2026-10-02?'),
        (1.0, 'md', [('p', [('Here are the customers checking in on ', 'r'), ('2026-10-02', 'b'), (':', 'r')]),
                     ('li', [('Jane Smith', 'b'), (' (ID 2) \u2013 Room 204, phone 0712345678, checking out on 2026-10-05.', 'r')])], 900),
        (2.5, 'user', 'Which customers are checking in on 2030-01-01?'),
        (3.2, 'agent', 'There are no customers scheduled to check in on 2030-01-01.'),
    ], ('Search by date', ["Who's arriving", 'today?'], ['Ask by check-in date.'], (0.9, 'search_by_check_in_date()'))),
    'export': ([
        (0.3, 'user', 'Export the customer list as a PDF.'),
        (1.0, 'md', [('p', [('The customer list has been exported as a PDF.', 'r')]),
                     ('code', 'File location:', 'customer_list.pdf'),
                     ('p', [('Number of customers:', 'b'), (' 3', 'r')]),
                     ('p', [('Let me know if you need anything else.', 'r')])]),
    ], ('Export', ['Print-ready,', 'on request.'], ['Writes customer_list.pdf.'], (0.9, 'export_customers_pdf()'))),
    'persist': ([
        (0.2, 'sys', 'Kernel restarted'),
        (0.7, 'user', 'Show me customer 2.'),
        (1.4, 'md', [('p', [('Here is the information for customer 2:', 'r')]), li('Full Name', 'Jane Smith'),
                     li('Phone', '0712345678'), li('Room Number', '204'), li('Check-in', '2026-10-02'), li('Check-out', '2026-10-05')]),
    ], ('Persistence', ['Restart it.', 'Still there.'], ['Records live in a local SQLite file.'], None)),
    'offtopic': ([
        (0.3, 'user', "What's the price for room 204 tonight?"),
        (1.1, 'agent', "I'm sorry, but I can only help with managing customer records."),
        (2.1, 'user', 'Can you process a credit card payment for me?'),
        (2.9, 'agent', "I'm sorry, but I can only assist with adding, viewing, updating, or deleting customer records."),
    ], ('Stays on topic', ["Won't quote", 'you a price.'], ['Prices and payments are out of scope.'], None)),
}


def s_outro(t, base):
    e = ease(seg(t, 0.05, 0.55))
    centered(base, 'A FRONT DESK YOU CAN TALK TO', F(25, 'b'), ORANGE + (255,), 270, e, (1 - e) * 16)
    e = ease(seg(t, 0.2, 0.75))
    centered(base, 'Hotel Management AI Agent', F(108, 'b'), WHITE + (255,), 318, e, (1 - e) * 22)
    chips = ['Add', 'View', 'Update', 'Delete', 'List all', 'Search by date', 'Export PDF']
    f = F(30, 'sb')
    ws = [f.getlength(c) / S + 52 for c in chips]
    gap = 14
    tot = sum(ws) + gap * (len(chips) - 1)
    x = (W - tot) / 2
    for i, c in enumerate(chips):
        e = ease(seg(t, 0.6 + i * 0.09, 0.95 + i * 0.09))
        im = new(ws[i], 62)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=31 * S, fill=(30, 32, 40), outline=(68, 72, 86), width=2)
        d.text((26 * S, 11 * S), c, font=f, fill=WHITE)
        comp(base, im, x, 492 + (1 - e) * 14, e)
        x += ws[i] + gap
    e = ease(seg(t, 1.2, 1.7))
    centered(base, 'Python  \u00b7  SQLite  \u00b7  Gradio  \u00b7  Llama 3.1 via Ollama, or Groq', F(30), MUTE + (255,), 610, e)
    e = ease(seg(t, 1.45, 1.95))
    fm = F(28, 'm')
    cmd = 'uv sync  \u2192  open hotel_agent.ipynb  \u2192  Run All'
    cw = fm.getlength(cmd) / S + 60
    im = new(cw, 60)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=12 * S, fill=(24, 20, 18), outline=(110, 56, 18), width=2)
    d.text((30 * S, 13 * S), cmd, font=fm, fill=(253, 186, 116))
    comp(base, im, (W - cw) / 2, 690 + (1 - e) * 10, e)


ORDER = [('hook', None, 2.4),
         ('chat', 'intake', 6.0), ('chat', 'view_id', 4.0), ('chat', 'view_name', 4.4), ('chat', 'not_found', 3.8),
         ('chat', 'update', 3.8), ('chat', 'id_lock', 4.0), ('chat', 'validate', 3.8), ('chat', 'dates', 4.2),
         ('chat', 'delete_yes', 5.0), ('chat', 'delete_no', 5.0), ('chat', 'list', 4.4), ('chat', 'search', 5.0),
         ('chat', 'export', 4.0), ('chat', 'persist', 4.2), ('chat', 'offtopic', 4.6),
         ('outro', None, 3.6)]
SCENES, _t = [], 0.0
for kind, key, dur in ORDER:
    SCENES.append((round(_t, 3), round(_t + dur, 3), kind, key))
    _t += dur
DUR = round(_t, 3)
NCHAT = sum(1 for s in SCENES if s[2] == 'chat')


def frame(t):
    base = bg()
    idx = max(i for i, s in enumerate(SCENES) if s[0] <= t or i == 0)
    a, b, kind, key = SCENES[idx]
    lt = t - a
    if kind == 'hook':
        lay = new(W, H)
        s_hook(lt, lay)
        fo = 1 - seg(lt, b - a - 0.3, b - a)
        comp(base, lay, 0, 0, fo)
    elif kind == 'chat':
        first = SCENES[idx - 1][2] != 'chat'
        last = SCENES[idx + 1][2] != 'chat'
        cin = ease(seg(lt, 0.0, 0.5)) if first else 1.0
        cout = 1 - seg(lt, b - a - 0.35, b - a) if last else 1.0
        im, pad = card_layer()
        cx = CX0 - pad + (1 - cin) * 160
        comp(base, im, cx, CY0 - pad, min(cin, cout))
        fin = seg(lt, 0, 0.22) if not first else 1.0
        fo = 1 - seg(lt, b - a - 0.3, b - a)
        al = min(fin, fo, cout if last else 1.0)
        lay = new(W, H)
        chat_content(lay, CHAT[key][0], lt)
        comp(base, lay, 0, 0, al)
        comp(base, tab_layer(), CX0 + 24 + (1 - cin) * 160, CY0 + 24, min(cin, cout))
        cap = new(W, H)
        caption(cap, lt, CHAT[key][1], idx, NCHAT)
        comp(base, cap, 0, 0, al)
    else:
        lay = new(W, H)
        s_outro(lt, lay)
        comp(base, lay, 0, 0, 1.0)
    return base.resize((W, H), Image.LANCZOS).convert('RGB')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for t in map(float, sys.argv[2:]):
            frame(t).save(f'{OUT}/still_{t:06.2f}.png')
    elif mode == 'scenes':
        for s in SCENES:
            print(s)
        print('DUR', DUR)
    else:
        part, nparts = int(sys.argv[2]), int(sys.argv[3])
        N = int(round(DUR * FPS))
        for i in range(part, N, nparts):
            p = f'{OUT}/frames/f{i:04d}.png'
            if not os.path.exists(p):
                frame(i / FPS).save(p)
