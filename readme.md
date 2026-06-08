## Donasi ❤

Klik link dibawah untuk mendukung pengembangan

[![Donate trakteer](https://img.shields.io/badge/Donate-Trakteer-red?style=for-the-badge&link=https%3A%2F%2Ftrakteer.id%2Fmdestafadilah%2Ftip&labelColor=%239f39b5&color=%2300bcd4)](https://trakteer.id/mdestafadilah/tip)
[![Donate saweria](https://img.shields.io/badge/Donate-Saweria-red?style=for-the-badge&link=https%3A%2F%2Fsaweria.co%2Fmdestafadilah&labelColor=%239f39b5&color=%2300bcd4)](https://saweria.co/mdestafadilah)

# Realtime Antrian — Python Version

Porting dari versi PHP (CodeIgniter 3) ke arsitektur modern berbasis **Python (FastAPI + Socket.IO)** dan **React (Vite + TanStack Router)** dengan database **MySQL**.

Sistem antrian realtime ini dirancang untuk rumah sakit, klinik, atau instansi pelayanan publik. Pengunjung dapat mengambil nomor antrian secara mandiri, petugas loket memanggil dari panel admin/panggilan, dan layar display TV terupdate secara instan tanpa refresh menggunakan WebSocket (Socket.IO).

---

## Tech Stack

1. **Backend**: FastAPI (Python 3.9+)
2. **Database**: MySQL (Koneksi via `pymysql` dan `cryptography`)
3. **Realtime Gateway**: `fastapi-socketio` (WebSocket Socket.IO terintegrasi langsung dengan FastAPI)
4. **Text-To-Speech (TTS)**: Microsoft `edge-tts` & `piper-tts` (untuk pemanggilan suara nomor antrian otomatis)
5. **Frontend**: React + Vite + Tailwind CSS + TanStack Router (Start)

---

## Struktur Folder

```
Realtime_Antrian_Python/
├── client/                     # Frontend App (React + Vite + TanStack Start)
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── routes/             # Client-side file-based routes
│   │   └── pages/              # Halaman Login, Blank, 404, dll.
│   └── package.json
└── server/                     # Backend App (FastAPI)
    ├── examples/
    │   └── app.py              # Launch entry point & dev server
    ├── fastapi_socketio/       # Library Socket.IO integration
    ├── modules/                # Domain modular backend
    │   ├── db.py               # Database manager (MySQL connection helper)
    │   ├── layanan.py          # Layanan CRUD REST API
    │   ├── loket.py            # Loket API (petugas counter) [TODO]
    │   ├── antrian.py          # Transaksi antrian harian [TODO]
    │   ├── panggilan.py        # Logika panggilan [TODO]
    │   └── users.py            # User management [TODO]
    ├── requirements.txt        # PIP dependencies
    └── setup.py                # Package installer
```

---

## Modul Layanan — `/api/layanan`

Modul `layanan` menangani data master jenis layanan (kategori antrian) beserta prefix kode hurufnya (misal: A = Loket Pendaftaran, B = Kasir).

### Daftar Endpoint

| Method   | Endpoint             | Keterangan                                                             |
| -------- | -------------------- | ---------------------------------------------------------------------- |
| `GET`    | `/api/layanan`       | Mengambil list semua jenis layanan                                     |
| `GET`    | `/api/layanan/{id}`  | Mengambil rincian detail satu layanan berdasarkan ID                   |
| `POST`   | `/api/layanan`       | Membuat layanan baru. Body: `kode_huruf`, `nama_layanan`, `keterangan?` |
| `PUT`    | `/api/layanan/{id}`  | Update sebagian field layanan                                          |
| `DELETE` | `/api/layanan/{id}`  | Menghapus layanan                                                      |

---

## Cara Menjalankan

### Menggunakan Docker Compose (Direkomendasikan)

1. Pastikan docker engine sudah aktif.
2. Setup file `.env` di root/server (menggunakan credential MySQL dan port yang sesuai).
3. Jalankan command:
   ```bash
   docker-compose up --build -d
   ```

### Menjalankan Manual di Lokal (Dev)

#### 1. Jalankan Backend (FastAPI)
1. Buka folder `server/` dan pastikan dependensi sudah terinstal:
   ```bash
   pip install -r requirements.txt
   ```
2. Pastikan database MySQL server Anda aktif dan buat database bernama `antrian_db`.
3. Atur environment variables Anda atau buat berkas `.env` di dalam folder `server/`:
   ```env
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PASS=toor
   DB_NAME=antrian_db
   ```
4. Jalankan FastAPI server:
   ```bash
   python examples/app.py
   ```
   Server backend akan berjalan di: `http://localhost:8000`

#### 2. Jalankan Frontend (React)
1. Buka folder `client/` di terminal baru.
2. Instal dependensi node:
   ```bash
   npm install
   ```
3. Jalankan Vite dev server:
   ```bash
   npm run dev
   ```
   Frontend akan berjalan di: `http://localhost:3000`

---

## Pengembangan / Roadmap Status

- [x] Inisialisasi Project (Setup FastAPI & React template)
- [x] Instalasi Driver & Integrasi Database MySQL
- [x] Implementasi Modul `layanan` (FastAPI Router + Pydantic validation + PyMySQL)
- [ ] Implementasi Modul `loket`
- [ ] Implementasi Modul `antrian`
- [ ] Integrasi Realtime WebSocket (Socket.IO)
- [ ] Integrasi Audio Voice Generator (`edge-tts`/`piper-tts`)