"""Cetar: tahan klik roller (tombol tengah), lalu kibaskan mouse untuk memecut apa saja di layar.
Ujung pecut kena jendela (mis. terminal) -> "CTAK!" dan jendelanya bergetar. Keluar: Ctrl+Shift+Q.
Jalankan: pythonw cetar.py [--lang id|en]  (tanpa jendela konsol)"""
import sys

if sys.platform != 'win32':
    sys.exit('cetar hanya berjalan di Windows / cetar only runs on Windows.')

import argparse, ctypes, math, os, random, struct, tempfile, time, tkinter as tk, wave, winsound
from ctypes import wintypes

u32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    u32.SetProcessDPIAware()
for f in (u32.WindowFromPoint, u32.GetAncestor, u32.GetParent):
    f.restype = wintypes.HWND
u32.WindowFromPoint.argtypes = [wintypes.POINT]
u32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND] + [ctypes.c_int] * 4 + [wintypes.UINT]

KEY = '#010101'                 # warna transparan overlay
DT = 1 / 60                     # satu langkah fisika (detik)
N, SEG = 38, 13                 # jumlah ruas total, panjang ruas (px) -> tali 32 x 13 = 416 px
H = 6                           # ruas pertama = gagang kaku (6 x 13 = 78 px)
MAX_TILT = 0.5                  # kemiringan gagang maksimal (radian, ~30°)
GRAV, DAMP = 0.6, 0.92          # DAMP lebih kecil = tali cepat tenang
HAND_SPEED = 18                 # ayunan dihitung kalau tangan secepat ini (px/frame): turunkan kalau susah memecut
LASH_FRAMES = 7                 # lama pecutan menggulung sampai CTAK (langkah 1/60 detik): kecil = cepat
LASH_WAVE = 0.35                # lebar gelombang gulungan di sepanjang tali (0..1)
RETURN_STEPS = 40               # ayunan berlawanan yang mulai < 40 langkah (~0.7 dtk) setelah CTAK = tarikan balik
RECOIL = 18                     # kuat pantulan balik ujung tali setelah CTAK (px/frame)
POW_LIFE = 50                   # lama efek ledakan kartun (frame, ~16 ms)
SKIP_CLASSES = {'Shell_TrayWnd', 'Progman', 'WorkerW'}  # taskbar & desktop jangan digoyang
# teks per bahasa: words = tulisan di ledakan, phrases = isi balon ucapan. Tambah bahasa = tambah entri.
TEXTS = {
    'id': {'words': ['CTAK!', 'BLETAK!', 'PLAK!', 'POW!', 'WHAM!', 'JDER!', 'CETAR!'],
           'phrases': ['AMPUN!', 'Aduh! Saya perbaiki!', 'Oke oke, saya refactor!', 'Jangan lagi!',
                       'Bug-nya hilang, sumpah!', 'Saya baca ulang dokumennya!', 'Maaf halusinasi!',
                       'Test-nya hijau sekarang!', 'AAAA!', 'Siap, bos!']},
    'en': {'words': ['CRACK!', 'WHAP!', 'SMACK!', 'POW!', 'WHAM!', 'THWACK!', 'KAPOW!'],
           'phrases': ['MERCY!', "Ouch! I'll fix it!", "Okay okay, I'll refactor!", 'Not again!',
                       'The bug is gone, I swear!', "I'll reread the docs!", 'Sorry for hallucinating!',
                       'Tests are green now!', 'AAAA!', 'Yes, boss!']},
}


def system_lang():
    """Bahasa tampilan Windows: Indonesia -> 'id', selain itu 'en'."""
    return 'id' if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x21 else 'en'


