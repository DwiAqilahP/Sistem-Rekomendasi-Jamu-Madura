from flask import Blueprint,current_app, render_template,session, redirect, url_for
import datetime
from home_routes import update_word2vec_tfidf

bp = Blueprint("hal_admin", __name__)

def ambil_data_validasi_insert():
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM validasi_insert WHERE validasi_in ='menunggu'")
            data_validasi_insert = cursor.fetchall()
            return data_validasi_insert
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

@bp.route('/admin')
def admin_val_Insert():
    if 'username' in session and 'password' in session:
        username = session['username']
        password = session['password']
        user = current_app.cek_login(username,password)
        if user and user['level_user'] == 'admin':
            val_insert = ambil_data_validasi_insert()
            return render_template('admin/index.html', val_insert=val_insert)    
    return redirect(url_for('login'))

@bp.route('/validasi_in/<int:id>/<status>', methods=['POST'])
def val_insert(id, status):
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            tgl_val = datetime.datetime.now()
            cursor.execute("UPDATE validasi_insert SET validasi_in = %s, tgl_validasi_in = %s WHERE id_validasi_in = %s", (status,tgl_val, id))
            connection.commit()
            update_word2vec_tfidf()
            return redirect(url_for('hal_admin.admin_val_Insert')) 
    except Exception as e:
        print("Error:", e)
        return 'Terjadi kesalahan saat menyimpan validasi'
    finally:
        if 'connection' in locals():
            connection.close()

def ambil_data_validasi_update():
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM validasi_update WHERE validasi_up ='menunggu'")
            data_validasi_insert = cursor.fetchall()
            return data_validasi_insert
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

@bp.route('/validasi_up')
def admin_val_update():
    if 'username' in session and 'password' in session:
        username = session['username']
        password = session['password']
        
        user = current_app.cek_login(username,password)
        if user and user['level_user'] == 'admin':
            val_update = ambil_data_validasi_update()
            return render_template('admin/val_update.html', val_update=val_update)
    return redirect(url_for('login'))

@bp.route('/validasi_up/<int:id>/<status>', methods=['POST'])
def val_update(id, status):
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            tgl_val = datetime.datetime.now()
            cursor.execute("UPDATE validasi_update SET validasi_up = %s, tgl_validasi_up = %s WHERE id_validasi_up = %s", (status,tgl_val, id))
            connection.commit()
            update_word2vec_tfidf()
            return redirect(url_for('hal_admin.admin_val_update')) 
    except Exception as e:
        print("Error:", e)
        return 'Terjadi kesalahan saat menyimpan validasi'
    finally:
        if 'connection' in locals():
            connection.close()

def ambil_data_validasi_delete():
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM validasi_delete WHERE validasi_del ='menunggu'")
            data_validasi_insert = cursor.fetchall()
            return data_validasi_insert
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

# validasi delete admin 
@bp.route('/validasi_del')
def admin_val_delete():
    if 'username' in session and 'password' in session:
        username = session['username']
        password = session['password']
        
        user =  current_app.cek_login(username,password)
        if user and user['level_user'] == 'admin':
            val_delete = ambil_data_validasi_delete()
            return render_template('admin/val_delete.html', val_delete=val_delete)
    
    return redirect(url_for('login'))

@bp.route('/validasi_del/<int:id>/<status>', methods=['POST'])
def val_delete(id, status):
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            tgl_val = datetime.datetime.now()
            cursor.execute("UPDATE validasi_delete SET validasi_del= %s, tgl_validasi_del= %s WHERE id_delete= %s", (status,tgl_val, id))
            connection.commit()
            update_word2vec_tfidf()
            return redirect(url_for('hal_admin.admin_val_delete')) 
    except Exception as e:
        print("Error:", e)
        return 'Terjadi kesalahan saat menyimpan validasi'
    finally:
        if 'connection' in locals():
            connection.close()
