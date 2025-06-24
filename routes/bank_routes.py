from flask import Blueprint, render_template
import sqlite3

bank_routes = Blueprint('bank_routes', __name__)



@bank_routes.route('/validasi_transaksi')
def validasi_transaksi():
    return render_template('validasi_transaksi.html')

@bank_routes.route('/laporan-keuangan')
def laporan_keuangan():
    conn = sqlite3.connect('myappdb.db')
    cursor = conn.cursor()

    # Total pemasukan
    cursor.execute("SELECT SUM(amount) FROM investments")
    total_pemasukan = cursor.fetchone()[0] or 0

    # Total pengeluaran
    cursor.execute("SELECT SUM(amount) FROM investment_usages")
    total_pengeluaran = cursor.fetchone()[0] or 0

    # Saldo akhir
    saldo_akhir = total_pemasukan - total_pengeluaran

    # Detail transaksi
    cursor.execute("""
        SELECT created_at AS tanggal, 'Investasi Masuk' AS keterangan, 'pemasukan' AS jenis, amount
        FROM investments
        UNION ALL
        SELECT used_at AS tanggal, description AS keterangan, 'pengeluaran' AS jenis, amount
        FROM investment_usages
        ORDER BY tanggal DESC
    """)
    laporan = cursor.fetchall()

    conn.close()

    return render_template('laporan_keuangan.html',
                           total_pemasukan=total_pemasukan,
                           total_pengeluaran=total_pengeluaran,
                           saldo_akhir=saldo_akhir,
                           laporan=laporan)



