import re
import datetime
from typing import Optional
from fastapi import APIRouter, Response, Request, status
from pydantic import BaseModel, Field
from enum import Enum
from .db import get_db_conn

# Enum for queue status
class StatusAntrianEnum(str, Enum):
    menunggu = "menunggu"
    dipanggil = "dipanggil"
    selesai = "selesai"
    batal = "batal"

# Pydantic schemas for request validation
class AntrianCreate(BaseModel):
    id_layanan: int = Field(..., description="ID layanan antrian (wajib)")
    nik: Optional[str] = Field(None, pattern=r"^\d{16}$", description="NIK 16 digit pengambil tiket (opsional)")
    keterangan: Optional[str] = Field(None, description="Keterangan tambahan (opsional)")
    nomor_antrian: Optional[str] = Field(None, description="Tiket manual override (opsional)")

class AntrianCall(BaseModel):
    id_loket: int = Field(..., description="ID loket pemanggil (wajib)")

class AntrianPanggilanSimpan(BaseModel):
    id_antrian: int = Field(..., description="ID antrian (wajib)")
    id_loket: int = Field(..., description="ID loket pemanggil (wajib)")

# API Router setup
router = APIRouter(prefix="/api/antrian", tags=["Antrian"])

# Helper function to format row dictionary
def format_row(row):
    if not row:
        return None
    res = dict(row)
    # Convert datetime/date/time objects to string formats
    for k, v in res.items():
        if hasattr(v, 'strftime'):
            if isinstance(v, datetime.date) and not isinstance(v, datetime.datetime):
                res[k] = v.strftime('%Y-%m-%d')
            else:
                res[k] = v.strftime('%Y-%m-%d %H:%M:%S')
    return res

# Broadcast Socket.IO event helper
async def broadcast_socket_message(request: Request, payload: str):
    try:
        sio = getattr(request.app.state, 'sio', None)
        if sio:
            await sio.emit('message', payload)
    except Exception as e:
        import sys
        print(f"Warning: Failed to broadcast Socket.IO message: {e}", file=sys.stderr)

