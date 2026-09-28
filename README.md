# CleanTempMail Bot — Made by Yaelahto

Bot CLI (terminal) untuk **membuat temporary email** lewat API `cleantempmail.com`, lalu **menerima & membaca inbox**, serta **scrape kode OTP 6 digit** secara otomatis dari semua email yang masuk. Tinggal jalanin, pilih menu, dan kode langsung ketarik.

## Fitur

* Generate email temporary baru (maksimal 10 slot), bisa domain random atau pilih manual dari daftar domain
* Tambahkan email lama yang sudah kamu miliki agar inboxnya tetap bisa dipantau dari satu tempat
* Cek inbox per-email atau semua sekaligus, dengan tabel rapi (pengirim, subjek, waktu) dan badge `NEW`
* Baca isi email lengkap langsung di terminal, HTML diformat jadi teks biasa
* Scrape kode OTP 6 digit dari seluruh inbox sekaligus, hasil disimpan ke `otp.txt`
* Auto refresh inbox tiap 5 detik, email baru masuk langsung disorot warna hijau
* Hapus email terpilih (bisa banyak nomor sekaligus, misal `1,3,5`) atau reset semua
* Semua email tersimpan di `emails.json` (juga mirror ke `Email.txt`), jadi tidak hilang saat program ditutup

## Struktur File

```
cleantempmail-bot/
├── bot.py         # program utama: semua menu & logika bot
├── requirements.txt   # dependensi Python (httpx, rich)
├── emails.json    # OUTPUT: daftar email tersimpan (auto-load saat mulai)
├── Email.txt      # OUTPUT: mirror daftar email dalam teks biasa
└── otp.txt        # OUTPUT: hasil scrape kode OTP 6 digit
```

## Persiapan

1. **Python 3.10+** terpasang, tambahkan ke `PATH`.
2. Install dependensi:

```
pip install -r requirements.txt
```

3. Pastikan kamu punya koneksi internet — bot ini memakai API publik `https://cleantempmail.com` tanpa perlu API key. Kalau mau ganti server, ubah `BASE = "https://cleantempmail.com"` di `bot.py`.

## Cara Pakai

1. **Jalankan bot:**

```
python bot.py
```

2. **Pilih menu** yang muncul di terminal:

```
  1  Generate Email Baru
  2  Tambah Email Lama
  3  Cek Inbox
  4  Scrape Kode dari Inbox
  5  Auto Refresh Inbox
  6  Reset Semua Email
  0  Keluar
```

3. Contoh alur cepat:

   * Pilih menu **1** untuk membuat email baru (pilih mode: satu domain untuk semua, domain beda tiap email, atau random)
   * Pakai email itu untuk daftar di situs yang butuh verifikasi
   * Pilih menu **5** untuk memantau inbox real-time, atau menu **4** untuk langsung ambil semua kode OTP
   * Kode OTP tersimpan berurutan di `otp.txt`, sesuai urutan email di `emails.json`

## Catatan

* Maksimal 10 email tersimpan sekaligus. Kalau penuh, hapus beberapa lewat menu 2 (sub-menu 2) atau reset semua lewat menu 6.
* `emails.json` adalah penyimpanan utama — file `Email.txt` cuma mirror biar mudah dibaca/di-copy di luar program.
* Saat membaca email (menu 3), kode OTP yang ditemukan langsung ditampilkan dan ditambahkan ke `otp.txt`, sedangkan menu 4 menimpa `otp.txt` dengan kode dari email terbaru tiap inbox.
* Menu 5 berjalan terus (loop) sampai kamu tekan `Ctrl+C`; email baru ditandai badge `NEW`.
* Format email lama yang bisa ditambahkan di menu 2 harus mengandung `@` dan domain yang valid, contoh: `nama@domain.com`.

## Disclaimer

Gunakan sesuai ketentuan layanan `cleantempmail.com` dan situs tempat email dipakai. Penulis tidak bertanggung jawab atas penyalahgunaan maupun data yang terbaca melalui layanan email sementara ini.
