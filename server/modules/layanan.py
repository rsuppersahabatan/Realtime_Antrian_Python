from typing import Optional
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from enum import Enum
from .db import get_db_conn

# Enum for show_welcome field
class ShowWelcomeEnum(str, Enum):
    ya = "ya"
    tidak = "tidak"

# Pydantic schemas for request validation
class LayananCreate(BaseModel):
    kode_huruf: str = Field(..., min_length=1, max_length=5, description="Prefix kode antrian, misal: A, B, CS")
    nama_layanan: str = Field(..., min_length=1, max_length=100, description="Nama layanan, misal: Poli Umum, Kasir")
    keterangan: Optional[str] = Field(None, description="Deskripsi/keterangan tambahan")
    show_welcome: ShowWelcomeEnum = Field(ShowWelcomeEnum.tidak, description="Tampilkan layanan di layar depan/welcome")

class LayananUpdate(BaseModel):
    kode_huruf: Optional[str] = Field(None, min_length=1, max_length=5)
    nama_layanan: Optional[str] = Field(None, min_length=1, max_length=100)
    keterangan: Optional[str] = None
    show_welcome: Optional[ShowWelcomeEnum] = None

# API Router setup
router = APIRouter(prefix="/api/layanan", tags=["Layanan"])

# Helper function to format row dictionary
def format_row(row):
    if not row:
        return None
    res = dict(row)
    # Convert datetime objects to string 'YYYY-MM-DD HH:MM:SS'
    for k, v in res.items():
        if hasattr(v, 'strftime'):
            res[k] = v.strftime('%Y-%m-%d %H:%M:%S')
    return res

@router.get("/")
def get_all_layanan(response: Response):
    """
    GET api/layanan -> list semua layanan
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM layanan ORDER BY id ASC")
            rows = cursor.fetchall()
            data = [format_row(row) for row in rows]
            return {
                "status": True,
                "data": data
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal mengambil data layanan: {str(e)}"
        }
    finally:
        conn.close()

@router.get("/{id}")
def get_layanan_by_id(id: int, response: Response):
    """
    GET api/layanan/{id} -> detail satu layanan
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM layanan WHERE id = %s", (id,))
            row = cursor.fetchone()
            if not row:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Layanan tidak ditemukan"
                }
            return {
                "status": True,
                "data": format_row(row)
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal mengambil detail layanan: {str(e)}"
        }
    finally:
        conn.close()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_layanan(layanan: LayananCreate, response: Response):
    """
    POST api/layanan -> tambah layanan baru
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # Check for duplicate kode_huruf
            cursor.execute("SELECT id FROM layanan WHERE kode_huruf = %s", (layanan.kode_huruf,))
            if cursor.fetchone():
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    "status": False,
                    "message": "Gagal menambah layanan (cek duplikasi kode_huruf)"
                }
            
            # Insert into database
            sql = """
            INSERT INTO layanan (kode_huruf, nama_layanan, keterangan, show_welcome)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                layanan.kode_huruf,
                layanan.nama_layanan,
                layanan.keterangan,
                layanan.show_welcome.value
            ))
            new_id = cursor.lastrowid
            
            # Fetch inserted data
            cursor.execute("SELECT * FROM layanan WHERE id = %s", (new_id,))
            row = cursor.fetchone()
            
            return {
                "status": True,
                "message": "Layanan berhasil ditambahkan",
                "data": format_row(row)
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal menambahkan layanan: {str(e)}"
        }
    finally:
        conn.close()

@router.put("/{id}")
def update_layanan(id: int, layanan: LayananUpdate, response: Response):
    """
    PUT api/layanan/{id} -> update layanan
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # Check if layanan exists
            cursor.execute("SELECT * FROM layanan WHERE id = %s", (id,))
            existing = cursor.fetchone()
            if not existing:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Layanan tidak ditemukan"
                }
            
            # Filter fields to update
            update_data = layanan.model_dump(exclude_unset=True)
            if not update_data:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    "status": False,
                    "message": "Tidak ada field yang diupdate"
                }
            
            # If updating kode_huruf, check for uniqueness
            if "kode_huruf" in update_data and update_data["kode_huruf"] != existing["kode_huruf"]:
                cursor.execute("SELECT id FROM layanan WHERE kode_huruf = %s AND id != %s", (update_data["kode_huruf"], id))
                if cursor.fetchone():
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return {
                        "status": False,
                        "message": "Gagal mengupdate layanan (cek duplikasi kode_huruf)"
                    }
            
            # Perform update
            fields = []
            values = []
            for k, v in update_data.items():
                fields.append(f"`{k}` = %s")
                if isinstance(v, ShowWelcomeEnum):
                    values.append(v.value)
                else:
                    values.append(v)
            values.append(id)
            
            sql = f"UPDATE layanan SET {', '.join(fields)} WHERE id = %s"
            cursor.execute(sql, tuple(values))
            
            # Fetch updated row
            cursor.execute("SELECT * FROM layanan WHERE id = %s", (id,))
            updated_row = cursor.fetchone()
            
            return {
                "status": True,
                "message": "Layanan berhasil diupdate",
                "data": format_row(updated_row)
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal mengupdate layanan: {str(e)}"
        }
    finally:
        conn.close()

@router.delete("/{id}")
def delete_layanan(id: int, response: Response):
    """
    DELETE api/layanan/{id} -> hapus layanan
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # Check if layanan exists
            cursor.execute("SELECT id FROM layanan WHERE id = %s", (id,))
            if not cursor.fetchone():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Layanan tidak ditemukan"
                }
            
            # Delete row
            cursor.execute("DELETE FROM layanan WHERE id = %s", (id,))
            return {
                "status": True,
                "message": "Layanan berhasil dihapus"
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal menghapus layanan: {str(e)}"
        }
    finally:
        conn.close()
