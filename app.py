from flask import Flask, current_app, render_template, session, request, redirect, url_for
import home_routes
import crudDB_routes
import hal_admin_routes
import diskusi_routes
import mysql.connector


app = Flask(__name__)
UPLOAD_FOLDER = r'static/bukti'
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Fungsi untuk koneksi ke database
def koneksi():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="db_sirjama"
    )

# Route untuk halaman login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = cek_login(username, password)
        if user:
            session['username'] = username
            session['password'] = password
            
            
            if user['level_user'] == 'admin':
                return redirect(url_for('hal_admin.admin_val_Insert'))
            else:
                return redirect(url_for('home.index'))
        else:
            return "Username atau password salah."
    return render_template('login.html')

# Route untuk logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('password', None)
    return redirect(url_for('home.index'))

# Fungsi untuk memeriksa login pengguna
def cek_login(username, password):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM user WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()
            return user
    except Exception as e:
        print("Error:", e)
        return None
    finally:
        if 'connection' in locals():
            connection.close()
def cek_email(email):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                return True
            else:
                return False
    except Exception as e:
        print("Error:", e)
        return True  
    finally:
        if 'connection' in locals():
            connection.close()
# Fungsi untuk memeriksa apakah username sudah ada
def cek_username(username):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user:
                return True
            else:
                return False
    except Exception as e:
        print("Error:", e)
        return True  # Return True agar tidak bisa menggunakan username yang sama
    finally:
        if 'connection' in locals():
            connection.close()

# Fungsi untuk menambahkan user baru ke database
def tambah_user(username, password, email):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("INSERT INTO user (username, password, email) VALUES (%s, %s, %s)", (username, password, email))
            connection.commit()
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()
# Route untuk halaman registrasi
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        again_password = request.form['again_password']
        email = request.form['email']

        if not username or not password or not again_password or not email:
            return "Semua kolom harus diisi!"

        if password != again_password:
            return "Password dan konfirmasi password tidak cocok. Silakan coba lagi."

        # Cek apakah username sudah ada di database
        if cek_username(username):
            return "Username sudah digunakan. Silakan gunakan username lain."
        
        if cek_email(email):
            return "Email sudah digunakan."

        # Tambahkan user baru ke database
        tambah_user(username, password, email)
        return redirect(url_for('login'))
    
    return render_template('register.html')

app.koneksi=koneksi
app.cek_login=cek_login
# Register blueprint dengan argumen tambahan
app.register_blueprint(home_routes.bp)
app.register_blueprint(crudDB_routes.bp)
app.register_blueprint(hal_admin_routes.bp)
app.register_blueprint(diskusi_routes.bp)

if __name__ == "__main__":
    app.run(debug=True)