@router.get("/")
def get_antrian(response: Response, tanggal: Optional[str] = None):
    """
    GET api/antrian -> list antrian hari ini dengan rekap summary
    Query: ?tanggal=YYYY-MM-DD (default hari ini)
    """
    if not tanggal or not re.match(r"^\d{4}-\d{2}-\d{2}$", tanggal):
        tanggal = datetime.date.today().strftime('%Y-%m-%d')
        
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # Query all queues for specific date with service & counter labels
            query = """
                SELECT a.*, l.kode_huruf, l.nama_layanan, lo.nama_loket 
                FROM antrian a 
                LEFT JOIN layanan l ON l.id = a.id_layanan 
                LEFT JOIN loket lo ON lo.id = a.id_loket 
                WHERE a.tanggal = %s 
                ORDER BY a.waktu_ambil ASC
            """
            cursor.execute(query, (tanggal,))
            rows = cursor.fetchall()
            
            data = [format_row(row) for row in rows]
            
            # Calculate rekap status
            rekap = {"menunggu": 0, "dipanggil": 0, "selesai": 0, "batal": 0}
            for d in data:
                status_val = d["status"]
                if status_val in rekap:
                    rekap[status_val] += 1
                    
            return {
                "status": True,
                "tanggal": tanggal,
                "rekap": rekap,
                "data": data
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal mengambil data antrian: {str(e)}"
        }
    finally:
        conn.close()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_antrian(request: Request, antrian_data: AntrianCreate, response: Response):
    """
    POST api/antrian -> generate nomor antrian baru
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # 1. Verify layanan exists to retrieve code prefix
            cursor.execute("SELECT kode_huruf FROM layanan WHERE id = %s", (antrian_data.id_layanan,))
            layanan_row = cursor.fetchone()
            if not layanan_row:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Gagal membuat antrian: layanan tidak ditemukan"
                }
            
            kode_huruf = layanan_row["kode_huruf"]
            tanggal = datetime.date.today().strftime('%Y-%m-%d')
            
            # 2. Get highest nomor_urut for today
            cursor.execute("""
                SELECT nomor_urut FROM antrian 
                WHERE id_layanan = %s AND tanggal = %s 
                ORDER BY nomor_urut DESC LIMIT 1
            """, (antrian_data.id_layanan, tanggal))
            last_antrian = cursor.fetchone()
            
            nomor_urut_baru = (last_antrian["nomor_urut"] + 1) if last_antrian else 1
            nomor_antrian_gabungan = f"{kode_huruf}{nomor_urut_baru}"
            
            # 3. Handle manual override if provided
            if antrian_data.nomor_antrian:
                nomor_antrian_manual = antrian_data.nomor_antrian.strip()
                if nomor_antrian_manual:
                    nomor_antrian_gabungan = nomor_antrian_manual
                    match = re.search(r'(\d+)', nomor_antrian_gabungan)
                    if match:
                        nomor_urut_baru = int(match.group(1))
            
            # 4. Insert queue record
            waktu_ambil = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sql = """
            INSERT INTO antrian (tanggal, id_layanan, nik, keterangan, nomor_antrian, nomor_urut, status, waktu_ambil)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                tanggal,
                antrian_data.id_layanan,
                antrian_data.nik if antrian_data.nik else None,
                antrian_data.keterangan if antrian_data.keterangan else None,
                nomor_antrian_gabungan,
                nomor_urut_baru,
                "menunggu",
                waktu_ambil
            ))
            new_id = cursor.lastrowid
            
            # 5. Broadcast new queue ticket event
            payload = f"antrian-baru-{antrian_data.id_layanan}-{nomor_antrian_gabungan}"
            if antrian_data.keterangan:
                # clean keterangan from newlines and pipes
                clean_ket = re.sub(r'[\r\n|]+', ' ', antrian_data.keterangan)
                clean_ket = re.sub(r'\s+', ' ', clean_ket).strip()
                if clean_ket:
                    payload += f"|{clean_ket}"
            
            await broadcast_socket_message(request, payload)
            
            # Return created ticket details
            cursor.execute("SELECT * FROM antrian WHERE id = %s", (new_id,))
            row = cursor.fetchone()
            return {
                "status": True,
                "message": "Nomor antrian berhasil dibuat",
                "data": format_row(row)
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal membuat antrian: {str(e)}"
        }
    finally:
        conn.close()

