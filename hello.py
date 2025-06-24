from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
from routes.user_routes import user_routes  # Import dari file routes.py
from database import get_db_connection, create_tables
from datetime import datetime
from collections import Counter
from functools import wraps
from flask import session, redirect, url_for, flash
from routes.bank_routes import bank_routes



app = Flask(__name__)
app.config['SECRET_KEY'] = '1111'
DATABASE = 'myappdb.db'
# Register blueprint
app.register_blueprint(user_routes)
app.register_blueprint(bank_routes)


import os
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    from functools import wraps
    from flask import session

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/verifikasi_pembiayaan')
@admin_required
def verifikasi_pembiayaan():
    conn = get_db_connection()
    pengajuan = conn.execute("SELECT * FROM funding_request WHERE status = 'pending'").fetchall()
    conn.close()
    return render_template('verifikasi_pembiayaan.html', pengajuan=pengajuan)

@app.route('/setujui_pembiayaan/<int:id>')
@admin_required
def setujui_pembiayaan(id):
    conn = get_db_connection()
    conn.execute("UPDATE funding_request SET status = 'approved' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('verifikasi_pembiayaan'))

@app.route('/tolak_pembiayaan/<int:id>')
@admin_required
def tolak_pembiayaan(id):
    conn = get_db_connection()
    conn.execute("UPDATE funding_request SET status = 'rejected' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('verifikasi_pembiayaan'))

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') != role:
                flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/dashboard_bank/validasi_pengguna', methods=['GET', 'POST'])
@role_required('bank')
def validasi_pengguna_bank():
    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        user_id = request.form['user_id']
        action = request.form['action']

        if action == "accept":
            cursor.execute("UPDATE users SET status='verified' WHERE id=?", (user_id,))
        elif action == "reject":
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))

        conn.commit()

    cursor.execute("SELECT id, fullname, email, role FROM users WHERE status IS NULL AND role NOT IN ('admin', 'bank')")
    users = cursor.fetchall()
    conn.close()

    return render_template('validasi_pengguna_bank.html', users=users)


