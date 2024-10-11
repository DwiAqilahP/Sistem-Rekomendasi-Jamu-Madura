from flask import Blueprint, current_app, render_template, request, session, url_for, redirect
import datetime

bp = Blueprint('hal_diskusi', __name__)

@bp.route('/diskusi', methods=['GET', 'POST'])
def diskusi():
    if 'username' not in session or 'password' not in session:
        return redirect(url_for('login'))
    username = session['username']
    password = session['password']
    user = current_app.cek_login(username,password)
    if user and user['level_user'] != 'user':
        return "Anda tidak memiliki izin untuk menambah data jamu."
    id_user = user['id_user']
    if request.method == 'POST':
        try:
            connection = current_app.koneksi()
            if connection.is_connected():
                cursor = connection.cursor()
                isi_pesan = request.form['isi_pesan']
                tgl_pesan = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                id_balas_pesan = request.form.get('id_balas_pesan', None)

                if id_balas_pesan: 
                    cursor.execute("INSERT INTO diskusi (id_user, isi_pesan, tgl_pesan, id_balas_pesan) VALUES (%s, %s, %s, %s)", (id_user, isi_pesan, tgl_pesan, id_balas_pesan))
                else: 
                    cursor.execute("INSERT INTO diskusi (id_user, isi_pesan, tgl_pesan) VALUES (%s, %s, %s)", (id_user, isi_pesan, tgl_pesan))

                connection.commit()
                return redirect(url_for('hal_diskusi.diskusi'))
        except Exception as e:
            print("Error:", e)
        finally:
            if 'connection' in locals():
                connection.close()
    else:
        try:
            connection = current_app.koneksi()
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT diskusi.*, user.username FROM diskusi JOIN user ON user.id_user = diskusi.id_user")
                diskusi = cursor.fetchall()
                current_user = session.get('username')
                return render_template('diskusi.html', diskusi=diskusi, current_user=current_user)
        except Exception as e:
            print("Error:", e)
        finally:
            if 'connection' in locals():
                connection.close()
    return redirect(url_for('hal_diskusi.diskusi'))
