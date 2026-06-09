from typing import List, Optional
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from enum import Enum
from database.dbmysql import get_db_conn


# ---------------------------------------------------------------------------
# Enums & Schemas
# ---------------------------------------------------------------------------
class StatusBukaEnum(str, Enum):
    buka = "buka"
    tutup = "tutup"


class LoketCreate(BaseModel):
    id_layanan: int = Field(..., gt=0, description="ID layanan yang dilayani oleh loket ini")
    nama_loket: str = Field(..., min_length=1, max_length=50,
                            description="Nama loket, misal: Loket 01, Kasir 01")
    status_buka: StatusBukaEnum = Field(StatusBukaEnum.tutup,
                                        description="Status buka/tutup loket")
    id_users: Optional[List[int]] = Field(default=None,
                                          description="Daftar ID user yang di-assign ke loket ini")


class LoketUpdate(BaseModel):
    """Partial update — kirim hanya field yang ingin diubah."""
    id_layanan: Optional[int] = Field(None, gt=0)
    nama_loket: Optional[str] = Field(None, min_length=1, max_length=50)
    status_buka: Optional[StatusBukaEnum] = None
    id_users: Optional[List[int]] = Field(None,
                                          description="Jika diisi: replace-all daftar user assignment")


class LoketStatusUpdate(BaseModel):
    status_buka: StatusBukaEnum = Field(..., description="Status buka/tutup loket yang baru")


class LoketUsersUpdate(BaseModel):
    id_users: List[int] = Field(..., description="Daftar ID user untuk sinkronisasi assignment")


# ---------------------------------------------------------------------------
# API Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/loket", tags=["Loket"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def format_row(row):
    if not row:
        return None
    res = dict(row)
    for k, v in res.items():
        if hasattr(v, "strftime"):
            res[k] = v.strftime("%Y-%m-%d %H:%M:%S")
    return res


def _dedup_positive_ids(ids: Optional[List[int]]) -> List[int]:
    """Buang duplikat & nilai non-positif. Pertahankan urutan stabil."""
    if not ids:
        return []
    seen = set()
    out = []
    for i in ids:
        if isinstance(i, int) and i > 0 and i not in seen:
            seen.add(i)
            out.append(i)
    return out


def validate_user_ids(cursor, user_ids: List[int]) -> List[int]:
    """Return list ID user yang TIDAK ditemukan di tabel users."""
    if not user_ids:
        return []
    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(f"SELECT id FROM users WHERE id IN ({placeholders})", tuple(user_ids))
    existing = {row["id"] for row in cursor.fetchall()}
    return [uid for uid in user_ids if uid not in existing]


def validate_layanan_id(cursor, id_layanan: int) -> bool:
    cursor.execute("SELECT id FROM layanan WHERE id = %s", (id_layanan,))
    return cursor.fetchone() is not None


def _sync_loket_users(cursor, id_loket: int, id_users: List[int], replace: bool = True):
    """
    Sinkronkan assignment user ke loket.
      - replace=True  : hapus semua assignment lama lalu insert id_users baru
      - replace=False : hanya tambah id_users (idempotent via INSERT IGNORE)
    Caller wajib memastikan id_users sudah di-validate (gunakan validate_user_ids).
    """
    if replace:
        cursor.execute("DELETE FROM loket_user WHERE id_loket = %s", (id_loket,))
    if id_users:
        rows = [(id_loket, uid) for uid in id_users]
        cursor.executemany(
            "INSERT IGNORE INTO loket_user (id_loket, id_user) VALUES (%s, %s)",
            rows,
        )


# ---------------------------------------------------------------------------
# DB queries untuk fetch loket beserta user-nya
# ---------------------------------------------------------------------------
def get_counter_by_id_db(conn, id: int):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT loket.*, layanan.nama_layanan, layanan.kode_huruf
            FROM loket
            LEFT JOIN layanan ON layanan.id = loket.id_layanan
            WHERE loket.id = %s
        """, (id,))
        row = cursor.fetchone()
        if not row:
            return None

        d = format_row(row)
        cursor.execute("""
            SELECT u.id, u.username, u.first_name, u.last_name, u.email
            FROM loket_user lu
            INNER JOIN users u ON u.id = lu.id_user
            WHERE lu.id_loket = %s
            ORDER BY u.username ASC
        """, (id,))
        d["users"] = [dict(ur) for ur in cursor.fetchall()]
        return d


def get_all_counters_db(conn):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT loket.*, layanan.nama_layanan, layanan.kode_huruf
            FROM loket
            LEFT JOIN layanan ON layanan.id = loket.id_layanan
            ORDER BY loket.id ASC
        """)
        rows = cursor.fetchall()
        if not rows:
            return []

        data = [format_row(row) for row in rows]
        loket_ids = [d["id"] for d in data]

        if loket_ids:
            placeholders = ",".join(["%s"] * len(loket_ids))
            cursor.execute(f"""
                SELECT lu.id_loket, u.id, u.username, u.first_name, u.last_name, u.email
                FROM loket_user lu
                INNER JOIN users u ON u.id = lu.id_user
                WHERE lu.id_loket IN ({placeholders})
                ORDER BY u.username ASC
            """, tuple(loket_ids))
            users_by_loket = {}
            for u_row in cursor.fetchall():
                u_dict = dict(u_row)
                lid = u_dict.pop("id_loket")
                users_by_loket.setdefault(lid, []).append(u_dict)

            for d in data:
                d["users"] = users_by_loket.get(d["id"], [])
        else:
            for d in data:
                d["users"] = []

        return data