@app.route('/')
def home():
    """Halaman utama."""
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registrasi pengguna baru."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        fullname = request.form['fullname']
        phone = request.form['phone']
        role = request.form['role']  # Pilihan dari form (investor/investy)

        if role not in ['investor', 'investy']:
            flash('Role tidak valid.')
            return redirect(url_for('register'))

        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = c.fetchone()

            if user:
                flash('Email sudah terdaftar!')
                return redirect(url_for('register'))

            c.execute('INSERT INTO users (email, password, fullname, phone, role) VALUES (?, ?, ?, ?, ?)',
                      (email, password, fullname, phone, role))
            conn.commit()
            flash('Registrasi berhasil! Silakan login.')
            return redirect(url_for('login', role=role))
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            flash('Terjadi kesalahan saat registrasi.')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login berdasarkan role (admin, investor, investy, bank)."""
    role = request.args.get('role')

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ? AND role = ?", (email, password, role))
        user = cursor.fetchone()
        conn.close()

        if user:
            session.clear()  # Membersihkan session sebelumnya
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['fullname'] = user['fullname']  # <-- Tambahkan baris ini

            # Redirect sesuai role
            if role == 'admin':
                return redirect(url_for('dashboard_admin'))
            elif role == 'investor':
                return redirect(url_for('dashboard_investor'))
            elif role == 'investy':
                return redirect(url_for('dashboard_investy'))
            elif role == 'bank':
                return redirect(url_for('dashboard_bank'))
        else:
            flash('Email, password, atau role salah!', 'danger')
            return redirect(url_for('login', role=role))

    return render_template('login.html', role=role)




@app.route('/dashboard_investy', methods=['GET', 'POST'])
def dashboard_investy():
    conn = get_db_connection()

    if request.method == 'POST':
        business_name = request.form['business_name']
        investy_id = session['user_id']
        amount = request.form['amount']
        description = request.form['description']
        created_at = datetime.now().strftime('%Y-%m-%d')

        # Upload Cover
        cover = request.files.get('cover')
        if cover and cover.filename:
            cover_filename = secure_filename(cover.filename)
            cover_path = os.path.join(app.config['UPLOAD_FOLDER'], cover_filename)
            cover.save(cover_path)
        else:
            cover_filename = None

        # Upload document
        document = request.files.get('document')
        if document and document.filename:
            doc_filename = secure_filename(document.filename)
            doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
            document.save(doc_path)
        else:
            doc_filename = None

        conn.execute('''
            INSERT INTO crowdfunding_requests 
            (business_name, investy_id, amount, description, cover_image, document, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (business_name, investy_id, amount, description, cover_filename, doc_filename, created_at, 'pending'))
        conn.commit()
        conn.close()
        return redirect('/dashboard_investy')

    # GET method
    investy_id = session['user_id']
    requests = conn.execute('SELECT * FROM crowdfunding_requests WHERE investy_id = ?', (investy_id,)).fetchall()

    # Statistik
    total_requests = len(requests)
    approved_count = len([r for r in requests if r['status'] == 'approved'])
    rejected_count = len([r for r in requests if r['status'] == 'rejected'])

    # Grafik: hitung pengajuan per bulan
    bulan_counter = Counter()
    for r in requests:
        if r['created_at']:
            try:
                tanggal = datetime.strptime(r['created_at'], "%Y-%m-%d")
                bulan = tanggal.strftime("%b %Y")
                bulan_counter[bulan] += 1
            except Exception:
                pass

    sorted_bulan = sorted(bulan_counter.items(), key=lambda x: datetime.strptime(x[0], "%b %Y"))
    chart_labels = [b[0] for b in sorted_bulan]
    chart_data = [b[1] for b in sorted_bulan]

    conn.close()

    return render_template('dashboard_investy.html',
                           requests=requests,
                           total_requests=total_requests,
                           approved_count=approved_count,
                           rejected_count=rejected_count,
                           chart_labels=chart_labels,
                           chart_data=chart_data)
    
    
    
    
    
#INVESTY PENGAJUAN
@app.route('/buat_pengajuan', methods=['GET', 'POST'])
def buat_pengajuan():
    if 'user_id' not in session or session.get('role') != 'investy':
        flash('Silakan login terlebih dahulu sebagai investy.')
        return redirect(url_for('login', role='investy'))

    if request.method == 'POST':
        business_name = request.form['business_name']
        amount = request.form['amount']
        description = request.form['description']
        created_at = datetime.now().strftime('%Y-%m-%d')
        user_id = session['user_id']

        # Penanganan file
        cover_image_file = request.files.get('cover_image')
        document_file = request.files.get('document')  # Pastikan ini nama input yang benar

        cover_image_filename = None
        document_filename = None

        # Simpan cover image
        if cover_image_file and allowed_file(cover_image_file.filename):
            cover_image_filename = secure_filename(cover_image_file.filename)
            cover_image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_image_filename))

        # Simpan document pdf
        if document_file and allowed_file(document_file.filename):
            document_filename = secure_filename(document_file.filename)
            document_file.save(os.path.join(app.config['UPLOAD_FOLDER'], document_filename))

        # Simpan ke database
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO crowdfunding_requests 
            (investy_id, business_name, amount, description, cover_image, document, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, business_name, amount, description, cover_image_filename, document_filename, 'pending', created_at))
        conn.commit()
        conn.close()

        flash('Pengajuan berhasil dibuat.')
        return redirect(url_for('dashboard_investy'))

    return render_template('buat_pengajuan.html')


# DASHBOARD ADMIN
@app.route('/dashboard_admin')
def dashboard_admin():
    conn = get_db_connection()

    jumlah_produk = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    jumlah_pesanan = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    validasi_investasi = conn.execute("SELECT COUNT(*) FROM crowdfunding_requests WHERE status = 'pending'").fetchone()[0]
    total_investasi = conn.execute('SELECT SUM(amount) FROM investments').fetchone()[0]
    total_investasi = total_investasi if total_investasi else 0

    hasil = conn.execute("""
        SELECT strftime('%m', order_date) as bulan, SUM(total_price)
        FROM orders
        WHERE status = 'completed'
        GROUP BY bulan
    """).fetchall()

    earnings_per_month = [0] * 12
    for bulan, total in hasil:
        earnings_per_month[int(bulan) - 1] = total

    conn.close()

    return render_template('dashboard_admin.html',
                           jumlah_produk=jumlah_produk,
                           jumlah_pesanan=jumlah_pesanan,
                           validasi_investasi=validasi_investasi,
                           total_investasi=total_investasi,
                           earnings_per_month=earnings_per_month)


@app.route('/admin/dashboard-data')
def admin_dashboard_data():
    conn = sqlite3.connect('myappdb.db')
    c = conn.cursor()

    c.execute("""
        SELECT strftime('%m', created_at), SUM(amount)
        FROM investasi
        GROUP BY strftime('%m', created_at)
    """)
    results = c.fetchall()
    conn.close()

    data = [0]*12
    for bulan, total in results:
        data[int(bulan)-1] = total  # index mulai dari 0

    return jsonify(data)



@app.route('/validasi_pengguna')
def validasi_pengguna():
    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()
    
    # Ambil semua user dengan status NULL dan bukan admin/bank
    cursor.execute("SELECT id, fullname, email, role FROM users WHERE role NOT IN ('admin', 'bank') AND status IS NULL")
    users = cursor.fetchall()
    conn.close()

    return render_template('validasi_pengguna.html', users=users)

@app.route('/update_user/<int:user_id>/<action>', methods=['POST'])
def update_user(user_id, action):
    conn = sqlite3.connect("myappdb.db")
    cursor = conn.cursor()

    try:
        if action == "validasi":
            cursor.execute("UPDATE users SET status='approved' WHERE id=?", (user_id,))
        elif action == "tolak":
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        else:
            return jsonify({"success": False, "error": "Aksi tidak dikenali"})

        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"success": False, "error": str(e)})
@app.route('/kelola_produk')
def kelola_produk():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()

    role = session['role']
    user_id = session['user_id']

    if role == 'admin':
        cursor.execute('SELECT * FROM products')
    else:
        cursor.execute('SELECT * FROM products WHERE owner_id = ? AND owner_role = ?', (user_id, role))

    products = cursor.fetchall()
    conn.close()
    return render_template('kelola_produk.html', products=[
    dict(id=row[0], name=row[1], price=row[2], image=row[3], stok=row[4]) for row in products
    ])



@app.route('/tambah-produk', methods=['GET', 'POST'])
def tambah_produk():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        image = request.form['image']
        stok = request.form['stok']
        owner_id = session['user_id']
        owner_role = session['role']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO products (name, price, image, stok, owner_id, owner_role) VALUES (?, ?, ?, ?, ?, ?)",
          (name, price, image, stok, owner_id, owner_role))
        conn.commit()
        conn.close()

        return redirect(url_for('kelola_produk'))

    return render_template('tambah_produk.html')


@app.route('/edit-produk/<int:id>', methods=['GET', 'POST'])
def edit_produk(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ambil produk dan pastikan hanya bisa diakses oleh pemilik
    cursor.execute("SELECT * FROM products WHERE id = ?", (id,))
    product = cursor.fetchone()

    if not product:
        flash("Produk tidak ditemukan!", "error")
        return redirect(url_for('kelola_produk'))

    # Cek hak akses
    if session['role'] != 'admin' and (product['owner_id'] != session['user_id'] or product['owner_role'] != session['role']):
        flash("Akses ditolak!", "danger")
        return redirect(url_for('kelola_produk'))

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        image = request.form['image']
        stok = request.form['stok']

        cursor.execute("UPDATE products SET name = ?, price = ?, image = ?, stok = ? WHERE id = ?",
               (name, price, image, stok, id))
        
        conn.commit()
        conn.close()

        flash("Produk berhasil diperbarui!", "success")
        return redirect(url_for('kelola_produk'))

    conn.close()
    return render_template('edit_produk.html', product=product)


@app.route('/hapus_produk/<int:id>')
def hapus_produk(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ambil produk
    cursor.execute("SELECT * FROM products WHERE id = ?", (id,))
    product = cursor.fetchone()

    if not product:
        flash("Produk tidak ditemukan!", "error")
        return redirect(url_for('kelola_produk'))

    if session['role'] != 'admin' and (product['owner_id'] != session['user_id'] or product['owner_role'] != session['role']):
        flash("Akses ditolak!", "danger")
        return redirect(url_for('kelola_produk'))

    cursor.execute("DELETE FROM products WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('kelola_produk'))

@app.route('/admin/update_status', methods=['POST'])
def update_status_admin():
    order_id = request.form['order_id']
    new_status = request.form['status']

    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

    flash('Status pesanan berhasil diperbarui!', 'success')
    return redirect(url_for('kelola_pesanan'))  # Khusus Admin



@app.route('/kelola_pesanan')
def kelola_pesanan():
    conn = sqlite3.connect('myappdb.db')
    c = conn.cursor()
    c.execute('''
        SELECT orders.id, users.fullname, products.name, orders.quantity, orders.status, orders.order_date
        FROM orders
        JOIN users ON orders.user_id = users.id
        JOIN products ON orders.product_id = products.id
    ''')
    orders = c.fetchall()
    conn.close()
    return render_template('kelola_pesanan.html', orders=orders)

@app.route('/investy/update_status', methods=['POST'])
def update_status_investy():
    order_id = request.form['order_id']
    new_status = request.form['status']

    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

    flash('Status pesanan berhasil diperbarui!', 'success')
    return redirect(url_for('pesanan_masuk'))  # Khusus Investy


@app.route('/admin/validasi-investasi')
def validasi_investasi():
    """Menampilkan daftar pengajuan pembiayaan Investy di dashboard admin."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ambil semua pengajuan pembiayaan yang masih pending
    cursor.execute(''' 
            SELECT crowdfunding_requests.id, users.fullname, crowdfunding_requests.amount, 
                crowdfunding_requests.description, crowdfunding_requests.status, 
                crowdfunding_requests.document, crowdfunding_requests.created_at,
                crowdfunding_requests.business_name
            FROM crowdfunding_requests
            JOIN users ON crowdfunding_requests.investy_id = users.id
            WHERE crowdfunding_requests.status = 'pending'
            ORDER BY crowdfunding_requests.created_at DESC
        ''')

    crowdfunding_requests = cursor.fetchall()
    
    # Mengonversi sqlite3.Row ke dictionary dan konversi created_at menjadi datetime
    crowdfunding_requests_list = []
    for request in crowdfunding_requests:
        request_dict = dict(request)  # Mengonversi sqlite3.Row menjadi dictionary
        created_at = request_dict['created_at']
        
        if len(created_at) > 10:  # Jika ada waktu (lebih dari 10 karakter)
            request_dict['created_at'] = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        else:
            request_dict['created_at'] = datetime.strptime(created_at, '%Y-%m-%d')
        
        crowdfunding_requests_list.append(request_dict)
    
    conn.close()
    
    return render_template('admin_validasi_investasi.html', crowdfunding_requests=crowdfunding_requests_list)