def make_crack_wav():
    rate, n = 22050, int(22050 * 0.18)
    data = b''.join(struct.pack('<h', int(32000 * random.uniform(-1, 1) * math.exp(-i / (rate * 0.015))))
                    for i in range(n))
    path = os.path.join(tempfile.gettempdir(), 'cetar_crack.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(data)
    return path


def down(vk):
    return u32.GetAsyncKeyState(vk) & 0x8000


class Cetar:
    def __init__(self, lang='en'):
        self.text = TEXTS[lang]
        self.vx, self.vy = u32.GetSystemMetrics(76), u32.GetSystemMetrics(77)
        w, h = u32.GetSystemMetrics(78), u32.GetSystemMetrics(79)
        self.root = root = tk.Tk()
        root.overrideredirect(True)
        root.geometry(f'{w}x{h}+{self.vx}+{self.vy}')
        root.attributes('-topmost', True, '-transparentcolor', KEY)
        self.cv = tk.Canvas(root, bg=KEY, highlightthickness=0)
        self.cv.pack(fill='both', expand=True)
        root.update()
        hwnd = u32.GetParent(root.winfo_id())
        # layered | transparent (tembus klik) | toolwindow (tak di taskbar) | noactivate
        u32.SetWindowLongW(hwnd, -20, u32.GetWindowLongW(hwnd, -20) | 0x80000 | 0x20 | 0x80 | 0x08000000)
        self.sound = make_crack_wav()
        self.active, self.shaking = False, set()
        self.last, self.acc, self.steps = time.perf_counter(), 0.0, 0
        self.pts, self.prev, self.sparks, self.texts = [], [], [], []
        self.tick()
        root.mainloop()

    def cursor(self):
        p = wintypes.POINT()
        u32.GetCursorPos(ctypes.byref(p))
        return p.x - self.vx, p.y - self.vy

    def tick(self):
        if down(0x11) and down(0x10) and down(0x51):  # Ctrl+Shift+Q
            self.root.destroy()
            return
        mx, my = self.cursor()
        # timer Tk di Windows tidak tepat 16 ms -> fisika dijalankan per 1/60 detik waktu sungguhan
        now = time.perf_counter()
        self.acc = min(self.acc + now - self.last, 4 * DT)
        self.last = now
        self.steps = int(self.acc / DT)
        self.acc -= self.steps * DT
        if down(0x04):  # tombol tengah ditahan
            if not self.active:
                self.active = True
                # gagang ke atas, tali menjuntai dari ujung gagang
                self.pts = [[mx, my - i * SEG] if i <= H else [mx + 1, my - H * SEG + (i - H) * SEG]
                            for i in range(N)]
                self.prev = [p[:] for p in self.pts]
                self.tilt, self.lash, self.swing = 0.0, None, [0.0, 0.0, 0]
                self.since_lash, self.last_angle, self.swing_start = 999, 0.0, 0
            x0, y0 = self.pts[0]
            for j in range(1, self.steps + 1):  # posisi kursor diinterpolasi di antara langkah
                self.step(x0 + (mx - x0) * j / self.steps, y0 + (my - y0) * j / self.steps)
        else:
            self.active = False
        self.draw()
        self.root.after(10, self.tick)

    def step(self, mx, my):
        hand = math.dist(self.pts[0], (mx, my))
        hdx, hdy = mx - self.pts[0][0], my - self.pts[0][1]
        # gagang selalu tegak ke atas, hanya miring mengikuti ayunan (saat pecutan: condong ke arah pecutan)
        if self.lash:
            target = MAX_TILT * (1 if math.cos(self.lash['angle']) > 0 else -1)
        else:
            target = max(-MAX_TILT, min(MAX_TILT, hdx * 0.03))
        self.tilt += (target - self.tilt) * 0.3
        self.pts[0][:] = mx, my
        ux, uy = math.sin(self.tilt), -math.cos(self.tilt)
        for i in range(1, H + 1):
            self.pts[i][:] = mx + ux * SEG * i, my + uy * SEG * i

        if self.lash:
            self.unroll()
            return
        # kumpulkan arah ayunan; ayunan selesai (tangan melambat) -> pecutan ke arah itu
        self.since_lash += 1
        if hand > HAND_SPEED:
            if not self.swing[2]:
                self.swing_start = self.since_lash
            self.swing[0] += hdx; self.swing[1] += hdy; self.swing[2] += 1
        elif hand < HAND_SPEED / 2:
            if self.swing[2] >= 3:
                angle = math.atan2(self.swing[1], self.swing[0])
                # tarikan balik (ancang-ancang) sesaat setelah CTAK, berlawanan arah -> bukan pecutan
                pull_back = self.swing_start < RETURN_STEPS and math.cos(angle - self.last_angle) < 0
                self.swing = [0.0, 0.0, 0]
                if not pull_back:
                    self.lash = {'f': 0, 'angle': angle, 'start': self.seg_angles()}
                    self.unroll()
                    return
            self.swing = [0.0, 0.0, 0]
        self.physics()

    def seg_angles(self):
        return [math.atan2(self.pts[i + 1][1] - self.pts[i][1], self.pts[i + 1][0] - self.pts[i][0])
                for i in range(H, N - 1)]

    def unroll(self):
        """Pecutan: tali menggulung lurus dari gagang ke ujung, ujung paling akhir & paling cepat, lalu CTAK."""
        lash = self.lash
        lash['f'] += 1
        p = (lash['f'] / LASH_FRAMES) ** 1.6  # makin lama makin cepat
        front, wave_w, m = p * (1 + LASH_WAVE), LASH_WAVE, N - H - 1
        x, y = self.pts[H]
        for k, a0 in enumerate(lash['start']):
            w = max(0.0, min(1.0, (front - k / (m - 1)) / wave_w))
            w = w * w * (3 - 2 * w)
            diff = (lash['angle'] - a0 + math.pi) % (2 * math.pi) - math.pi
            if abs(diff) > 2.0 and math.sin(a0 + diff / 2) > 0:  # putar lewat atas, bukan lewat bawah
                diff -= math.copysign(2 * math.pi, diff)
            a = a0 + diff * w
            x, y = x + math.cos(a) * SEG, y + math.sin(a) * SEG
            self.pts[H + 1 + k][:] = x, y
        if lash['f'] >= LASH_FRAMES:
            self.lash, self.since_lash, self.last_angle = None, 0, lash['angle']
            # lepas ke fisika dengan sentakan balik: ujung memantul ke arah gagang dan jatuh
            c, s = math.cos(lash['angle']), math.sin(lash['angle'])
            self.prev = [q[:] for q in self.pts]
            for k in range(1, m + 1):
                f = k / m
                self.prev[H + k][0] -= (-c * RECOIL) * f
                self.prev[H + k][1] -= (-s * RECOIL + RECOIL) * f
            self.crack(*self.pts[-1])

    def physics(self):
        for p, q in zip(self.pts[H + 1:], self.prev[H + 1:]):
            vx, vy = (p[0] - q[0]) * DAMP, (p[1] - q[1]) * DAMP
            q[:] = p
            p[0] += vx
            p[1] += vy + GRAV
        # tiap ruas dipaksa tepat SEG -> panjang tetap; koreksi kecepatan (follow-the-leader, Müller 2012)
        # supaya koreksi panjang tidak jadi tenaga palsu yang membuat tali menggeliat terus
        corr = [(0.0, 0.0)] * N
        for i in range(H, N - 1):
            a, b = self.pts[i], self.pts[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy) or 1e-6
            nx, ny = a[0] + dx / d * SEG, a[1] + dy / d * SEG
            corr[i + 1] = nx - b[0], ny - b[1]
            b[0], b[1] = nx, ny
        for i in range(H + 1, N - 1):
            self.prev[i][0] += 0.9 * corr[i + 1][0]
            self.prev[i][1] += 0.9 * corr[i + 1][1]

    def crack(self, x, y):
        winsound.PlaySound(self.sound, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        self.sparks.append({'x': x, 'y': y, 'age': 0, 'word': random.choice(self.text['words']),
                            'ang': random.uniform(-15, 15), 'rot': random.uniform(0, math.pi),
                            'jit': [random.uniform(0.8, 1.25) for _ in range(28)]})
        self.texts.append([x + random.choice((-110, 110)), y - 110, random.choice(self.text['phrases']), 70, x])
        self.shake(int(x) + self.vx, int(y) + self.vy)

    def shake(self, sx, sy):
        h = u32.WindowFromPoint(wintypes.POINT(sx, sy))
        h = h and u32.GetAncestor(h, 2)
        if not h or h in self.shaking or u32.IsZoomed(h):  # ponytail: jendela maximize tidak digoyang
            return
        cls = ctypes.create_unicode_buffer(64)
        u32.GetClassNameW(h, cls, 64)
        if cls.value in SKIP_CLASSES:
            return
        r = wintypes.RECT()
        u32.GetWindowRect(h, ctypes.byref(r))
        self.shaking.add(h)
        offs = [(14, 0), (-12, 5), (10, -5), (-7, 3), (5, 0), (-2, 0), (0, 0)]
        for i, (dx, dy) in enumerate(offs):
            self.root.after(25 * i, u32.SetWindowPos, h, None, r.left + dx, r.top + dy, 0, 0, 0x1 | 0x4 | 0x10)
        self.root.after(25 * len(offs), self.shaking.discard, h)

    def draw(self):
        cv = self.cv
        cv.delete('all')
        if self.active:
            for i in range(H, N - 1):
                (x1, y1), (x2, y2) = self.pts[i], self.pts[i + 1]
                w = max(1.5, 7 - (i - H) * 6 / (N - H))
                cv.create_line(x1, y1, x2, y2, fill='#2a1608', width=w + 3, capstyle='round')
                cv.create_line(x1, y1, x2, y2, fill='#a8703a', width=w, capstyle='round')
            (x0, y0), (xh, yh) = self.pts[0], self.pts[H]
            cv.create_line(x0, y0, xh, yh, fill='#1a0d05', width=24, capstyle='round')
            cv.create_line(x0, y0, xh, yh, fill='#6b3a1a', width=18, capstyle='round')
            nx, ny = (y0 - yh) / (H * SEG), (xh - x0) / (H * SEG)  # tegak lurus gagang
            for t in (0.3, 0.45, 0.6, 0.75):  # lilitan pegangan
                px, py = x0 + (xh - x0) * t, y0 + (yh - y0) * t
                cv.create_line(px - nx * 9, py - ny * 9, px + nx * 9, py + ny * 9, fill='#d9b07a', width=3)
            cv.create_oval(x0 - 13, y0 - 13, x0 + 13, y0 + 13, fill='#d9b07a', outline='#1a0d05', width=3)
            cv.create_oval(xh - 8, yh - 8, xh + 8, yh + 8, fill='#c0c0c0', outline='#1a0d05', width=2)
        for s in self.sparks:
            self.draw_pow(s)
            s['age'] += self.steps
        for t in self.texts:  # balon ucapan kartun
            item = cv.create_text(t[0], t[1], text=t[2], fill='#000000', font=('Comic Sans MS', 15, 'bold'))
            x1, y1, x2, y2 = cv.bbox(item)
            cx = (x1 + x2) / 2
            cv.create_polygon(cx - 12, y2 + 4, cx + 12, y2 + 4, cx + (25 if t[4] > cx else -25), y2 + 30,
                              fill='#ffffff', outline='#000000', width=3)
            bubble = cv.create_oval(x1 - 22, y1 - 14, x2 + 22, y2 + 14, fill='#ffffff', outline='#000000', width=3)
            cv.tag_raise(item, bubble)
            t[1] -= self.steps
            t[3] -= self.steps
        self.sparks = [s for s in self.sparks if s['age'] < POW_LIFE]
        self.texts = [t for t in self.texts if t[3] > 0]

    def draw_pow(self, s):
        """Ledakan ala kartun klasik: bintang bergerigi + tulisan BLETAK! + garis benturan + bintang pusing."""
        cv, x, y, age = self.cv, s['x'], s['y'], s['age']
        if age < 4:
            k = 0.4 + age * 0.25          # muncul "pop" membesar
        elif age < POW_LIFE - 12:
            k = 1.0 + 0.04 * math.sin(age * 0.8)  # sedikit berdenyut
        else:
            k = (POW_LIFE - age) / 12     # mengecil lalu hilang
        r = 60 * k
        if age < 10:  # garis benturan
            for i in range(10):
                a = s['rot'] + i * math.pi / 5
                c, d = math.cos(a), math.sin(a)
                cv.create_line(x + c * r * 1.35, y + d * r * 1.35, x + c * r * 1.8, y + d * r * 1.8,
                               fill='#000000', width=4, capstyle='round')
        for scale, fill in ((1.25, '#e8231a'), (1.0, '#ffe600')):  # bintang merah di belakang, kuning di depan
            pts = []
            for i in range(28):
                a = s['rot'] + i * math.pi / 14
                rr = r * scale * (1 if i % 2 == 0 else 0.55) * s['jit'][i]
                pts += [x + math.cos(a) * rr, y + math.sin(a) * rr]
            cv.create_polygon(pts, fill=fill, outline='#000000', width=3)
        size = max(1, int(26 * k))
        for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3)):  # outline hitam tebal
            cv.create_text(x + dx, y + dy, text=s['word'], angle=s['ang'], fill='#000000', font=('Impact', size))
        cv.create_text(x, y, text=s['word'], angle=s['ang'], fill='#ffffff', font=('Impact', size))
        for i in range(4):  # bintang pusing berputar di atas
            a = age * 0.25 + i * math.pi / 2
            self.star(x + math.cos(a) * 55, y - r - 25 + math.sin(a) * 14, 10)

    def star(self, x, y, r):
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts += [x + math.cos(a) * rr, y + math.sin(a) * rr]
        self.cv.create_polygon(pts, fill='#ffe600', outline='#000000', width=2)


def main():
    ap = argparse.ArgumentParser(prog='cetar', description='Pecut fisika di atas layar Windows. Keluar: Ctrl+Shift+Q.')
    ap.add_argument('--lang', choices=sorted(TEXTS), default=system_lang(),
                    help='bahasa teks efek (default: mengikuti bahasa Windows)')
    Cetar(ap.parse_args().lang)


if __name__ == '__main__':
    main()
