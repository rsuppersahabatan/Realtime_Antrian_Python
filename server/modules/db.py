import os
import pymysql
import pymysql.cursors

def load_env():
    # Try to find .env file in server dir or parent dir
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
        ".env"
    ]
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key and key not in os.environ:
                            os.environ[key] = val
            break

# Load env file variables
load_env()

def get_db_conn():
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port_str = os.environ.get("DB_PORT", os.environ.get("MYSQL_PORT", "3306"))
    try:
        port = int(port_str)
    except ValueError:
        port = 3306
        
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASS", os.environ.get("MYSQL_ROOT_PASSWORD", "toor"))
    db = os.environ.get("DB_NAME", "antrian_db")
    
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
    return conn

def init_db():
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port_str = os.environ.get("DB_PORT", os.environ.get("MYSQL_PORT", "3306"))
    try:
        port = int(port_str)
    except ValueError:
        port = 3306
        
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASS", os.environ.get("MYSQL_ROOT_PASSWORD", "toor"))
    db = os.environ.get("DB_NAME", "antrian_db")
    
    # First connect without database to ensure DB exists
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset='utf8mb4',
        autocommit=True
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
    finally:
        conn.close()
        
    # Connect to the database and create tables
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `layanan` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `kode_huruf` varchar(5) NOT NULL COMMENT 'Misal: A, B, CS',
              `nama_layanan` varchar(100) NOT NULL COMMENT 'Misal: Poli Umum, Kasir',
              `keterangan` text DEFAULT NULL,
              `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
              `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              `show_welcome` enum('ya','tidak') NOT NULL DEFAULT 'tidak',
              PRIMARY KEY (`id`),
              UNIQUE KEY `kode_huruf` (`kode_huruf`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `users` (
              `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
              `username` varchar(100) NOT NULL,
              `password` varchar(255) NOT NULL,
              `email` varchar(100) NOT NULL,
              `first_name` varchar(50) DEFAULT NULL,
              `last_name` varchar(50) DEFAULT NULL,
              `active` tinyint(1) unsigned DEFAULT NULL,
              PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `loket` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `id_layanan` int(11) NOT NULL COMMENT 'Loket ini melayani layanan apa?',
              `nama_loket` varchar(50) NOT NULL COMMENT 'Misal: Loket 01, Kasir 01',
              `status_buka` enum('buka','tutup') DEFAULT 'tutup',
              `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
              `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              KEY `id_layanan` (`id_layanan`),
              CONSTRAINT `loket_ibfk_1` FOREIGN KEY (`id_layanan`) REFERENCES `layanan` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `loket_user` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `id_loket` int(11) NOT NULL,
              `id_user` int(11) unsigned NOT NULL,
              PRIMARY KEY (`id`),
              UNIQUE KEY `unique_loket_user` (`id_loket`, `id_user`),
              CONSTRAINT `fk_loket_user_loket` FOREIGN KEY (`id_loket`) REFERENCES `loket`(`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_loket_user_user` FOREIGN KEY (`id_user`) REFERENCES `users`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `groups` (
              `id` mediumint(8) UNSIGNED NOT NULL AUTO_INCREMENT,
              `name` varchar(20) NOT NULL,
              `description` varchar(100) NOT NULL,
              `bgcolor` char(7) NOT NULL DEFAULT '#607D8B',
              PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `users_groups` (
              `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
              `user_id` int(11) unsigned NOT NULL,
              `group_id` mediumint(8) unsigned NOT NULL,
              PRIMARY KEY (`id`),
              UNIQUE KEY `uc_users_groups` (`user_id`,`group_id`),
              KEY `fk_users_groups_users1_idx` (`user_id`),
              KEY `fk_users_groups_groups1_idx` (`group_id`),
              CONSTRAINT `fk_users_groups_groups1` FOREIGN KEY (`group_id`) REFERENCES `groups` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION,
              CONSTRAINT `fk_users_groups_users1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `antrian` (
              `id` bigint(20) NOT NULL AUTO_INCREMENT,
              `tanggal` date NOT NULL COMMENT 'Tanggal antrian terjadi (untuk reset harian)',
              `id_layanan` int(11) NOT NULL,
              `nomor_antrian` varchar(20) NOT NULL COMMENT 'Nomor urut gabungan (Misal: A12)',
              `nomor_urut` int(11) NOT NULL COMMENT 'Angka murninya saja (Misal: 12)',
              `status` enum('menunggu','dipanggil','selesai','batal') DEFAULT 'menunggu',
              `id_loket` int(11) DEFAULT NULL COMMENT 'Loket mana yang memanggil antrian ini',
              `waktu_ambil` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `waktu_panggil` datetime DEFAULT NULL,
              `waktu_selesai` datetime DEFAULT NULL,
              `nik` varchar(16) DEFAULT NULL,
              `keterangan` text DEFAULT NULL,
              PRIMARY KEY (`id`),
              KEY `id_layanan` (`id_layanan`),
              KEY `id_loket` (`id_loket`),
              KEY `idx_tanggal` (`tanggal`),
              KEY `idx_status` (`status`),
              CONSTRAINT `antrian_ibfk_1` FOREIGN KEY (`id_layanan`) REFERENCES `layanan` (`id`) ON DELETE CASCADE,
              CONSTRAINT `antrian_ibfk_2` FOREIGN KEY (`id_loket`) REFERENCES `loket` (`id`) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """)
    finally:
        conn.close()

# Auto-initialize database on import
try:
    init_db()
except Exception as e:
    import sys
    print(f"Warning: Database initialization failed: {e}", file=sys.stderr)
