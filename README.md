# cetar

Pecut berbasis fisika untuk Windows. Tahan tombol tengah mouse (roller), ayunkan, dan pecut jendela apa pun di layar, termasuk terminal.

> **English:** a physics-based whip overlay for Windows. Install with `pip install git+https://github.com/nothinx/cetar`, run `cetar --lang en`, hold the middle mouse button and swing. Quit with `Ctrl+Shift+Q`.

## Fitur

- **Tampil di mana saja.** Lapisan transparan yang tembus klik dan selalu di atas menutupi semua monitor, jadi pecut muncul di atas aplikasi apa pun.
- **Gerakan pecut sungguhan.** Saat diayun, tali terseret di belakang gagang. Saat tangan berhenti, tali menggulung dari gagang ke ujung, lurus penuh, lalu berbunyi *cetar*, kemudian memantul balik.
- **Mengikuti arah.** Pecutan keluar searah ayunan. Tarikan balik tangan setelah pecutan dikenali sebagai ancang-ancang dan diabaikan.
- **Efek kartun.** Setiap pecutan memunculkan ledakan bergerigi berisi tulisan, garis benturan, bintang pusing, balon ucapan, dan suara cambuk.
- **Jendela bergetar.** Jendela yang kena ujung pecut bergetar sebentar.
- **Dua bahasa.** Teks efek tersedia dalam bahasa Indonesia dan Inggris. Bahasa dipilih otomatis mengikuti bahasa Windows.
- **Tanpa dependensi.** Hanya memakai pustaka standar Python.

## Kebutuhan

- Windows 10 atau 11
- Python 3.8+ dari [python.org](https://www.python.org/downloads/). Saat instalasi, centang *Add python.exe to PATH*.

## Instalasi

```powershell
pip install git+https://github.com/nothinx/cetar
```

Perintah ini membutuhkan Git. Kalau Git tidak terpasang, gunakan arsip ZIP:

```powershell
pip install https://github.com/nothinx/cetar/archive/refs/heads/main.zip
```

Untuk menghapus: `pip uninstall cetar`.

## Pemakaian

```powershell
cetar
```

Program berjalan tanpa jendela konsol. Tanpa instalasi, bisa juga langsung dengan `pythonw cetar.py`.

| Aksi | Cara |
|---|---|
| Memunculkan pecut | Tahan tombol tengah mouse |
| Memecut | Ayunkan dengan cepat, lalu berhenti |
| Keluar | `Ctrl` + `Shift` + `Q` |

### Bahasa

Bahasa teks efek mengikuti bahasa tampilan Windows: Indonesia untuk Windows berbahasa Indonesia, Inggris untuk lainnya. Untuk memilih sendiri:

```powershell
cetar --lang id
cetar --lang en
```

Untuk menambah bahasa, tambahkan satu entri di `TEXTS` dalam `cetar.py`. Isinya `words` (tulisan di ledakan) dan `phrases` (isi balon ucapan).

## Pengaturan

Angka pengaturan ada di bagian atas `cetar.py`:

| Konstanta | Bawaan | Fungsi |
|---|---|---|
| `N`, `SEG` | `38`, `13` | Jumlah ruas dan panjang tiap ruas (px). `H` ruas pertama menjadi gagang. |
| `H` | `6` | Panjang gagang (dalam ruas) |
| `MAX_TILT` | `0.5` | Kemiringan gagang maksimal (radian) |
| `GRAV`, `DAMP` | `0.6`, `0.92` | Gravitasi dan redaman tali saat diam |
| `HAND_SPEED` | `18` | Kecepatan tangan (px per langkah) yang dihitung sebagai ayunan. Turunkan kalau memecut terasa berat. |
| `LASH_FRAMES` | `7` | Lama tali menggulung sebelum *cetar* (langkah 1/60 detik). Makin kecil makin tajam. |
| `LASH_WAVE` | `0.35` | Lebar gelombang gulungan di sepanjang tali |
| `RETURN_STEPS` | `40` | Jeda setelah pecutan; ayunan berlawanan arah dalam jeda ini dianggap ancang-ancang |
| `RECOIL` | `18` | Kuat pantulan balik ujung tali setelah *cetar* |

## Cara kerja

- **Lapisan layar.** Jendela Tk tanpa bingkai menutupi seluruh desktop virtual. Latarnya warna kunci yang dibuat transparan dengan `-transparentcolor`. Gaya `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE` membuatnya tembus klik dan tidak muncul di taskbar.
- **Input.** Posisi kursor dan tombol tengah dibaca dengan `GetCursorPos` dan `GetAsyncKeyState`. Tidak ada hook global yang dipasang.
- **Waktu.** Simulasi berjalan dengan langkah tetap 60 Hz, tidak bergantung pada ketepatan timer Tk. Posisi kursor diinterpolasi di antara langkah.
- **Tali saat diam.** Integrasi Verlet dengan batasan panjang *follow-the-leader* dan koreksi kecepatan ([Müller dkk., 2012](https://matthias-research.github.io/pages/publications/FTLHairFur.pdf)). Panjang tali tetap tanpa ada tenaga palsu yang membuatnya menggeliat.
- **Pecutan.** Arah ayunan dikumpulkan selama tangan bergerak di atas `HAND_SPEED`. Saat tangan melambat, sudut setiap ruas dibelokkan ke arah ayunan oleh gelombang *smoothstep* yang berjalan dari gagang ke ujung, berputar lewat atas. Bunyi *cetar* terjadi saat tali lurus penuh.
- **Jendela bergetar.** `WindowFromPoint` mencari jendela di bawah ujung pecut, lalu `SetWindowPos` menggesernya dalam urutan singkat yang meredam, dan jendela kembali ke posisi semula.

## Keamanan dan privasi

- Tidak ada akses jaringan dan tidak ada data yang dikirim ke mana pun.
- Keyboard tidak direkam. Program hanya mengecek tombol tengah mouse dan kombinasi `Ctrl+Shift+Q`.
- Tidak membutuhkan hak administrator dan tidak mengubah pengaturan sistem.
- Satu-satunya file yang ditulis adalah `cetar_crack.wav` di folder temp, yaitu suara cambuk yang dibuat saat program dijalankan.

## Pengujian

```powershell
python test_cetar.py
```

Pengujian berjalan tanpa jendela dan tanpa mouse. Yang diperiksa:

- ayunan cepat menghasilkan tepat satu pecutan, setelah tangan berhenti, searah ayunan;
- ayunan pelan tidak menghasilkan pecutan;
- panjang tali tetap dan tali kembali diam;
- urutan kanan–kiri–kanan menghasilkan dua pecutan ke kanan;
- setiap bahasa memiliki teks.

## Batasan

- Jendela yang sedang maximize tidak digetarkan.
- Klik tengah tetap diteruskan ke aplikasi di bawahnya. Di browser, misalnya, ini bisa memicu autoscroll.
- Jendela yang berjalan dengan hak lebih tinggi (misalnya terminal administrator) tidak bisa digeser.

## Lisensi

[MIT](LICENSE)
