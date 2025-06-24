import sqlite3

DATABASE_NAME = "myappdb.db"

def get_db_connection():
    """Membuka koneksi ke database SQLite."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Mengembalikan hasil dalam bentuk dictionary
    return conn

def get_db():
    conn = get_db_connection()
    return conn.cursor()

def create_tables():
    """Membuat tabel jika belum ada dalam database."""
    conn = get_db_connection()
    c = conn.cursor()

    # Tabel Users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT NULL
        )
    ''')

    # Tabel Products
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            image TEXT NOT NULL
        )
    ''')
    # Buat tabel funding_requests jika belum ada
    # Buat tabel crowdfunding_requests jika belum ada
    c.execute('''
        CREATE TABLE IF NOT EXISTS crowdfunding_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            investy_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            document TEXT,
            created_at TEXT,
            cover_image TEXT,
            FOREIGN KEY (investy_id) REFERENCES users(id)
        )
    ''')

    #LAPORAN INVEST
    c.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investy_id INTEGER,
            investy_name TEXT,       -- Tambahan
            investor_id INTEGER,     -- Tambahan
            investor_name TEXT,      -- Tambahan
            amount REAL,
            description TEXT,
            document TEXT,
            investment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Tambahan
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (investy_id) REFERENCES users (id),
            FOREIGN KEY (investor_id) REFERENCES users (id)  -- Tambahan
        );
    """)
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme TEXT DEFAULT 'Terang',
            notifications TEXT DEFAULT 'Aktif'
        )
    ''')
    # Masukkan data default jika belum ada
    c.execute('SELECT COUNT(*) FROM admin_settings')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO admin_settings (theme, notifications) VALUES (?, ?)', ('Terang', 'Aktif'))


    conn.commit()
    conn.close()
 