@router.post("/call")
def call_next(antrian_call: AntrianCall, response: Response):
    """
    POST api/antrian/call -> panggil antrian berikutnya di sebuah loket (tanpa broadcast display)
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # 1. Fetch counter details
            cursor.execute("SELECT id, id_layanan FROM loket WHERE id = %s", (antrian_call.id_loket,))
            loket = cursor.fetchone()
            if not loket:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Loket tidak ditemukan"
                }
            
            # 2. Query oldest 'menunggu' ticket for loket's service category today
            tanggal = datetime.date.today().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT * FROM antrian 
                WHERE id_layanan = %s AND tanggal = %s AND status = 'menunggu' 
                ORDER BY nomor_urut ASC LIMIT 1
            """, (loket["id_layanan"], tanggal))
            tiket = cursor.fetchone()
            
            if not tiket:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Tidak ada antrian yang menunggu untuk loket ini"
                }
                
            # 3. Update status to 'dipanggil'
            waktu_panggil = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                UPDATE antrian 
                SET status = 'dipanggil', id_loket = %s, waktu_panggil = %s 
                WHERE id = %s
            """, (antrian_call.id_loket, waktu_panggil, tiket["id"]))
            
            return {
                "status": True,
                "message": "Antrian berhasil dipanggil",
                "data": {
                    "id_loket": antrian_call.id_loket,
                    "nomor_antrian": tiket["nomor_antrian"],
                    "waktu_panggil": waktu_panggil
                }
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal memproses panggilan: {str(e)}"
        }
    finally:
        conn.close()

@router.post("/panggilansimpan")
def panggilan_simpan(panggilan: AntrianPanggilanSimpan, response: Response):
    """
    POST api/antrian/panggilansimpan -> simpan panggilan manual (manual / panggil ulang)
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # 1. Fetch antrian
            cursor.execute("SELECT * FROM antrian WHERE id = %s", (panggilan.id_antrian,))
            antrian_row = cursor.fetchone()
            if not antrian_row:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Antrian tidak ditemukan"
                }
                
            # 2. Fetch loket
            cursor.execute("SELECT id, nama_loket, id_layanan FROM loket WHERE id = %s", (panggilan.id_loket,))
            loket_row = cursor.fetchone()
            if not loket_row:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Loket tidak ditemukan"
                }
                
            # 3. Check service category mismatch
            if int(antrian_row["id_layanan"]) != int(loket_row["id_layanan"]):
                response.status_code = status.HTTP_409_CONFLICT
                return {
                    "status": False,
                    "message": "Loket ini tidak melayani layanan antrian tersebut"
                }
                
            # 4. Check status final
            if antrian_row["status"] in ["selesai", "batal"]:
                response.status_code = status.HTTP_409_CONFLICT
                return {
                    "status": False,
                    "message": "Antrian sudah selesai/batal dan tidak dapat dipanggil",
                    "data": format_row(antrian_row)
                }
                
            # 5. Check if recall/panggilan ulang
            is_ulang = antrian_row["status"] == "dipanggil"
            
            # 6. Update
            waktu_panggil = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                UPDATE antrian 
                SET status = 'dipanggil', id_loket = %s, waktu_panggil = %s 
                WHERE id = %s
            """, (panggilan.id_loket, waktu_panggil, panggilan.id_antrian))
            
            msg = "Panggilan ulang berhasil disimpan" if is_ulang else "Panggilan berhasil disimpan"
            return {
                "status": True,
                "message": msg,
                "data": {
                    "id_antrian": panggilan.id_antrian,
                    "nomor_antrian": antrian_row["nomor_antrian"],
                    "id_loket": panggilan.id_loket,
                    "nama_loket": loket_row["nama_loket"],
                    "waktu_panggil": waktu_panggil,
                    "is_ulang": is_ulang
                }
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal menyimpan panggilan: {str(e)}"
        }
    finally:
        conn.close()

def _update_status_db(id: int, target_status: str, response: Response):
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # Check if exists
            cursor.execute("SELECT * FROM antrian WHERE id = %s", (id,))
            row = cursor.fetchone()
            if not row:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Antrian tidak ditemukan"
                }
                
            # Perform update
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if target_status == "selesai":
                cursor.execute("UPDATE antrian SET status = %s, waktu_selesai = %s WHERE id = %s", (target_status, now_time, id))
                row["waktu_selesai"] = now_time
            else:
                cursor.execute("UPDATE antrian SET status = %s WHERE id = %s", (target_status, id))
                
            row["status"] = target_status
            return {
                "status": True,
                "message": f"Antrian berhasil diupdate ke status '{target_status}'",
                "data": format_row(row)
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal mengupdate status antrian: {str(e)}"
        }
    finally:
        conn.close()

@router.put("/selesai/{id}")
def mark_selesai(id: int, response: Response):
    """
    PUT api/antrian/selesai/{id} -> tandai antrian selesai
    """
    return _update_status_db(id, "selesai", response)

@router.put("/batal/{id}")
def mark_batal(id: int, response: Response):
    """
    PUT api/antrian/batal/{id} -> tandai antrian batal
    """
    return _update_status_db(id, "batal", response)

@router.delete("/{id}")
def delete_antrian(id: int, response: Response):
    """
    DELETE api/antrian/{id} -> hapus record antrian
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM antrian WHERE id = %s", (id,))
            if not cursor.fetchone():
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    "status": False,
                    "message": "Antrian tidak ditemukan"
                }
                
            cursor.execute("DELETE FROM antrian WHERE id = %s", (id,))
            return {
                "status": True,
                "message": "Antrian berhasil dihapus"
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": False,
            "message": f"Gagal menghapus record antrian: {str(e)}"
        }
    finally:
        conn.close()