@app.route('/admin/validasi-investasi/approve/<int:request_id>', methods=['GET'])
def approve_funding(request_id):
    """Menyetujui pengajuan pembiayaan."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE crowdfunding_requests SET status = 'approved' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

    flash('Pengajuan pembiayaan berhasil disetujui.', 'success')
    return redirect(url_for('validasi_investasi'))

@app.route('/admin/validasi-investasi/reject/<int:request_id>', methods=['GET'])
def reject_funding(request_id):
    """Menolak pengajuan pembiayaan."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE crowdfunding_requests SET status = 'rejected' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

    flash('Pengajuan pembiayaan telah ditolak.', 'danger')
    return redirect(url_for('validasi_investasi'))


@app.route("/admin/laporan-investasi")
def laporan_investasi_admin():
    bulan = request.args.get('bulan')  # e.g., "Januari"
    tahun = request.args.get('tahun')
    status = request.args.get('status')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM investments WHERE 1=1"
    params = []

    bulan_mapping = {
        "Januari": "01",
        "Februari": "02",
        "Maret": "03",
        "April": "04",
        "Mei": "05",
        "Juni": "06",
        "Juli": "07",
        "Agustus": "08",
        "September": "09",
        "Oktober": "10",
        "November": "11",
        "Desember": "12"
    }

    if bulan and bulan.lower() != "semua":
        bulan_angka = bulan_mapping.get(bulan)
        if bulan_angka:
            query += " AND strftime('%m', created_at) = ?"
            params.append(bulan_angka)

    if tahun and tahun.strip():
        query += " AND strftime('%Y', created_at) = ?"
        params.append(tahun)

    if status and status.lower() != "semua":
        query += " AND LOWER(status) = ?"
        params.append(status.lower())

    cursor.execute(query, params)
    rows = cursor.fetchall()

    formatted_data = []
    for row in rows:
        row = dict(row)
        try:
            date_obj = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
            row['formatted_date'] = date_obj.strftime('%d-%m-%Y')
        except:
            row['formatted_date'] = row['created_at']
        row['status'] = 'Selesai'
        formatted_data.append(row)

    conn.close()
    return render_template("admin_laporan_investasi.html", investment_reports=formatted_data, bulan_dipilih=bulan, tahun_dipilih=tahun, status_dipilih=status)


@app.route('/admin/investasi/<int:investasi_id>')
def detail_investasi(investasi_id):
    conn = get_db_connection()
    investasi = conn.execute('SELECT * FROM investments WHERE id = ?', (investasi_id,)).fetchone()
    conn.close()
    return render_template('detail_investasi.html', data=investasi)


@app.route("/admin/investment/<int:investment_id>")
def detail_investment(investment_id):
    # Sementara dummy
    return f"Detail investasi {investment_id}"

@app.route("/admin/investment/<int:investment_id>/export")
def export_pdf(investment_id):
    # Sementara dummy
    return f"Export PDF investasi {investment_id}"


@app.route('/upload_dokumen/<int:id>', methods=['POST'])
def upload_dokumen(id):
    if 'user_id' not in session or session.get('role') != 'investy':
        flash('Silakan login terlebih dahulu.')
        return redirect(url_for('login'))

    file = request.files.get('document')
    if not file:
        flash('Tidak ada file yang diunggah.')
        return redirect(url_for('dashboard_investy'))

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    conn = get_db_connection()
    conn.execute("UPDATE crowdfunding_requests SET document = ? WHERE id = ?", (filename, id))
    conn.commit()
    conn.close()

    flash('Dokumen berhasil diupload.')
    return redirect(url_for('dashboard_investy'))


