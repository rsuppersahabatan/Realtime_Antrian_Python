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
    │   ├── loket.py            # Loket CRUD REST API
    │   ├── groups.py           # Groups CRUD REST API
    │   ├── users.py            # Users CRUD REST API
    │   ├── antrian.py          # Antrian CRUD REST API
    │   └── panggilan.py        # Logika panggilan [TODO]
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

## Modul Loket — `/api/loket`

Modul `loket` mengelola data meja/loket counter petugas panggilan, status keaktifan buka/tutup loket, serta penugasan user ke loket tertentu.

### Daftar Endpoint

| Method   | Endpoint                 | Keterangan                                                                     |
| -------- | ------------------------ | ------------------------------------------------------------------------------ |
| `GET`    | `/api/loket`             | Mengambil list semua loket (termasuk relasi layanan & user ter-assign)         |
| `GET`    | `/api/loket/{id}`        | Mengambil rincian detail satu loket beserta user ter-assign                    |
| `GET`    | `/api/loket/buka`        | List loket yang sedang buka (opsional: `?with_last=1` untuk nomor antrian hari ini) |
| `GET`    | `/api/loket/users/{id}`  | Mendapatkan daftar user yang ter-assign ke loket                               |
| `POST`   | `/api/loket`             | Membuat loket baru (dapat menyertakan array user IDs `id_users`)              |
| `PUT`    | `/api/loket/status/{id}` | Update status buka/tutup loket                                                 |
| `PUT`    | `/api/loket/users/{id}`  | Sinkronisasi/replace-all penugasan user untuk loket                            |
| `DELETE` | `/api/loket/{id}`        | Menghapus loket                                                                |

---

## Modul Users — `/api/users`

Modul `users` menangani data pengguna/petugas (User Management), hashing password dengan bcrypt, dan relasi penugasan group.

### Daftar Endpoint

| Method   | Endpoint                     | Keterangan                                                                     |
| -------- | ---------------------------- | ------------------------------------------------------------------------------ |
| `GET`    | `/api/users`                 | Mengambil list semua user beserta details group masing-masing                  |
| `GET`    | `/api/users/{id}`            | Mengambil rincian detail satu user beserta details group                       |
| `POST`   | `/api/users`                 | Mendaftarkan user baru (IP otomatis terekam, password dihash, & assign groups) |
| `PUT`    | `/api/users/{id}`            | Update detail user (partial update data user & sinkronisasi group)            |
| `PUT`    | `/api/users/activate/{id}`   | Mengaktifkan status keaktifan user (`active = 1`)                              |
| `PUT`    | `/api/users/deactivate/{id}` | Menonaktifkan status keaktifan user (`active = 0`)                            |
| `DELETE` | `/api/users/{id}`            | Menghapus user                                                                 |

---

## Modul Groups — `/api/groups`

Modul `groups` menangani hak akses / role (Group Management via Ion Auth) beserta warna label background display TV.

### Daftar Endpoint

| Method   | Endpoint                 | Keterangan                                                                     |
| -------- | ------------------------ | ------------------------------------------------------------------------------ |
| `GET`    | `/api/groups`             | Mengambil list semua groups                                                    |
| `GET`    | `/api/groups/{id}`        | Mengambil rincian detail satu group                                            |
| `GET`    | `/api/groups/users/{id}`  | Mengambil daftar user yang termasuk ke dalam group tersebut                    |
| `POST`   | `/api/groups`             | Membuat group baru (nama group hanya alfanumerik & dash/underscore)            |
| `PUT`    | `/api/groups/{id}`        | Update data group (nama group `admin` dilindungi dari pengubahan/rename)       |
| `DELETE` | `/api/groups/{id}`        | Menghapus group (group `admin` dilindungi dari penghapusan)                   |

---

## Modul Antrian — `/api/antrian`

Modul `antrian` mengelola data transaksi antrian harian, pengambilan tiket baru, serta flow panggilan antrian loket.

### Daftar Endpoint

| Method   | Endpoint                       | Keterangan                                                                       |
| -------- | ------------------------------ | -------------------------------------------------------------------------------- |
| `GET`    | `/api/antrian`                 | Mengambil rekap status & list transaksi harian (opsional filter `?tanggal=`)     |
| `POST`   | `/api/antrian`                 | Membuat nomor antrian baru (menggenerate tiket harian, otomatis broadcast TV)    |
| `POST`   | `/api/antrian/call`            | Memanggil antrian berikutnya di loket tertentu (hanya DB, tanpa broadcast TV)   |
| `POST`   | `/api/antrian/panggilansimpan` | Menyimpan panggilan manual/panggil ulang (bisa mendeteksi panggilan ulang)       |
| `PUT`    | `/api/antrian/selesai/{id}`    | Mengupdate status antrian menjadi selesai                                         |
| `PUT`    | `/api/antrian/batal/{id}`      | Mengupdate status antrian menjadi batal                                           |
| `DELETE` | `/api/antrian/{id}`            | Menghapus record transaksi antrian                                               |

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
- [x] Driver & Database Integration (MySQL via PyMySQL & Cryptography)
- [x] Implementasi Modul `layanan` (FastAPI Router + Pydantic validation + PyMySQL)
- [x] Implementasi Modul `loket` (FastAPI Router + Pivot Users Sync + PyMySQL)
- [x] Implementasi Modul `users` (FastAPI Router + Bcrypt Hash + Groups Sync)
- [x] Implementasi Modul `groups` (FastAPI Router + Admin Protections)
- [x] Implementasi Modul `antrian` (FastAPI Router + Daily Reset + Socket.IO)
- [ ] Integrasi Realtime WebSocket (Socket.IO)
- [ ] Integrasi Audio Voice Generator (`edge-tts`/`piper-tts`)