# ---------------------------------------------------------------------------
# GET /api/loket -> list semua loket (+ users)
# ---------------------------------------------------------------------------
@router.get("/")
def get_all_loket(response: Response):
    conn = get_db_conn()
    try:
        return {"status": True, "data": get_all_counters_db(conn)}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal mengambil data loket: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/loket/buka -> list loket yang sedang buka (+opsional nomor terakhir)
# ---------------------------------------------------------------------------
@router.get("/buka")
def get_loket_buka(response: Response, with_last: int = 0, tanggal: Optional[str] = None):
    """
    Query:
      ?with_last=1               -> sertakan nomor_terakhir & keterangan_terakhir
      ?tanggal=YYYY-MM-DD        -> custom tanggal (default: hari ini)
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            if with_last == 1:
                if not tanggal:
                    import datetime
                    tanggal = datetime.date.today().strftime("%Y-%m-%d")
                cursor.execute("""
                    SELECT loket.*, layanan.nama_layanan, layanan.kode_huruf,
                    (SELECT a.nomor_antrian FROM antrian a
                     WHERE a.id_loket = loket.id
                       AND a.tanggal = %s
                       AND a.waktu_panggil IS NOT NULL
                     ORDER BY a.waktu_panggil DESC LIMIT 1) AS nomor_terakhir,
                    (SELECT a.keterangan FROM antrian a
                     WHERE a.id_loket = loket.id
                       AND a.tanggal = %s
                       AND a.waktu_panggil IS NOT NULL
                     ORDER BY a.waktu_panggil DESC LIMIT 1) AS keterangan_terakhir
                    FROM loket
                    LEFT JOIN layanan ON layanan.id = loket.id_layanan
                    WHERE loket.status_buka = 'buka'
                    ORDER BY loket.id ASC
                """, (tanggal, tanggal))
            else:
                cursor.execute("""
                    SELECT loket.*, layanan.nama_layanan, layanan.kode_huruf, layanan.show_welcome
                    FROM loket
                    LEFT JOIN layanan ON layanan.id = loket.id_layanan
                    WHERE loket.status_buka = 'buka'
                    ORDER BY loket.id ASC
                """)
            rows = cursor.fetchall()
            return {"status": True, "data": [format_row(r) for r in rows]}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal mengambil data loket buka: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/loket/by-user/{id_user} -> list loket yang di-assign ke seorang user
# ---------------------------------------------------------------------------
@router.get("/by-user/{id_user}")
def get_loket_by_user(id_user: int, response: Response):
    """
    Berguna setelah login: tampilkan daftar loket yang boleh dilayani user ini.
    """
    if id_user <= 0:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"status": False, "message": "id_user tidak valid"}

    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (id_user,))
            if not cursor.fetchone():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"status": False, "message": "User tidak ditemukan"}

            cursor.execute("""
                SELECT loket.*, layanan.nama_layanan, layanan.kode_huruf
                FROM loket_user lu
                INNER JOIN loket ON loket.id = lu.id_loket
                LEFT JOIN layanan ON layanan.id = loket.id_layanan
                WHERE lu.id_user = %s
                ORDER BY loket.id ASC
            """, (id_user,))
            rows = cursor.fetchall()
            return {
                "status": True,
                "id_user": id_user,
                "data": [format_row(r) for r in rows],
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal mengambil loket per user: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/loket/{id} -> detail loket (+ users)
# ---------------------------------------------------------------------------
@router.get("/{id}")
def get_loket_by_id(id: int, response: Response):
    conn = get_db_conn()
    try:
        data = get_counter_by_id_db(conn, id)
        if not data:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"status": False, "message": "Loket tidak ditemukan"}
        return {"status": True, "data": data}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal mengambil detail loket: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/loket/users/{id} -> list user yang ter-assign ke loket
# ---------------------------------------------------------------------------
@router.get("/users/{id}")
def get_loket_users(id: int, response: Response):
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM loket WHERE id = %s", (id,))
            if not cursor.fetchone():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"status": False, "message": "Loket tidak ditemukan"}

            cursor.execute("""
                SELECT u.id, u.username, u.first_name, u.last_name, u.email
                FROM loket_user lu
                INNER JOIN users u ON u.id = lu.id_user
                WHERE lu.id_loket = %s
                ORDER BY u.username ASC
            """, (id,))
            return {
                "status": True,
                "id_loket": id,
                "data": [dict(ur) for ur in cursor.fetchall()],
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal mengambil user loket: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /api/loket -> tambah loket baru
# ---------------------------------------------------------------------------
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_loket(loket: LoketCreate, response: Response):
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            if not validate_layanan_id(cursor, loket.id_layanan):
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {"status": False, "message": "id_layanan tidak valid / layanan tidak ditemukan"}

            user_ids = _dedup_positive_ids(loket.id_users)
            if user_ids:
                invalid = validate_user_ids(cursor, user_ids)
                if invalid:
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return {
                        "status": False,
                        "message": "id_users mengandung user yang tidak valid",
                        "invalid": invalid,
                    }

            cursor.execute("""
                INSERT INTO loket (id_layanan, nama_loket, status_buka)
                VALUES (%s, %s, %s)
            """, (loket.id_layanan, loket.nama_loket, loket.status_buka.value))
            new_id = cursor.lastrowid

            _sync_loket_users(cursor, new_id, user_ids, replace=False)

            return {
                "status": True,
                "message": "Loket berhasil ditambahkan",
                "data": get_counter_by_id_db(conn, new_id),
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal menambahkan loket: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# PUT /api/loket/{id} -> partial-update info loket (+ optional sync users)
# ---------------------------------------------------------------------------
@router.put("/{id}")
def update_loket(id: int, body: LoketUpdate, response: Response):
    """
    Update parsial. Kirim hanya field yang ingin diubah.
    Bila `id_users` diisi (termasuk list kosong), assignment user di-replace.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM loket WHERE id = %s", (id,))
            if not cursor.fetchone():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"status": False, "message": "Loket tidak ditemukan"}

            patch = body.model_dump(exclude_unset=True)
            id_users_patch = patch.pop("id_users", None)  # None vs list — beda perlakuan
            replace_users = id_users_patch is not None

            if not patch and not replace_users:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {"status": False, "message": "Tidak ada field yang diupdate"}

            # Validate id_layanan jika di-patch
            if "id_layanan" in patch:
                if not validate_layanan_id(cursor, patch["id_layanan"]):
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return {"status": False, "message": "id_layanan tidak valid"}

            # Validate id_users jika di-patch
            user_ids = _dedup_positive_ids(id_users_patch) if replace_users else []
            if replace_users and user_ids:
                invalid = validate_user_ids(cursor, user_ids)
                if invalid:
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return {
                        "status": False,
                        "message": "id_users mengandung user yang tidak valid",
                        "invalid": invalid,
                    }

            # Update kolom-kolom loket
            if patch:
                # Convert enum value bila ada
                if "status_buka" in patch and hasattr(patch["status_buka"], "value"):
                    patch["status_buka"] = patch["status_buka"].value
                set_clauses = ", ".join([f"`{k}` = %s" for k in patch.keys()])
                values = list(patch.values()) + [id]
                cursor.execute(f"UPDATE loket SET {set_clauses} WHERE id = %s", tuple(values))

            # Sync users (replace-all) bila diminta
            if replace_users:
                _sync_loket_users(cursor, id, user_ids, replace=True)

            return {
                "status": True,
                "message": "Loket berhasil diupdate",
                "data": get_counter_by_id_db(conn, id),
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal mengupdate loket: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# PUT /api/loket/status/{id} -> update status buka/tutup saja
# ---------------------------------------------------------------------------
@router.put("/status/{id}")
def update_loket_status(id: int, status_update: LoketStatusUpdate, response: Response):
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM loket WHERE id = %s", (id,))
            if not cursor.fetchone():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"status": False, "message": "Loket tidak ditemukan"}

            cursor.execute(
                "UPDATE loket SET status_buka = %s WHERE id = %s",
                (status_update.status_buka.value, id),
            )
            return {
                "status": True,
                "message": "Status loket berhasil diupdate",
                "data": get_counter_by_id_db(conn, id),
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal mengupdate status loket: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# PUT /api/loket/users/{id} -> sinkronisasi assignment user (replace-all)
# ---------------------------------------------------------------------------
@router.put("/users/{id}")
def update_loket_users(id: int, users_update: LoketUsersUpdate, response: Response):
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM loket WHERE id = %s", (id,))
            if not cursor.fetchone():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"status": False, "message": "Loket tidak ditemukan"}

            user_ids = _dedup_positive_ids(users_update.id_users)
            if user_ids:
                invalid = validate_user_ids(cursor, user_ids)
                if invalid:
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return {
                        "status": False,
                        "message": "id_users mengandung user yang tidak valid",
                        "invalid": invalid,
                    }

            _sync_loket_users(cursor, id, user_ids, replace=True)

            return {
                "status": True,
                "message": "User loket berhasil disinkronkan",
                "data": get_counter_by_id_db(conn, id),
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal menyinkronkan user loket: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# DELETE /api/loket/{id} -> hapus loket (cascade ke loket_user via FK)
# ---------------------------------------------------------------------------
@router.delete("/{id}")
def delete_loket(id: int, response: Response):
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM loket WHERE id = %s", (id,))
            if not cursor.fetchone():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"status": False, "message": "Loket tidak ditemukan"}

            cursor.execute("DELETE FROM loket WHERE id = %s", (id,))
            return {"status": True, "message": "Loket berhasil dihapus"}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal menghapus loket: {str(e)}"}
    finally:
        conn.close()