@app.route('/admin/investasi')
def semua_investasi():
    conn = get_db_connection()
    investasi = conn.execute("""
        SELECT id, business_name, description, amount, status, created_at
        FROM crowdfunding_requests
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin/semua_investasi.html', investasi=investasi)

# Menghapus / Takedown investasi
@app.route('/admin/investasi/delete/<int:id>', methods=['POST'])
def hapus_investasi(id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM crowdfunding_requests WHERE id = ?', (id,))
        conn.commit()
        flash('Investasi berhasil dihapus.', 'success')
    except:
        flash('Gagal menghapus investasi.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('semua_investasi'))

#PIHAK BANK










@app.route('/validasi_transaksi')
def validasi_transaksi():
    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nama_investor, jumlah, status FROM transaksi WHERE status = 'menunggu_validasi'")
    transaksi = cursor.fetchall()
    conn.close()
    return render_template('validasi_transaksi.html', transaksi=transaksi)

@app.route('/validasi_transaksi/setujui/<int:id>')
def setujui_transaksi(id):
    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE transaksi SET status = 'disetujui' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/validasi_transaksi')

@app.route('/validasi_transaksi/tolak/<int:id>')
def tolak_transaksi(id):
    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE transaksi SET status = 'ditolak' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/validasi_transaksi')

    
    
@app.route('/edit-pengguna', methods=['GET', 'POST'])
def edit_pengguna():
    conn = get_db_connection()
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        role = request.form['role']
        
        if user_id:  # Jika ada ID, berarti edit
            if password:
                conn.execute('''UPDATE users SET fullname=?, email=?, password=?, phone=?, role=? WHERE id=?''',
                             (fullname, email, password, phone, role, user_id))
            else:
                conn.execute('''UPDATE users SET fullname=?, email=?, phone=?, role=? WHERE id=?''',
                             (fullname, email, phone, role, user_id))
        else:  # Jika tidak ada ID, berarti tambah
            conn.execute('''INSERT INTO users (fullname, email, password, phone, role) VALUES (?, ?, ?, ?, ?)''',
                         (fullname, email, password, phone, role))
        conn.commit()
    
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('edit-pengguna.html', users=users)

@app.route('/hapus-pengguna/<int:user_id>', methods=['POST'])
def hapus_pengguna(user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_pengguna'))


@app.route('/validasi_pembiayaan')
def validasi_pembiayaan():
    conn = sqlite3.connect('myappdb.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM crowdfunding_requests 
        WHERE status IN ('approved', 'terpenuhi')
    """)
    data = cursor.fetchall()
    conn.close()
    return render_template('validasi_pembiayaan.html', data=data)



@app.route('/dashboard_bank')
def dashboard_bank():
    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()

    # Hitung jumlah validasi pembiayaan (status 'approved')
    cursor.execute("SELECT COUNT(*) FROM crowdfunding_requests WHERE status = 'approved'")
    jumlah_validasi = cursor.fetchone()[0] or 0

    # Hitung jumlah pencairan dana (status 'terpenuhi' dan saldo > 0)
    cursor.execute("SELECT COUNT(*) FROM crowdfunding_requests WHERE status = 'terpenuhi' AND saldo > 0")
    jumlah_pencairan = cursor.fetchone()[0] or 0

    conn.close()

    return render_template('dashboard_bank.html',
                           jumlah_validasi=jumlah_validasi,
                           jumlah_pencairan=jumlah_pencairan)





