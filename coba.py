import pandas as pd
import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template,session, request, redirect, url_for
import datetime
import mysql.connector
import math
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
import nltk
nltk.download('punkt')
from gensim.models import Word2Vec
from nltk.tokenize import word_tokenize

UPLOAD_FOLDER = 'bukti'
format_file = {'txt', 'pdf','word', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def koneksi():
    return mysql.connector.connect(
        host="localhost",
        user="root",  
        password="",  
        database="db_sisijamu"
    )

# Fungsi untuk mengambil data jamu dari database MySQL
def ambil_data_jamu(start, items_per_page):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM jamu LIMIT %s, %s", (start, items_per_page))
            data_jamu = cursor.fetchall()
            return data_jamu
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

def get_total_data_jamu():
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM jamu")
            total_data = cursor.fetchone()[0]
            return total_data
    except Exception as e:
        print("Error in get_total_data_jamu:", e)
        return None
    finally:
        if 'connection' in locals():
            connection.close()

# Menampilkan data jamu dengan pagination
@app.route('/database')
def database_jamu():
    page = int(request.args.get('page', 1))
    items_per_page = 10  
    start = (page - 1) * items_per_page

    total_items = get_total_data_jamu()
    total_pages = math.ceil(total_items / items_per_page)

    jamu = ambil_data_jamu(start, items_per_page)

    return render_template('database_jamu.html', jamu=jamu, page=page, total_pages=total_pages)

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

# Route untuk menambahkan data jamu
@app.route('/tambah', methods=['GET'])
def tambah_form():
    return render_template('tambah_data1.html')


# Fungsi untuk memeriksa apakah ekstensi file diperbolehkan
def cek_ekstensi(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in format_file

# Route untuk menambahkan data jamu ke database
@app.route('/tambah', methods=['POST'])
def tambah_data():
    if request.method == 'POST':
        if 'username' not in session or 'password' not in session:
            return redirect(url_for('login'))

        username = session['username']
        password = session['password']
        user = cek_login(username, password)
        if user and user['level_user'] != 'user':
            return "Anda tidak memiliki izin untuk menambah data jamu."
        
        nama_jamu = request.form['nama_jamu']
        khasiat = request.form['khasiat']
        kandungan = request.form['kandungan']
        id_user = user['id_user']

        # preprcessing
        metadata = khasiat + ' ' + kandungan
        preprocessed_metadata = preprocess_metadata(metadata)
        
        # Periksa apakah file bukti diunggah
        if 'bukti' not in request.files:
            return "File bukti tidak ditemukan"
        
        bukti = request.files['bukti']
        # Jika pengguna tidak memilih file, browser mengirimkan data tanpa nama file
        if bukti.filename == '':
            return "Tidak ada file yang dipilih"
        
        # Jika file bukti ada dan memiliki ekstensi yang diizinkan
        if bukti and cek_ekstensi(bukti.filename):
            # Aman untuk menyimpan file bukti
            filename = secure_filename(bukti.filename)
            bukti.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            try:
                connection = koneksi()
                if connection.is_connected():
                    cursor = connection.cursor()
                    tgl_insert = datetime.datetime.now()
                    cursor.execute("INSERT INTO validasi_insert (id_user, bukti, tgl_masuk_in, nama_jamu_in, khasiat_in, kandungan_in, METADATA, PREPRO_METADATA) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                                   (id_user, filename, tgl_insert, nama_jamu, khasiat, kandungan,metadata,preprocessed_metadata))
                    connection.commit()
            except Exception as e:
                print("Error:", e)
            finally:
                if 'connection' in locals():
                    connection.close()
        else:
            return "Ekstensi file tidak diizinkan"
    return redirect(url_for('index'))

# Route untuk menampilkan formulir edit data jamu
@app.route('/edit/<int:id>', methods=['GET'])
def edit_form(id):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM jamu WHERE ID_JAMU = %s", (id,))
            data_jamu = cursor.fetchone()
            return render_template('edit_data1.html', jamu=data_jamu)
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

# Route untuk memproses perubahan data jamu
@app.route('/edit/<int:id>', methods=['POST'])
def edit_data(id):
    if request.method == 'POST':
        if 'username' not in session or 'password' not in session:
            return redirect(url_for('login'))
        
        username = session['username']
        password = session['password']
        user = cek_login(username, password)
        if user and user['level_user'] != 'user':
            return "Anda tidak memiliki izin untuk menambah data jamu."
        
        nama_jamu = request.form['nama_jamu']
        khasiat = request.form['khasiat']
        kandungan = request.form['kandungan']
        id_user = user['id_user']

        # preprcessing
        metadata = khasiat + ' ' + kandungan
        preprocessed_metadata = preprocess_metadata(metadata)
        
        # Periksa apakah file bukti diunggah
        if 'bukti' not in request.files:
            return "File bukti tidak ditemukan"
        
        bukti = request.files['bukti']
        
        # Jika pengguna tidak memilih file, browser mengirimkan data tanpa nama file
        if bukti.filename == '':
            return "Tidak ada file yang dipilih"
        
        # Jika file bukti ada dan memiliki ekstensi yang diizinkan
        if bukti and cek_ekstensi(bukti.filename):
            # Aman untuk menyimpan file bukti
            filename = secure_filename(bukti.filename)
            bukti.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            try:
                connection = koneksi()
                if connection.is_connected():
                    cursor = connection.cursor()
                    tgl_insert = datetime.datetime.now()
                    cursor.execute("INSERT INTO validasi_update (id_jamu, id_user, bukti_up, tgl_masuk_up, nama_jamu_up, khasiat_up, kandungan_up, METADATA, PREPRO_METADATA) VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s)",
                                   (id, id_user, filename, tgl_insert, nama_jamu, khasiat, kandungan, metadata, preprocessed_metadata))
                    connection.commit()
            except Exception as e:
                print("Error:", e)
            finally:
                if 'connection' in locals():
                    connection.close()
        else:
            return "Ekstensi file tidak diizinkan"
    return redirect(url_for('index'))

# Route untuk menampilkan formulir edit data jamu
@app.route('/hapus/<int:id>', methods=['GET'])
def hapus_form(id):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM jamu WHERE ID_JAMU = %s", (id,))
            data_jamu = cursor.fetchone()
            return render_template('hapus_data1.html', jamu=data_jamu)
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()
# Route untuk menghapus data jamu
@app.route('/hapus/<int:id>', methods=['POST'])
def hapus_jamu(id):
    if request.method == 'POST':
        if 'username' not in session or 'password' not in session:
            return redirect(url_for('login'))

        username = session['username']
        password = session['password']
        user = cek_login(username, password)
        if user and user['level_user'] != 'user':
            return "Anda tidak memiliki izin untuk menambah data jamu."
        id_user = user['id_user']
        
        # Periksa apakah file bukti diunggah
        if 'bukti' not in request.files:
            return "File bukti tidak ditemukan"
        
        bukti = request.files['bukti']
        
        # Jika pengguna tidak memilih file, browser mengirimkan data tanpa nama file
        if bukti.filename == '':
            return "Tidak ada file yang dipilih"
        
        # Jika file bukti ada dan memiliki ekstensi yang diizinkan
        if bukti and cek_ekstensi(bukti.filename):
            # Aman untuk menyimpan file bukti
            filename = secure_filename(bukti.filename)
            bukti.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            tgl_insert = datetime.datetime.now()
            cursor.execute("INSERT INTO validasi_delete (id_jamu, id_user, bukti_del, tgl_masuk_del) VALUES (%s, %s, %s, %s)",
                            (id, id_user, filename, tgl_insert))
            connection.commit()
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()
    return redirect(url_for('index'))
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
            
            # Periksa level pengguna dan arahkan sesuai ke halaman yang sesuai
            if user['level_user'] == 'admin':
                return redirect(url_for('admin_val_Insert'))
            else:
                return redirect(url_for('index'))
        else:
            return "Username atau password salah."
    return render_template('login.html')

# Route untuk logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('password', None)
    return redirect(url_for('index'))

# Fungsi untuk mencari data jamu berdasarkan pencarian teks dan filter
def data_preprocessing():
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Query dasar untuk mencari data jamu
            query = "SELECT * FROM jamu"
            cursor.execute(query)
            prepro_metadata = cursor.fetchall()
            
            # Menghapus spasi berlebihan dan menggunakan koma sebagai pemisah
            prepro_list1 = [' '.join(doc['PREPRO_METADATA'].split()) for doc in prepro_metadata]
            return prepro_list1
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

# Fungsi untuk mendapatkan total data jamu berdasarkan pencarian teks dan filter
def total_data_jamu(cari, kabupaten_filters, jenis_filters, perizinan_filters):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            # Query dasar untuk menghitung total data jamu
            query = "SELECT COUNT(*) FROM jamu WHERE nama_jamu LIKE %s OR KHASIAT LIKE %s"
            params = ('%' + cari + '%',)
            
            # Tambahkan filter berdasarkan kabupaten
            if kabupaten_filters:
                query += " AND kabupaten IN %s"
                params += (tuple(kabupaten_filters),)
            
            # Tambahkan filter berdasarkan jenis
            if jenis_filters:
                query += " AND jenis IN %s"
                params += (tuple(jenis_filters),)
            
            # Tambahkan filter berdasarkan perizinan
            if perizinan_filters:
                query += " AND perizinan IN %s"
                params += (tuple(perizinan_filters),)
            
            cursor.execute(query, params)
            total_data = cursor.fetchone()[0]
            return total_data
    except Exception as e:
        print("Error in total_data_jamu:", e)
        return None
    finally:
        if 'connection' in locals():
            connection.close()

def ambil_dokumen_prepro(kabupaten_filters, jenis_filters, perizinan_filters):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Inisialisasi list untuk menyimpan kondisi-kondisi
            where_conditions = []
            if kabupaten_filters:
                # Jika kabupaten_filters tidak kosong, tambahkan kondisi untuk kabupaten
                kabupaten_values = ",".join([f"'{value}'" for value in kabupaten_filters])
                where_conditions.append(f"(kabupaten IN ({kabupaten_values}))")

            if jenis_filters:
                # Jika jenis_filters tidak kosong, tambahkan kondisi untuk jenis
                jenis_values = ",".join([f"'{value}'" for value in jenis_filters])
                where_conditions.append(f"(jenis IN ({jenis_values}))")

            if perizinan_filters:
                # Jika perizinan_filters tidak kosong, tambahkan kondisi untuk perizinan
                perizinan_values = ",".join([f"'{value}'" for value in perizinan_filters])
                where_conditions.append(f"(perizinan IN ({perizinan_values}))")

            # Gabungkan semua kondisi dengan klausa "AND"
            where_clause_str = " AND ".join(where_conditions)
            
            # Buat query berdasarkan klausa WHERE
            query = "SELECT * FROM jamu"
            if where_clause_str:
                query += f" WHERE {where_clause_str};"
            else:
                query += ";"
            
            print(query)
            cursor.execute(query)
            data_jamu = cursor.fetchall()
            
            # Menghapus spasi berlebihan dan menggunakan koma sebagai pemisah
            # prepro_list = [f"{doc['ID_JAMU']}. {' '.join(doc['PREPRO_METADATA'].split())}" for doc in data_jamu]
            prepro_list = [' '.join(doc['PREPRO_METADATA'].split()) for doc in data_jamu]
            
            return prepro_list,data_jamu
    except Exception as e:
        print("Error:", e)
        return None
    finally:
        if 'connection' in locals():
            connection.close()


def ambil_data_word2vec(kabupaten_filters, jenis_filters, perizinan_filters):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Inisialisasi kamus untuk menyimpan hasil
            word2vec_dict = {}
            # Inisialisasi list untuk menyimpan kondisi-kondisi
            where_conditions = []
            if kabupaten_filters:
                # Jika kabupaten_filters tidak kosong, tambahkan kondisi untuk kabupaten
                kabupaten_values = ",".join([f"'{value}'" for value in kabupaten_filters])
                where_conditions.append(f"(kabupaten IN ({kabupaten_values}))")

            if jenis_filters:
                # Jika jenis_filters tidak kosong, tambahkan kondisi untuk jenis
                jenis_values = ",".join([f"'{value}'" for value in jenis_filters])
                where_conditions.append(f"(jenis IN ({jenis_values}))")

            if perizinan_filters:
                # Jika perizinan_filters tidak kosong, tambahkan kondisi untuk perizinan
                perizinan_values = ",".join([f"'{value}'" for value in perizinan_filters])
                where_conditions.append(f"(perizinan IN ({perizinan_values}))")

            # Gabungkan semua kondisi dengan klausa "AND"
            where_clause_str = " AND ".join(where_conditions)
            
            # Buat query berdasarkan klausa WHERE
            query = "SELECT word2vec.id_jamu, bobot FROM word2vec JOIN jamu ON word2vec.id_jamu = jamu.id_jamu"
            if where_clause_str:
                query += f" WHERE {where_clause_str};"
            else:
                query += ";"
            
            cursor.execute(query)
            word2vec_results = cursor.fetchall()
            
            # Mengonversi hasil dari list ke dalam format kamus yang diinginkan
            for result in word2vec_results:
                id_jamu = result['id_jamu']
                bobot = [float(val.strip()) for val in result['bobot'].split(',')]
                word2vec_dict[f'vektor_word2vec_dokumen_{id_jamu}'] = bobot
                    
            return word2vec_dict
    except Exception as e:
        print("Error:", e)
        return None
    finally:
        if 'connection' in locals():
            connection.close()


def ambil_data_tfidf(kabupaten_filters, jenis_filters, perizinan_filters):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Inisialisasi kamus untuk menyimpan hasil
            word2vec_dict = {}
            # Inisialisasi list untuk menyimpan kondisi-kondisi
            where_conditions = []
            if kabupaten_filters:
                # Jika kabupaten_filters tidak kosong, tambahkan kondisi untuk kabupaten
                kabupaten_values = ",".join([f"'{value}'" for value in kabupaten_filters])
                where_conditions.append(f"(kabupaten IN ({kabupaten_values}))")

            if jenis_filters:
                # Jika jenis_filters tidak kosong, tambahkan kondisi untuk jenis
                jenis_values = ",".join([f"'{value}'" for value in jenis_filters])
                where_conditions.append(f"(jenis IN ({jenis_values}))")

            if perizinan_filters:
                # Jika perizinan_filters tidak kosong, tambahkan kondisi untuk perizinan
                perizinan_values = ",".join([f"'{value}'" for value in perizinan_filters])
                where_conditions.append(f"(perizinan IN ({perizinan_values}))")

            # Gabungkan semua kondisi dengan klausa "AND"
            where_clause_str = " AND ".join(where_conditions)
            
            # Buat query berdasarkan klausa WHERE
            query = "SELECT tfidf.id_jamu, term, bobot FROM tfidf JOIN jamu ON tfidf.id_jamu = jamu.id_jamu"
            if where_clause_str:
                query += f" WHERE {where_clause_str};"
            else:
                query += ";"
            
            cursor.execute(query)
            word2vec_results = cursor.fetchall()
            
            # Mengonversi hasil dari list ke dalam format kamus yang diinginkan
            for result in word2vec_results:
                id_jamu = result['id_jamu']
                terms = result['term'].split(',')
                weights = [float(val.strip()) for val in result['bobot'].split(',')]
                word2vec_dict[f'dokumen_preprocessed_{id_jamu}'] = {term: weight for term, weight in zip(terms, weights)}
                    
            return word2vec_dict
    except Exception as e:
        print("Error:", e)
        return None
    finally:
        if 'connection' in locals():
            connection.close()




@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        cari = request.form['searchInput']
        kabupaten_filters = request.form.getlist('kabupaten')
        jenis_filters = request.form.getlist('jenis')
        perizinan_filters = request.form.getlist('perizinan')

        # preprocessing query
        preprocessed_query = preprocess_query(cari)
        prepro_list, data_jamu = ambil_dokumen_prepro(kabupaten_filters, jenis_filters, perizinan_filters)
        dokumen_preprocessed = prepro_list
        # dokumen_preprocessed = '\n'.join(dokumen_preprocessed)
        dokumen= pd.DataFrame(data_jamu)
        # dokumen_preprocessed = data_preprocessing()
        # dokumenn = pd.DataFrame(dokumen_preprocessed)
        # dokumen_preprocessed.to_csv('dokumen_preprocessed.csv', index=False)

        
        # Training model Word2Vec
        model = train_word2vec_model(dokumen_preprocessed)
        # word2vec dokumen
        # bobot_word2vec2 = extract_document_features(model, dokumen_preprocessed)
        # word2vec query
        bobot_query = extract_query_features(model, preprocessed_query)
        # Word2vec = {**bobot_word2vec2, **bobot_query}

        # Tfidf
        token_dokumen_preprocessed = [dokumen_preprocessed.split() for dokumen_preprocessed in dokumen_preprocessed]
        token_preprocessed_query = preprocessed_query.split()
        # tf_dokumen_preprocessed = [hitung_tf(d) for d in token_dokumen_preprocessed]
        # # print(tf_dokumen_preprocessed)
        all_terms = [term for dokumen_preprocessed in token_dokumen_preprocessed for term in dokumen_preprocessed]
        counter_all_terms = Counter(all_terms)
        idf = {term: hitung_idf(term, token_dokumen_preprocessed, default_idf) for term in counter_all_terms}
        # # print('idf=',idf)
        # tfidf_dokumen_preprocessed = {'dokumen_preprocessed_{}'.format(i+1): hitung_tfidf(tf_dokumen_preprocessed[i], idf,default_idf) for i in range(len(tf_dokumen_preprocessed))}
        tf_preprocessed_query = hitung_tf(token_preprocessed_query)
        # print(tf_preprocessed_query)
        tfidf_preprocessed_query = hitung_tfidf(tf_preprocessed_query, idf,default_idf)
        # print(tfidf_preprocessed_query)

        # word2vec dan TF-IDF
        bobot_word2vec = ambil_data_word2vec(kabupaten_filters, jenis_filters, perizinan_filters)
        Word2vec = {**bobot_word2vec, **bobot_query}
        tfidf_dokumen_preprocessed = ambil_data_tfidf(kabupaten_filters, jenis_filters, perizinan_filters)
        TFIDF = {**tfidf_dokumen_preprocessed, 'preprocessed_query': tfidf_preprocessed_query}
        result = kombinasiTfidfWord2vec(TFIDF, Word2vec)
        # query = kombinasi['preprocessed_query']
        # cosine_similarities = cosine_similarity(result)
        # Mengkuadratkan hasil dari perhitungan
        squared_results = {}
        for doc, doc_result in result.items():
            squared_results[doc] = square_values(doc_result)

        # Menampilkan hasil
        # for doc, doc_result in squared_results.items():
        #     print(f"{doc} = ")
        #     print(doc_result)

        # Menjumlahkan nilai-nilai kuadrat dari setiap dokumen
        sum_of_squared_results = {}
        for doc, doc_result in squared_results.items():
            sum_of_squared_results[doc] = sum(doc_result.values())

        # Menampilkan hasil penjumlahan
        # print("Jumlah nilai-nilai kuadrat dari setiap dokumen:")
        # for doc, total in sum_of_squared_results.items():
        #     print(f"{doc}: {total}")
        # Melakukan perkalian antara query dan hasil dokumen-dokumen
        query_result_multiplied = calculate_query_document_multiplication(result['preprocessed_query'], result)

        # Menampilkan hasil
        # print("Hasil perkalian antara query dan dokumen-dokumen:")
        # for doc_name, doc_result in query_result_multiplied.items():
        #     print(f"Dokumen {doc_name}:")
        #     for key, value in doc_result.items():
        #         print(f"{key}: {value}")
        #     print()
        aquery= {'jamu': 0.6148981273249238,
                'kurang': 0.3610959046094567,
                'stres': 0.0,
                'tingkat': 0.413764734798886,
                'sehat': 0.3499967471801715,
                'mental': 0.0,
                'kualitas': 0.7417992386826573,
                'tidur': 0.0}
        ad4= {'awat': 0.23493488843523896,
                'khusus': 0.20657286890781013,
                'remaja': 0.25505813356268686,
                'putri': 0.2834201530901155,
                'kurang': 0.1379643591254856,
                'bau': 0.11894279559202955,
                'badan': 0.10674682600450705,
                'atas': 0.11568864721118008,
                'putih': 0.07745820206037725,
                'daun': 0.10960233959805687,
                'sirih': 0.10674682600450705,
                'kunyit': 0.08732662768375127,
                'kulit': 0.11257929587024265,
                'manggis': 0.25505813356268686,
                'kunci': 0.13372369031141973,
                'pinang': 0.12972542366094422,
                'muda': 0.12594346671525392}
        q=result['preprocessed_query']
        d4=result['dokumen_preprocessed_4']
        hasil = multiply_values(result['preprocessed_query'], result['dokumen_preprocessed_4'])
        print('hasil=',hasil)
        # dict1=dict1
        # hasil = multiplied_dict
        q1=aquery
        d41=ad4
        # multiplied_dict,dict1 = multiply_values(q1, d41)
        # dict1=dict1
        # hasil=multiplied_dict
        # hasil1 = multiply_values(aquery, ad4)

        
        # Menjumlahkan hasil perkalian menjadi perdokumen
        sum_per_document = sum_values_per_document(query_result_multiplied)

        # print("Jumlah hasil perkalian menjadi perdokumen:")
        # for doc_name, doc_result in sum_per_document.items():
        #     print(f"Dokumen {doc_name}: {doc_result}")

        print("Hasil perhitungan cosine similarity untuk setiap dokumen:")
        cosine_similarities = []

        # Iterasi melalui hasil perkalian query dengan setiap dokumen
        for doc_name, doc_result in query_result_multiplied.items():
            # Memeriksa apakah dokumen bukan query
            if doc_name != 'preprocessed_query':
                # Mengambil nilai total hasil perkalian query dengan dokumen dari dictionary sum_per_document
                totalQxD = sum_per_document[doc_name]
                # Menghitung penyebut cosine similarity
                sqrtQD = math.sqrt(sum_of_squared_results['preprocessed_query'] * sum_of_squared_results[doc_name])
                # Menghitung cosine similarity antara query dan dokumen
                result = totalQxD / sqrtQD if sqrtQD != 0 else 0
                # Menambahkan hasil cosine similarity ke dalam list
                cosine_similarities.append((doc_name, result))

        # Mengurutkan hasil secara descending berdasarkan cosine similarity
        cosine_similarities_sorted = sorted(cosine_similarities, key=lambda x: x[1], reverse=True)

        top_5_results = cosine_similarities_sorted[:5]
        # Get detailed jamu data based on ID
        detailed_results = []
        for result in top_5_results:
            id_jamu = result[0].split('_')[-1]
            jamu_details = dokumen[dokumen['ID_JAMU'] == int(id_jamu)].to_dict(orient='records')[0]
            detailed_results.append((result[0], result[1], jamu_details))

        return render_template('hasil_pencarian.html',idf=idf,tfidf_preprocessed_query=tfidf_preprocessed_query,query_result_multiplied=query_result_multiplied,q1=q1,d41=d41,q=q,d4=d4, hasil=hasil, cari=cari, preprocessed_query=preprocessed_query, top_5_results=detailed_results)
    return render_template('index1.html')



def ambil_data_validasi_insert():
    try:
        connection = koneksi()
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

@app.route('/admin')
def admin_val_Insert():
    if 'username' in session and 'password' in session:
        username = session['username']
        password = session['password']
        
        user = cek_login(username, password)
        if user and user['level_user'] == 'admin':
            val_insert = ambil_data_validasi_insert()
            # Tampilkan halaman admin_index.html
            return render_template('admin/index.html', val_insert=val_insert)
    
    # Jika pengguna bukan admin atau tidak ada sesi yang terautentikasi, arahkan kembali ke login
    return redirect(url_for('login'))

# Tambahkan route baru di bawah route '/admin'
@app.route('/validasi_in/<int:id>/<status>', methods=['POST'])
def val_insert(id, status):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            tgl_val = datetime.datetime.now()
            cursor.execute("UPDATE validasi_insert SET validasi_in = %s, tgl_validasi_in = %s WHERE id_validasi_in = %s", (status,tgl_val, id))
            connection.commit()
            update_word2vec_tfidf()
            return redirect(url_for('admin_val_Insert')) 
    except Exception as e:
        print("Error:", e)
        return 'Terjadi kesalahan saat menyimpan validasi'
    finally:
        if 'connection' in locals():
            connection.close()

def ambil_data_validasi_update():
    try:
        connection = koneksi()
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

# validasi update admin 
@app.route('/validasi_up')
def admin_val_update():
    if 'username' in session and 'password' in session:
        username = session['username']
        password = session['password']
        
        user = cek_login(username, password)
        if user and user['level_user'] == 'admin':
            val_update = ambil_data_validasi_update()
            # Tampilkan halaman admin_index.html
            return render_template('admin/val_update.html', val_update=val_update)
    
    # Jika pengguna bukan admin atau tidak ada sesi yang terautentikasi, arahkan kembali ke login
    return redirect(url_for('login'))

@app.route('/validasi_up/<int:id>/<status>', methods=['POST'])
def val_update(id, status):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            tgl_val = datetime.datetime.now()
            cursor.execute("UPDATE validasi_update SET validasi_up = %s, tgl_validasi_up = %s WHERE id_validasi_up = %s", (status,tgl_val, id))
            connection.commit()
            update_word2vec_tfidf()
            return redirect(url_for('admin_val_update')) 
    except Exception as e:
        print("Error:", e)
        return 'Terjadi kesalahan saat menyimpan validasi'
    finally:
        if 'connection' in locals():
            connection.close()

def ambil_data_validasi_delete():
    try:
        connection = koneksi()
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
@app.route('/validasi_del')
def admin_val_delete():
    if 'username' in session and 'password' in session:
        username = session['username']
        password = session['password']
        
        user = cek_login(username, password)
        if user and user['level_user'] == 'admin':
            val_delete = ambil_data_validasi_delete()
            # Tampilkan halaman admin_index.html
            return render_template('admin/val_delete.html', val_delete=val_delete)
    
    # Jika pengguna bukan admin atau tidak ada sesi yang terautentikasi, arahkan kembali ke login
    return redirect(url_for('login'))

@app.route('/validasi_del/<int:id>/<status>', methods=['POST'])
def val_delete(id, status):
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()
            tgl_val = datetime.datetime.now()
            cursor.execute("UPDATE validasi_delete SET validasi_del= %s, tgl_validasi_del= %s WHERE id_delete= %s", (status,tgl_val, id))
            connection.commit()
            update_word2vec_tfidf()
            return redirect(url_for('admin_val_delete')) 
    except Exception as e:
        print("Error:", e)
        return 'Terjadi kesalahan saat menyimpan validasi'
    finally:
        if 'connection' in locals():
            connection.close()

def preprocessing(text):
    # Case folding
    text = text.lower()

    # Tokenization
    tokens = word_tokenize(text)

    # Stopword removal
    stop_re = set(stopwords.words('indonesian'))
    stop_word = [token for token in tokens if token not in stop_re]

    # Stemming
    stemm = StemmerFactory().create_stemmer()
    stemming_token = [stemm.stem(token) for token in stop_word]

    return stemming_token

def preprocess_query(query):
    preprocessed_tokens = preprocessing(query)
    return ' '.join(preprocessed_tokens)

def preprocess_metadata(metadata):
    preprocessed_tokens = preprocessing(metadata)
    return ' '.join(preprocessed_tokens)

# Training model Word2Vec
def train_word2vec_model(dokumen):
    token_dokumen = [word_tokenize(doc.lower()) for doc in dokumen]
    model = Word2Vec(sentences=token_dokumen, vector_size=100, window=3, min_count=1, sg=1)
    return model

# Ekstraksi fitur untuk dokumen
def extract_document_features(model, dokumen):
    fitur_dokumen = {}
    for i, doc in enumerate(dokumen, start=1):
        vektor_doc = []
        for kata in doc:
            if kata in model.wv:
                vektor_doc.append(model.wv[kata])
        if vektor_doc:
            fitur_dokumen[f'vektor_word2vec_dokumen_{i}'] = list(sum(vektor_doc) / len(vektor_doc))
        else:
            fitur_dokumen[f'vektor_word2vec_dokumen_{i}'] = [0] * model.vector_size
    return fitur_dokumen

# Ekstraksi fitur untuk query
def extract_query_features(model, query):
    token_query = word_tokenize(query.lower())
    fitur_query = []
    for kata in token_query:
        if kata in model.wv:
            fitur_query.append(model.wv[kata])
    if fitur_query:
        fitur_query = list(sum(fitur_query) / len(fitur_query))
    else:
        fitur_query = [0] * model.vector_size
    return {'vektor_word2vec_dokumen_query': fitur_query}

# Fungsi untuk memperbarui model Word2Vec dan nilai Word2Vec setiap kali ada perubahan pada data jamu
def update_word2vec_tfidf():
    try:
        connection = koneksi()
        if connection.is_connected():
            cursor = connection.cursor()

            cursor.execute("DELETE FROM word2vec")
            cursor.execute("ALTER TABLE word2vec AUTO_INCREMENT = 1")
            cursor.execute("DELETE FROM tfidf")
            cursor.execute("ALTER TABLE tfidf AUTO_INCREMENT = 1")
            
            dokumen_preprocessed = data_preprocessing()

            token_dokumen_preprocessed = [dokumen_preprocessed.split() for dokumen_preprocessed in dokumen_preprocessed]

            tf_dokumen_preprocessed = [hitung_tf(d) for d in token_dokumen_preprocessed]

            all_terms = [term for dokumen_preprocessed in token_dokumen_preprocessed for term in dokumen_preprocessed]
            counter_all_terms = Counter(all_terms)
            idf = {term: hitung_idf(term, token_dokumen_preprocessed, default_idf) for term in counter_all_terms}

            tfidf_dokumen_preprocessed = {'dokumen_preprocessed_{}'.format(i+1): hitung_tfidf(tf_dokumen_preprocessed[i], idf,default_idf) for i in range(len(tf_dokumen_preprocessed))}
            
            print("Hasil TF-IDF untuk setiap kata pada setiap dokumen_preprocessed dan preprocessed_query:")
            for doc, values in tfidf_dokumen_preprocessed.items():
                print(f"{doc}:")
                for term, nilai_tfidf in values.items():
                    print(f"   {term}: {nilai_tfidf}")
            
            # Simpan hasil TF-IDF ke dalam database
            for i, (doc, values) in enumerate(tfidf_dokumen_preprocessed.items()):
                id_jamu = int(doc.split('_')[-1])
                terms = ', '.join(values.keys())
                weights = ', '.join(map(str, values.values()))
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                insert_query = "INSERT INTO tfidf (id_jamu, term, bobot, datetime) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (id_jamu, terms, weights, current_time))

            # Train Word2Vec model
            model = train_word2vec_model(dokumen_preprocessed)

            # Extract features for documents
            fitur_dokumen = extract_document_features(model, dokumen_preprocessed)

            # Insert Word2Vec features into database
            for i, (doc, features) in enumerate(fitur_dokumen.items()):
                id_jamu = int(doc.split('_')[-1])
                features_str = ', '.join(map(str, features))
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                insert_query = "INSERT INTO word2vec (id_jamu, bobot, datetime) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (id_jamu, features_str, current_time))

            connection.commit()
            print("Data berhasil disimpan ke dalam tabel word2vec.")
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()


def hitung_tf(dokumen_preprocessed):
    frekuensi_term = Counter(dokumen_preprocessed)
    return frekuensi_term

def hitung_idf(term, korpus, default_idf):
    total_dokumen_preprocessed = len(korpus)
    dokumen_preprocessed_term = sum(1 for doc in korpus if term in doc)
    if dokumen_preprocessed_term == 0:
        return default_idf
    idf = math.log10(total_dokumen_preprocessed / (dokumen_preprocessed_term+1))
    return idf
default_idf = 0

def hitung_tfidf(tf_dokumen, idf, default_idf):
    tfidf = {}
    for term, tf in tf_dokumen.items():
        if term in idf:
            tfidf[term] = round(tf * idf[term], 6)
        else:
            tfidf[term] = round(tf * default_idf, 6)  # Use default IDF value for terms not found in IDF dictionary
    return tfidf

def kombinasiTfidfWord2vec(tfidf, word2vec):
    result = {}
    for doc, tfidf_values in tfidf.items():
        doc_name = doc.split('_')[-1]
        word_vec_key = 'vektor_word2vec_dokumen_' + doc_name
        word_vector = word2vec[word_vec_key]
        doc_result = {}
        for word, tfidf_value in tfidf_values.items():
            doc_result[word] = sum(tfidf_value * word_vec for tfidf_value, word_vec in zip([tfidf_value]*len(word_vector), word_vector))
        result[doc] = doc_result
    return result

# cosine Similarity
# Fungsi untuk mengkuadratkan nilai-nilai dalam kamus
def square_values(dictionary):
    squared_dict = {key: value**2 for key, value in dictionary.items()}
    return squared_dict
# Fungsi untuk mengalikan nilai-nilai dalam dua kamus
def multiply_values(dict1, dict2):
    # dict2=dict2
    # dict1=dict1
    print('dict1=',dict1)
    print("dict2=",dict2)
    multiplied_dict = {}
    # i = 0
    for key in dict1:
        # print(key)
        if key in dict2:
            # print ("dok ke -",i)
            multiplied_dict[key] = dict1[key] * dict2[key]
            # print('bisa')
            # print(multiplied_dict[key],'=',dict1[key],'dikali',dict2[key] )
            # i += 1
        elif (" "+key) in dict2:
            multiplied_dict[key] = dict1[key] * dict2[(" "+key)]
        else:
            multiplied_dict[key] = 0 # Jika kunci tidak ada dalam dict2, hasil perkaliannya adalah 0
            # print('gabisa')
            # i += 1
    return multiplied_dict


# Fungsi untuk melakukan perkalian antara query dan hasil dokumen-dokumen
def calculate_query_document_multiplication(query, documents):
    query_result_multiplied = {}
    # ir = 1
    for doc_name, doc_tfidf in documents.items():
        if doc_name != 'query':
            multiplied_dict = multiply_values(query, doc_tfidf)
            # if ir == 4:
            #     break
            # ir += 1
            query_result_multiplied[doc_name] = multiplied_dict
    return query_result_multiplied

# Fungsi untuk menjumlahkan hasil perkalian menjadi perdokumen
def sum_values_per_document(query_result_multiplied):
    sum_per_document = {}
    # Iterasi melalui setiap item (pasangan kunci-nilai) dalam dictionary query_result_multiplied
    for doc_name, doc_result in query_result_multiplied.items():
        # Menjumlahkan nilai-nilai dalam dictionary doc_result dan menyimpannya ke dalam sum_per_document
        sum_per_document[doc_name] = sum(doc_result.values())
    # Mengembalikan dictionary yang berisi jumlah hasil perhitungan per dokumen
    return sum_per_document


if __name__ == '__main__':
    app.run(debug=True)