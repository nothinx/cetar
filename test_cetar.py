"""Cek fisika pecut tanpa mouse: satu kibasan cepat = tepat satu CTAK di akhir ayunan, searah ayunan,
kibasan pelan = tidak, panjang tali tetap, tali lalu tenang."""
import math
import cetar


class Sim(cetar.Cetar):
    def __init__(self):  # tanpa jendela
        H, N, SEG = cetar.H, cetar.N, cetar.SEG
        self.pts = [[500, 500 - i * SEG] if i <= H else [501, 500 - H * SEG + (i - H) * SEG] for i in range(N)]
        self.prev = [p[:] for p in self.pts]
        self.tilt, self.lash, self.swing, self.cracks, self.n = 0.0, None, [0.0, 0.0, 0], [], 0
        self.since_lash, self.last_angle, self.swing_start = 999, 0.0, 0

    def crack(self, x, y):
        self.cracks.append((self.n, x, y))


def gerak(path):
    s = Sim()
    for p in path:
        s.n += 1
        s.step(*p)
    return s.cracks


def ayun(x, dx, n=8):
    return [(x + dx * i, 500) for i in range(1, n + 1)]


def kibas(speed):
    s, tips = Sim(), []
    path = [(500, 500)] * 90 + ayun(500, speed) + [(500 + speed * 8, 500)] * 180
    for p in path:
        s.n += 1
        before = s.pts[-1][:]
        s.step(*p)
        tips.append(math.dist(before, s.pts[-1]))
    length = sum(math.dist(s.pts[i], s.pts[i + 1]) for i in range(cetar.H, cetar.N - 1))
    return s.cracks, max(tips[-30:]), length


if __name__ == '__main__':
    cracks, rest, length = kibas(40)
    assert len(cracks) == 1, f'kibasan cepat harus 1 CTAK, dapat {len(cracks)}'
    n, x, y = cracks[0]
    assert n > 98, f'CTAK harus setelah tangan berhenti (frame 98), dapat frame {n}'
    assert x > 500 + 40 * 8 + 300, f'ujung pecut harus terlempar ke kanan (arah ayunan), x={x:.0f}'
    assert rest < 1, f'tali belum tenang 2.5 detik setelah berhenti (ujung {rest:.1f} px/frame)'
    assert abs(length - (cetar.N - cetar.H - 1) * cetar.SEG) < 0.01, 'panjang tali berubah'
    assert not kibas(10)[0], 'kibasan pelan tidak boleh CTAK'
    # pecut berulang: kanan, tarik balik ke kiri, kanan lagi -> 2 pecutan, dua-duanya ke kanan
    p = [(500, 500)] * 60 + ayun(500, 40)
    p += [p[-1]] * 15 + ayun(820, -40)
    p += [p[-1]] * 15 + ayun(500, 40) + [(820, 500)] * 40
    cr = gerak(p)
    assert len(cr) == 2 and all(x > 820 for _, x, _ in cr), f'pecut berulang salah: {cr}'
    for lang, text in cetar.TEXTS.items():
        assert text['words'] and text['phrases'], f'teks bahasa {lang} kosong'
    print('OK')