@app.route('/dashboard_bank/pencairan_dana')
@role_required('bank')
def daftar_pencairan_dana():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, business_name, amount, funded_amount, saldo, created_at 
        FROM crowdfunding_requests
        WHERE status = 'terpenuhi' AND (saldo IS NULL OR saldo = 0)
    ''')
    proyek = cursor.fetchall()
    conn.close()
    return render_template('bank_pencairan_dana.html', proyek=proyek)

@app.route('/dashboard_bank/cairkan/<int:id>', methods=['POST'])
@role_required('bank')
def cairkan_dana(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ambil funded_amount
    cursor.execute('SELECT funded_amount FROM crowdfunding_requests WHERE id = ?', (id,))
    result = cursor.fetchone()

    if result:
        funded_amount = result['funded_amount']
        cursor.execute('UPDATE crowdfunding_requests SET saldo = ? WHERE id = ?', (funded_amount, id))
        conn.commit()
        flash('Dana berhasil dicairkan ke saldo Investy.', 'success')
    else:
        flash('Data tidak ditemukan.', 'danger')

    conn.close()
    return redirect(url_for('daftar_pencairan_dana'))









#CROWFUNDING
@app.route('/pembiayaan')
def pembiayaan():
    conn = get_db_connection()
    hasil = conn.execute("SELECT * FROM crowdfunding_requests WHERE status = 'approved'").fetchall()
    conn.close()
    return render_template('pembiayaan.html', hasil=hasil)

@app.route('/pembiayaan/<int:id>')
def detail_pembiayaan(id):
    conn = get_db_connection()
    data = conn.execute("SELECT * FROM crowdfunding_requests WHERE id = ?", (id,)).fetchone()
    conn.close()

    if data is None:
        return "Pengajuan tidak ditemukan", 404

    return render_template('detail_pembiayaan.html', data=data, request_id=id)


@app.route('/investasi/<int:pembiayaan_id>', methods=['GET', 'POST'])
def investasi(pembiayaan_id):
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ambil data pembiayaan
    pembiayaan = cursor.execute("SELECT * FROM crowdfunding_requests WHERE id = ?", (pembiayaan_id,)).fetchone()

    if not pembiayaan:
        flash("Data pembiayaan tidak ditemukan.", "danger")
        return redirect(url_for('pembiayaan'))

    if request.method == 'POST':
        amount = request.form['jumlah']
        investor_id = session['user_id']

        # Ambil nama investor dari tabel users
        investor = cursor.execute("SELECT fullname FROM users WHERE id = ?", (investor_id,)).fetchone()
        investor_name = investor['fullname'] if investor else 'Investor Tanpa Nama'

        cursor.execute("""
            INSERT INTO investments (
                investy_id, amount, description, document, created_at, status,
                investy_name, investor_name, investment_date
            ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?, date('now'))
        """, (
            pembiayaan['investy_id'],      # investy_id
            amount,
            pembiayaan['description'],
            pembiayaan['document'],
            'Menunggu Konfirmasi',
            pembiayaan['investy_name'], # pastikan kolom ini ada di crowdfunding_requests
            investor_name
        ))

        conn.commit()
        conn.close()
        flash("Investasi berhasil diajukan!", "success")
        return redirect(url_for('pembiayaan'))

    conn.close()
    return render_template('form_investasi.html', pembiayaan=pembiayaan)





from collections import defaultdict
from datetime import datetime

@app.route('/dashboard_investor')
def dashboard_investor():
    if 'user_id' not in session or session.get('role') != 'investor':
        flash('Silakan login terlebih dahulu sebagai investor.')
        return redirect(url_for('login', role='investor'))

    investor_id = session['user_id']

    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()

    # 1. Hitung total proyek yang pernah diinvestasikan investor ini
    cursor.execute("""
        SELECT COUNT(DISTINCT crowdfunding_id)
        FROM investments
        WHERE investor_id = ?
    """, (investor_id,))
    total_crowdfunding = cursor.fetchone()[0]

    # 2. Hitung total investasi (anggap ini "keuntungan")
    cursor.execute("""
        SELECT SUM(amount)
        FROM investments
        WHERE investor_id = ?
    """, (investor_id,))
    total_keuntungan = cursor.fetchone()[0] or 0

    # 3. Ambil data investasi per bulan
    cursor.execute("""
        SELECT strftime('%m-%Y', created_at) as bulan, SUM(amount)
        FROM investments
        WHERE investor_id = ?
        GROUP BY bulan
        ORDER BY created_at ASC
    """, (investor_id,))
    results = cursor.fetchall()
    conn.close()

    chart_labels = [row[0] for row in results]
    chart_data = [row[1] for row in results]

    return render_template('dashboard_investor.html',
                           total_crowdfunding=total_crowdfunding,
                           total_keuntungan=total_keuntungan,
                           chart_labels=chart_labels,
                           chart_data=chart_data)


@app.route('/investasi_saya')
def investasi_saya():
    if 'user_id' not in session or session.get('role') != 'investor':
        flash("Silakan login terlebih dahulu sebagai investor.")
        return redirect(url_for('login', role='investor'))

    conn = get_db_connection()
    c = conn.cursor()

    # Ambil daftar investasi user
    c.execute('''
        SELECT i.id, i.crowdfunding_id, i.amount, i.created_at, c.business_name
        FROM investments i
        JOIN crowdfunding_requests c ON i.crowdfunding_id = c.id
        WHERE i.investor_id = ?
        ORDER BY i.created_at DESC
    ''', (session['user_id'],))
    daftar_investasi = c.fetchall()

    # Ambil semua usage yang berkaitan
    crowdfunding_ids = [str(invest['crowdfunding_id']) for invest in daftar_investasi]
    usage_dict = {}

    if crowdfunding_ids:
        placeholder = ','.join('?' * len(crowdfunding_ids))
        usage_rows = c.execute(f'''
            SELECT * FROM investment_usages
            WHERE crowdfunding_id IN ({placeholder})
        ''', crowdfunding_ids).fetchall()

        for row in usage_rows:
            cid = row['crowdfunding_id']
            if cid not in usage_dict:
                usage_dict[cid] = []
            usage_dict[cid].append(row)

    conn.close()

    return render_template("investor_investasi_saya.html",
                           daftar_investasi=daftar_investasi,
                           penggunaan_dana=usage_dict)



@app.route('/investasi/<int:investment_id>/penggunaan')
def lihat_penggunaan_dana(investment_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Dapatkan crowdfunding_id dari investment_id
    result = cursor.execute('''
        SELECT crowdfunding_id FROM investments
        WHERE id = ?
    ''', (investment_id,)).fetchone()

    if not result:
        flash("Data tidak ditemukan.", "danger")
        return redirect(url_for('dashboard_investor'))

    crowdfunding_id = result['crowdfunding_id']

    # Ambil penggunaan dana berdasarkan crowdfunding_id
    usage = cursor.execute('''
        SELECT * FROM investment_usages
        WHERE crowdfunding_id = ?
        ORDER BY used_at DESC
    ''', (crowdfunding_id,)).fetchall()

    # Ambil nama usaha (opsional)
    project = cursor.execute('''
        SELECT business_name FROM crowdfunding_requests
        WHERE id = ?
    ''', (crowdfunding_id,)).fetchone()

    conn.close()

    return render_template('penggunaan_dana.html', usage=usage, project=project)


@app.route("/investor/laporan-investasi")
def laporan_investasi_investor():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    investor_id = session['user_id']
    bulan = request.args.get('bulan')
    tahun = request.args.get('tahun')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM investments WHERE investor_id = ?"
    params = [investor_id]

    bulan_mapping = {
        "Januari": "01",
        "Februari": "02",
        "Maret": "03",
        "April": "04",
        "Mei": "05",
        "Juni": "06",
        "Juli": "07",
        "Agustus": "08",
        "September": "09",
        "Oktober": "10",
        "November": "11",
        "Desember": "12"
    }

    if bulan and bulan.lower() != "semua":
        bulan_angka = bulan_mapping.get(bulan)
        if bulan_angka:
            query += " AND strftime('%m', created_at) = ?"
            params.append(bulan_angka)

    if tahun and tahun.strip():
        query += " AND strftime('%Y', created_at) = ?"
        params.append(tahun)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    formatted_data = []
    for row in rows:
        row = dict(row)
        try:
            date_obj = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
            row['formatted_date'] = date_obj.strftime('%d-%m-%Y')
        except:
            row['formatted_date'] = row['created_at']
        row['status'] = "Approved"  # Atau ambil dari tabel lain jika ada
        formatted_data.append(row)

    return render_template("investor_laporan_investasi.html", investment_reports=formatted_data,
                           bulan_dipilih=bulan, tahun_dipilih=tahun)



@app.route('/pesanan_investor')
def pesanan_investor():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
        SELECT o.order_date, p.name AS product_name, o.quantity, o.total_price, o.status
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.user_id = ?
        ORDER BY o.order_date DESC
    """, (user_id,))
    orders = c.fetchall()
    conn.close()

    return render_template('investor_orders.html', orders=orders)




@app.route('/riwayat_transaksi')
def riwayat_transaksi():
    if 'user_id' not in session or session.get('role') != 'investor':
        return redirect('/login')  # atau halaman lain

    investor_id = session['user_id']  # Ambil ID investor dari session

    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.created_at, c.business_name, i.amount
        FROM investments i
        JOIN crowdfunding_requests c ON i.crowdfunding_id = c.id
        WHERE i.investor_id = ?
        ORDER BY i.created_at DESC
    """, (investor_id,))

    rows = cursor.fetchall()
    conn.close()

    riwayat = []
    for row in rows:
        riwayat.append({
            "tanggal": row[0],
            "proyek": row[1],
            "jumlah": row[2],
            "tipe": "investasi",
            "status": "berhasil"
        })

    return render_template("investor_riwayat_transaksi.html", riwayat=riwayat)


@app.template_filter('format_price')
def format_price(value):
    return "{:,.0f}".format(value).replace(",", ".")

@app.route('/kalkulator_investasi', methods=['GET', 'POST'])
def kalkulator_investasi():
    hasil = None
    total_keuntungan = 0

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Ambil total return dari database (jika tabel investment_returns dibuat)
    conn = sqlite3.connect('myappdb.db')
    c = conn.cursor()

    # Cek apakah tabel investment_returns ada
    try:
        c.execute("SELECT SUM(return_amount) FROM investment_returns WHERE investor_id = ?", (user_id,))
        total_keuntungan = c.fetchone()[0] or 0
    except:
        total_keuntungan = 0  # Jika tabel belum ada

    # Hitung simulasi
    if request.method == 'POST':
        modal = float(request.form['modal'])
        durasi = int(request.form['durasi'])
        margin = float(request.form['margin'])

        # Total margin per bulan
        total_margin_per_bulan = modal * (margin / 100)

        # Bagi hasil
        return_investor = total_margin_per_bulan * 0.6
        return_investor_total = return_investor * durasi
        total_kembali = modal + return_investor_total

        hasil = {
            'modal': modal,
            'durasi': durasi,
            'margin': margin,
            'return_investor_per_bulan': return_investor,
            'total_return': return_investor_total,
            'total_kembali': total_kembali
        }

    conn.close()
    return render_template('investor_kalkulator_investasi.html', hasil=hasil, total_keuntungan=total_keuntungan)


@app.route('/invest', methods=['POST'])
def invest():
    crowdfunding_id = request.form['crowdfunding_id']
    investor_id = request.form['investor_id']
    amount = float(request.form['amount'])
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Simpan investasi
    cursor.execute('''
        INSERT INTO investments (crowdfunding_id, investor_id, amount, created_at)
        VALUES (?, ?, ?, ?)
    ''', (crowdfunding_id, investor_id, amount, created_at))

    # Update funded_amount
    cursor.execute('''
        UPDATE crowdfunding_requests
        SET funded_amount = funded_amount + ?
        WHERE id = ?
    ''', (amount, crowdfunding_id))

    # Cek apakah sudah terpenuhi
    cursor.execute('''
        SELECT amount, funded_amount FROM crowdfunding_requests
        WHERE id = ?
    ''', (crowdfunding_id,))
    row = cursor.fetchone()
    if row and row['funded_amount'] >= row['amount']:
        cursor.execute('''
            UPDATE crowdfunding_requests
            SET status = 'terpenuhi'
            WHERE id = ?
        ''', (crowdfunding_id,))

    conn.commit()
    conn.close()
    flash('Investasi berhasil!')
    return redirect('/dashboard_investor')  # sesuaikan dengan halaman kamu



@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    admin_id = session.get('admin_id')  # atau dari session login
    conn = sqlite3.connect('myappdb.db')
    c = conn.cursor()

    if request.method == 'POST':
        theme = request.form['theme']
        notifications = request.form['notifications']

        # Cek apakah sudah ada data setting
        c.execute("SELECT * FROM admin_settings WHERE admin_id = ?", (admin_id,))
        existing = c.fetchone()

        if existing:
            c.execute("""UPDATE admin_settings SET theme = ?, notifications = ?
                         WHERE admin_id = ?""", (theme, notifications, admin_id))
        else:
            c.execute("""INSERT INTO admin_settings (admin_id, theme, notifications)
                         VALUES (?, ?, ?)""", (admin_id, theme, notifications))

        conn.commit()
        flash('Pengaturan berhasil disimpan.')

    c.execute("SELECT theme, notifications FROM admin_settings WHERE admin_id = ?", (admin_id,))
    setting = c.fetchone()
    conn.close()

    return render_template('admin_settings.html', setting=setting)


@app.route('/marketplace')
def marketplace():
    role = session.get('role')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, price, image, stok FROM products")
    products = c.fetchall()
    conn.close()

    # Konversi hasil query ke list of dict
    products_list = [{'id': p[0], 'name': p[1], 'price': float(p[2]), 'image': p[3], 'stock': p[4] } for p in products]

    # Render halaman sesuai role
    if role == 'investor':
        return render_template('marketplace_investor.html', products=products_list)
    elif role == 'investy':
        return render_template('marketplace_investy.html', products=products_list)
    elif role == 'admin':
        return render_template('marketplace_admin.html', products=products_list)
    elif role == 'bank':
        return render_template('marketplace_bank.html', products=products_list)
    else:
        return redirect(url_for('login'))


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    quantity = request.form.get('quantity', 1, type=int)

    conn = get_db_connection()
    c = conn.cursor()

    # Cek jika sudah ada item ini di keranjang user
    c.execute("SELECT id, quantity FROM cart_items WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    existing_item = c.fetchone()

    if existing_item:
        # Update jumlah jika sudah ada
        new_quantity = existing_item['quantity'] + quantity
        c.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_quantity, existing_item['id']))
    else:
        # Tambahkan baru jika belum ada
        c.execute("INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, quantity))

    conn.commit()
    conn.close()

    return jsonify(success=True)

@app.route('/cart')
def view_cart():
    user_id = session.get('user_id')
    user_role = session.get('role')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
        SELECT ci.id AS cart_item_id, p.id AS product_id, p.name, p.price, ci.quantity
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.user_id = ?
    """, (user_id,))
    rows = c.fetchall()
    conn.close()

    cart_items = []
    total_price = 0
    for row in rows:
        price = float(row['price'])
        quantity = int(row['quantity'])
        total = price * quantity
        total_price += total
        cart_items.append({
            'cart_item_id': row['cart_item_id'],
            'product': {
                'id': row['product_id'],
                'name': row['name'],
                'price': price
            },
            'quantity': quantity,
            'total_price': total
        })

    return render_template('cart.html', cart_items=cart_items, total_price=total_price, role=user_role)


@app.route('/cart/count')
def cart_count():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'count': 0})

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT SUM(quantity) AS total_items FROM cart_items WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()

    total_items = result['total_items'] if result['total_items'] else 0
    return jsonify({'count': total_items})


@app.route('/update_cart/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    action = request.form['action']
    conn = sqlite3.connect('myappdb.db')
    c = conn.cursor()

    # Ambil quantity sekarang
    c.execute("SELECT quantity FROM cart_items WHERE id = ?", (item_id,))
    result = c.fetchone()
    if result:
        current_qty = result[0]
        if action == 'increase':
            new_qty = current_qty + 1
        elif action == 'decrease':
            new_qty = max(1, current_qty - 1)  # Tidak bisa kurang dari 1

        c.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_qty, item_id))
        conn.commit()

    conn.close()
    return redirect(url_for('view_cart'))


@app.route('/delete_cart_item/<int:item_id>', methods=['POST'])
def delete_cart_item(item_id):
    conn = sqlite3.connect('myappdb.db')
    c = conn.cursor()
    c.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_cart'))





@app.route('/checkout', methods=['POST'])
def checkout():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    nama = request.form.get('nama')
    alamat = request.form.get('alamat')

    conn = get_db_connection()
    c = conn.cursor()

    # Ambil item dari cart_items sebelum dihapus
    c.execute("""
        SELECT product_id, quantity 
        FROM cart_items 
        WHERE user_id = ?
    """, (user_id,))
    cart_items = c.fetchall()

    # Simpan ke tabel orders
    for item in cart_items:
        product_id = item['product_id']
        quantity = item['quantity']

        # Ambil harga produk
        c.execute("SELECT price FROM products WHERE id = ?", (product_id,))
        product = c.fetchone()

        if product:
            price = float(product['price'])  # tambahkan konversi ke float
            total_price = price * quantity

            c.execute("""
                INSERT INTO orders (user_id, product_id, quantity, total_price, status, order_date)
                VALUES (?, ?, ?, ?, 'diproses', CURRENT_TIMESTAMP)
            """, (user_id, product_id, quantity, total_price))


    # Hapus item keranjang
    c.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return render_template('checkout_success.html', nama=nama)



@app.route('/checkout-form', methods=['GET', 'POST'])
def checkout_form():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_role = session['role']

    conn = sqlite3.connect('myappdb.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == 'POST':
        if user_role == 'investor':
            full_name = request.form.get('full_name')
            phone_number = request.form.get('phone_number')
            shipping_address = request.form.get('shipping_address')
            metode = 'pribadi'
            crowdfunding_id = None
        else:
            full_name = request.form.get('nama')
            phone_number = '-'
            shipping_address = request.form.get('alamat')
            metode = request.form.get('metode_pembayaran')
            crowdfunding_id = request.form.get('crowdfunding_id')

        if not full_name or not shipping_address:
            flash("Silakan lengkapi semua data.", "warning")
            return redirect(url_for('checkout_form'))

        # Ambil isi keranjang beserta stok produk
        c.execute('''
            SELECT ci.product_id, ci.quantity, p.price, p.stok
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            WHERE ci.user_id = ?
        ''', (user_id,))
        cart_items = c.fetchall()

        if not cart_items:
            flash("Keranjang kosong.", "warning")
            return redirect(url_for('view_cart'))

        # Cek apakah semua produk memiliki stok yang cukup
        for item in cart_items:
            if int(item['stok']) < int(item['quantity']):
                flash(f"Stok tidak cukup untuk produk ID {item['product_id']}.", "danger")
                return redirect(url_for('view_cart'))

        total_checkout = sum(int(row['quantity']) * int(row['price']) for row in cart_items)

        # Jika menggunakan dana investasi
        if user_role == 'investy' and metode == 'investasi':
            if not crowdfunding_id:
                flash("Pilih proyek yang ingin digunakan untuk dana investasi.", "warning")
                return redirect(url_for('checkout_form'))

            crowdfunding_id = int(crowdfunding_id)
            c.execute('''
                SELECT saldo FROM crowdfunding_requests
                WHERE id = ? AND investy_id = ? AND status IN ('approved', 'terpenuhi')
            ''', (crowdfunding_id, user_id))
            row = c.fetchone()

            if not row:
                flash("Proyek tidak ditemukan atau bukan milik Anda.", "danger")
                return redirect(url_for('checkout_form'))

            saldo = int(row['saldo'])

            if saldo < total_checkout:
                flash("Saldo proyek tidak mencukupi untuk checkout ini.", "danger")
                return redirect(url_for('checkout_form'))

            # Kurangi saldo proyek
            new_saldo = saldo - total_checkout
            c.execute("UPDATE crowdfunding_requests SET saldo = ? WHERE id = ?", (new_saldo, crowdfunding_id))
            status_order = 'Dibayar dari Dana Investasi'
        else:
            status_order = 'Menunggu Pembayaran'

        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for item in cart_items:
            product_id = int(item['product_id'])
            quantity = int(item['quantity'])
            price = int(item['price'])
            total_price = quantity * price
            stok_sekarang = int(item['stok'])

            # Simpan ke tabel orders
            c.execute('''
                INSERT INTO orders 
                (user_id, product_id, quantity, status, order_date, total_price, full_name, shipping_address, phone_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, product_id, quantity, status_order, order_date,
                total_price, full_name, shipping_address, phone_number
            ))

            # Catat penggunaan dana investasi
            if user_role == 'investy' and metode == 'investasi':
                c.execute('''
                    INSERT INTO investment_usages (crowdfunding_id, description, amount, used_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    crowdfunding_id,
                    f'Pembelian produk ID {product_id}',
                    total_price,
                    order_date
                ))

            # Kurangi stok produk
            sisa_stok = stok_sekarang - quantity
            c.execute("UPDATE products SET stok = ? WHERE id = ?", (sisa_stok, product_id))

        # Hapus keranjang
        c.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        flash("✅ Checkout berhasil!", "success")
        return redirect(url_for(f'pesanan_{user_role}'))

    # GET: ambil proyek aktif investy
    proyek_aktif = []
    if user_role == 'investy':
        c.execute('''
            SELECT id, business_name, saldo
            FROM crowdfunding_requests
            WHERE investy_id = ? AND status IN ('approved', 'terpenuhi') AND saldo > 0
        ''', (user_id,))
        proyek_aktif = c.fetchall()

    conn.close()
    return render_template('checkout.html', role=user_role, proyek_aktif=proyek_aktif)


@app.route('/order_now/<int:product_id>')
def order_now(product_id):
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "danger")
        return redirect(url_for('login'))

    qty = int(request.args.get('qty', 1))
    user_id = session['user_id']

    conn = sqlite3.connect('myappdb.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Ambil data stok produk
    c.execute("SELECT stok FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()

    if not product:
        flash("Produk tidak ditemukan.", "danger")
        conn.close()
        return redirect(url_for('marketplace'))

    stok_tersedia = int(product['stok'])

    if qty > stok_tersedia:
        flash(f"Stok hanya tersedia {stok_tersedia} unit.", "warning")
        conn.close()
        return redirect(url_for('marketplace'))

    # Cek apakah produk sudah ada di cart
    c.execute("SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    existing = c.fetchone()

    if existing:
        total_qty = existing['quantity'] + qty
        if total_qty > stok_tersedia:
            total_qty = stok_tersedia  # batasi sesuai stok
        c.execute("UPDATE cart_items SET quantity = ? WHERE user_id = ? AND product_id = ?", (total_qty, user_id, product_id))
    else:
        c.execute("INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, qty))

    conn.commit()
    conn.close()

    flash("Produk ditambahkan ke keranjang. Lanjutkan checkout.", "success")
    return redirect(url_for('checkout_form'))


@app.template_filter('format_price')
def format_price(value):
    return "{:,.0f}".format(value)



#Dashboard Investy
@app.route('/profil-investy', methods=['GET', 'POST'])
def profil_investy():
    user_id = session.get('user_id')
    if not user_id:
        flash("Session pengguna tidak ditemukan. Silakan login ulang.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        profil = cursor.execute('SELECT * FROM investy_profiles WHERE user_id = ?', (user_id,)).fetchone()

        if request.method == 'POST':
            nama_lengkap = request.form.get('nama_lengkap')
            nomor_ktp = request.form.get('nomor_ktp')
            alamat = request.form.get('alamat')
            nomor_hp = request.form.get('nomor_hp')
            nama_bank = request.form.get('nama_bank')
            nomor_rekening = request.form.get('nomor_rekening')

            if not all([nama_lengkap, nomor_ktp, alamat, nomor_hp, nama_bank, nomor_rekening]):
                flash("Semua field wajib diisi.", "danger")
                return redirect(url_for('profil_investy'))

            if profil:
                cursor.execute('''
                    UPDATE investy_profiles
                    SET nama_lengkap = ?, nomor_ktp = ?, alamat = ?, nomor_hp = ?, nama_bank = ?, nomor_rekening = ?
                    WHERE user_id = ?
                ''', (nama_lengkap, nomor_ktp, alamat, nomor_hp, nama_bank, nomor_rekening, user_id))
            else:
                cursor.execute('''
                    INSERT INTO investy_profiles (
                        user_id, nama_lengkap, nomor_ktp, alamat, nomor_hp, nama_bank, nomor_rekening, status_rekening, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (user_id, nama_lengkap, nomor_ktp, alamat, nomor_hp, nama_bank, nomor_rekening, 'simulasi'))

            conn.commit()
            flash("Profil investy berhasil disimpan.", "success")
            return redirect(url_for('profil_investy'))

        return render_template('profil_investy.html', profil=profil)

    finally:
        conn.close()

# Tampilkan halaman pengajuan
@app.route('/pengajuan_pendanaan')
def pengajuan_pendanaan():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Cek apakah user sudah memiliki profil Investy
    profil = cursor.execute('SELECT * FROM investy_profiles WHERE user_id = ?', (user_id,)).fetchone()

    if not profil:
        conn.close()
        flash('Silakan lengkapi profil dan rekening Investy terlebih dahulu.', 'warning')
        return redirect(url_for('profil_investy'))  # Route ke halaman form profil

    # Ambil data pengajuan pendanaan user
    pengajuan = cursor.execute('''
        SELECT * FROM crowdfunding_requests 
        WHERE investy_id = ?
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('investy_pendanaan.html', requests=pengajuan)


# Upload cover image
@app.route('/upload_cover/<int:request_id>', methods=['POST'])
def upload_cover(request_id):
    if 'cover_image' not in request.files:
        flash('Tidak ada file yang diunggah.', 'danger')
        return redirect(request.referrer)

    file = request.files['cover_image']
    if file.filename == '':
        flash('Nama file kosong.', 'danger')
        return redirect(request.referrer)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        conn = get_db_connection()
        conn.execute('UPDATE crowdfunding_requests SET cover_image = ? WHERE id = ?', (filename, request_id))
        conn.commit()
        conn.close()

        flash('Cover berhasil diunggah.', 'success')
    else:
        flash('Format file tidak didukung. Hanya PDF/JPG/PNG.', 'danger')

    return redirect(url_for('pengajuan_pendanaan'))

# Upload dokumen Investy 
@app.route('/upload_document/<int:request_id>', methods=['POST'])
def upload_document(request_id):
    if 'document' not in request.files:
        flash('Tidak ada file yang dipilih.', 'danger')
        return redirect(request.referrer)

    file = request.files['document']
    if file.filename == '':
        flash('Nama file kosong.', 'danger')
        return redirect(request.referrer)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        conn = get_db_connection()
        conn.execute('UPDATE crowdfunding_requests SET document = ? WHERE id = ?', (filename, request_id))
        conn.commit()
        conn.close()

        flash('Dokumen berhasil diunggah.', 'success')
    else:
        flash('Format file tidak didukung. Hanya PDF/JPG/PNG.', 'danger')

    return redirect(url_for('pengajuan_pendanaan'))


# Route untuk Pesanan Investy
@app.route('/pesanan_investy')
def pesanan_investy():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = sqlite3.connect('myappdb.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT 
            o.order_date AS order_date,
            p.name AS product_name,
            SUM(o.quantity) AS total_quantity,
            SUM(o.total_price) AS total_price,
            o.status
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.user_id = ?
        GROUP BY p.name, o.order_date, o.status
        ORDER BY o.order_date DESC
    ''', (user_id,))
    pesanan = c.fetchall()
    conn.close()

    return render_template('pesanan_investy.html', pesanan=pesanan)

@app.route('/pesanan_masuk')
def pesanan_masuk():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('myappdb.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
    SELECT o.*, u.fullname, u.email, p.name as product_name
    FROM orders o
    JOIN users u ON o.user_id = u.id
    JOIN products p ON o.product_id = p.id
    WHERE p.owner_id = ?
    ORDER BY o.order_date DESC
    '''
    
    cursor.execute(query, (user_id,))
    pesanan = cursor.fetchall()
    conn.close()
    
    return render_template('pesanan_masuk.html', pesanan=pesanan)

# Route untuk Portfolio Investy
@app.route('/portofolio_investy')
def portofolio_investy():
    investy_id = session.get('user_id')
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM crowdfunding_requests WHERE investy_id = ?', (investy_id,)).fetchall()
    conn.close()
    return render_template('portofolio_investy.html', rows=rows)

@app.route('/marketplace_investy')
def marketplace_investy():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('marketplace_investy.html', products=products)


@app.route('/checkout-form-investy')
def show_checkout_form_investy():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Jika kamu pakai sistem role, bisa cek dulu apakah user ini investy
    return render_template('investy_checkout.html')

@app.route('/checkout_investy', methods=['POST'])
def checkout_investy():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    nama = request.form.get('nama')
    alamat = request.form.get('alamat')

    # Proses checkout untuk Investy (sama seperti investor bisa disesuaikan)
    # Simpan ke orders atau tabel lain jika dibedakan

    return render_template('checkout_success.html', nama=nama)


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)


