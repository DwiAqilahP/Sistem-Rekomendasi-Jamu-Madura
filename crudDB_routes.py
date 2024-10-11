from flask import Flask,Blueprint,current_app, render_template,session, request, redirect, url_for
import math
import datetime
from werkzeug.utils import secure_filename
import os
from home_routes import preprocess_metadata, data_preprocessing,train_word2vec_model, extract_query_features, hitung_idf,hitung_tf,hitung_tfidf,ambil_data_word2vec, ambil_data_tfidf,kombinasiTfidfWord2vec,square_values, calculate_query_document_multiplication,sum_values_per_document
import pandas as pd
from collections import Counter
# UPLOAD_FOLDER = 'bukti'
format_file = {'txt', 'pdf','word', 'png', 'jpg', 'jpeg', 'gif'}
# app = Flask(__name__)
# app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
bp = Blueprint('crudDB', __name__)



# Fungsi untuk mengambil data jamu dari database MySQL
def ambil_data_jamu(start, items_per_page):
    try:
        connection = current_app.koneksi()
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
        connection = current_app.koneksi()
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
@bp.route("/database")
def database_jamu():
    page = int(request.args.get('page', 1))
    items_per_page = 10  
    start = (page - 1) * items_per_page

    total_items = get_total_data_jamu()
    total_pages = math.ceil(total_items / items_per_page)

    jamu = ambil_data_jamu(start, items_per_page)

    return render_template('database_jamu.html', jamu=jamu, page=page, total_pages=total_pages)

# @bp.route('/notifikasi', methods=['GET'])
# def notifikasi():
#     if 'username' not in session or 'password' not in session:
#         return redirect(url_for('login'))

#     username = session['username']
#     password = session['password']
#     user =  current_app.cek_login(username,password)
#     if user and user['level_user'] != 'user':
#         return "Anda tidak memiliki izin untuk menambah data jamu."
#     return render_template('notifikasi.html')

# Route untuk menambahkan data jamu
@bp.route('/tambah', methods=['GET'])
def tambah_form():
    if 'username' not in session or 'password' not in session:
        return redirect(url_for('login'))

    username = session['username']
    password = session['password']
    user =  current_app.cek_login(username,password)
    if user and user['level_user'] != 'user':
        return "Anda tidak memiliki izin untuk menambah data jamu."
    return render_template('tambah_data1.html')


# Fungsi untuk memeriksa apakah ekstensi file diperbolehkan
def cek_ekstensi(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in format_file

# Route untuk menambahkan data jamu ke database
@bp.route('/tambah', methods=['POST'])
def tambah_data():
    if request.method == 'POST':
        if 'username' not in session or 'password' not in session:
            return redirect(url_for('login'))

        username = session['username']
        password = session['password']
        user =  current_app.cek_login(username,password)
        if user and user['level_user'] != 'user':
            return "Anda tidak memiliki izin untuk menambah data jamu."
        
        nama_jamu = request.form['nama_jamu']
        khasiat = request.form['khasiat']
        kandungan = request.form['kandungan']
        aturan_minum = request.form['aturan_minum']
        efek_samping = request.form['efek_samping']
        jenis = request.form['jenis']
        produsen = request.form['produsen']
        lokasi_pemasaran = request.form['lokasi_pemasaran']
        lokasi_produksi = request.form['lokasi_produksi']
        kabupaten = request.form['kabupaten']
        perizinan = request.form['perizinan']
        id_user = user['id_user']

        # preprcessing
        metadata = nama_jamu +' '+khasiat + ' ' + kandungan
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
            bukti.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            try:
                connection = current_app.koneksi()
                if connection.is_connected():
                    cursor = connection.cursor()
                    tgl_insert = datetime.datetime.now()
                    cursor.execute("INSERT INTO validasi_insert (id_user, bukti, tgl_masuk_in, nama_jamu_in, khasiat_in, kandungan_in,aturan_minum_in,efek_samping_in,jenis_in,produsen_in,lokasi_pemasaran_in,lokasi_produksi_in,kabupaten_in,perizinan_in, METADATA, PREPRO_METADATA) VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s)",
                                   (id_user, filename, tgl_insert, nama_jamu, khasiat, kandungan,aturan_minum,efek_samping,jenis,produsen,lokasi_pemasaran,lokasi_produksi,kabupaten,perizinan,metadata,preprocessed_metadata))
                    connection.commit()
            except Exception as e:
                print("Error:", e)
            finally:
                if 'connection' in locals():
                    connection.close()
        else:
            return "Ekstensi file tidak diizinkan"
    return redirect(url_for('home.index'))

@bp.route('/lihat_detail/<int:id>', methods=['GET'])
def lihat_detail(id):
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM jamu WHERE ID_JAMU = %s", (id,))
            data_jamu = cursor.fetchone()
            preprocessed_query = data_jamu['PREPRO_METADATA']
            prepro_list1,prepro_metadata=data_preprocessing()
            dokumen_preprocessed = prepro_list1
            dokumen= pd.DataFrame(prepro_metadata)
            model = train_word2vec_model(dokumen_preprocessed)
            bobot_query = extract_query_features(model, preprocessed_query)
            token_dokumen_preprocessed = [dokumen_preprocessed.split() for dokumen_preprocessed in dokumen_preprocessed]
            token_preprocessed_query = preprocessed_query.split()
            all_terms = [term for dokumen_preprocessed in token_dokumen_preprocessed for term in dokumen_preprocessed]
            counter_all_terms = Counter(all_terms)
            default_idf=0
            idf = {term: hitung_idf(term, token_dokumen_preprocessed, default_idf) for term in counter_all_terms}
            tf_preprocessed_query = hitung_tf(token_preprocessed_query)
            tfidf_preprocessed_query = hitung_tfidf(tf_preprocessed_query, idf,default_idf)

            bobot_word2vec = ambil_data_word2vec('','','')
            Word2vec = {**bobot_word2vec, **bobot_query}
            tfidf_dokumen_preprocessed = ambil_data_tfidf('','','')
            print(tfidf_dokumen_preprocessed)
            TFIDF = {**tfidf_dokumen_preprocessed, 'preprocessed_query': tfidf_preprocessed_query}
            result = kombinasiTfidfWord2vec(TFIDF, Word2vec)
            squared_results = {}
            for doc, doc_result in result.items():
                squared_results[doc] = square_values(doc_result)

            
            sum_of_squared_results = {}
            for doc, doc_result in squared_results.items():
                sum_of_squared_results[doc] = sum(doc_result.values())

            
            query_result_multiplied = calculate_query_document_multiplication(result['preprocessed_query'], result)

            sum_per_document = sum_values_per_document(query_result_multiplied)
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
           
            top_5_results = cosine_similarities_sorted[1:6]
            detailed_results = []
            for result in top_5_results :
                id_jamu = result[0].split('_')[-1]
                jamu_details = dokumen[dokumen['ID_JAMU'] == int(id_jamu)].to_dict(orient='records')[0]
                bobot_word2vec_doc = bobot_word2vec.get(f'vektor_word2vec_dokumen_{id_jamu}', {})
                bobot_tfidf_doc = tfidf_dokumen_preprocessed.get(f'dokumen_preprocessed_{id_jamu}', {})
                detailed_results.append((result[0], result[1], jamu_details, bobot_word2vec_doc,bobot_tfidf_doc))   
            if data_jamu:
                cursor.execute("SELECT komentar.*, user.username FROM komentar JOIN user ON user.id_user = komentar.id_user WHERE ID_JAMU = %s", (id,))
                data_komentar = cursor.fetchall()
                return render_template('detail_jamu.html', jamu=data_jamu, komentar=data_komentar, top_5_results=detailed_results)
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

@bp.route('/lihat_detail1/<int:id>', methods=['GET'])
def lihat_detail1(id):
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM jamu WHERE ID_JAMU = %s", (id,))
            data_jamu = cursor.fetchone()
            preprocessed_query = data_jamu['PREPRO_METADATA']
            prepro_list1,prepro_metadata=data_preprocessing()
            dokumen_preprocessed = prepro_list1
            dokumen= pd.DataFrame(prepro_metadata)
            model = train_word2vec_model(dokumen_preprocessed)
            bobot_query = extract_query_features(model, preprocessed_query)
            token_dokumen_preprocessed = [dokumen_preprocessed.split() for dokumen_preprocessed in dokumen_preprocessed]
            token_preprocessed_query = preprocessed_query.split()
            all_terms = [term for dokumen_preprocessed in token_dokumen_preprocessed for term in dokumen_preprocessed]
            counter_all_terms = Counter(all_terms)
            default_idf=0
            idf = {term: hitung_idf(term, token_dokumen_preprocessed, default_idf) for term in counter_all_terms}
            tf_preprocessed_query = hitung_tf(token_preprocessed_query)
            tfidf_preprocessed_query = hitung_tfidf(tf_preprocessed_query, idf,default_idf)

            bobot_word2vec = ambil_data_word2vec('','','')
            Word2vec = {**bobot_word2vec, **bobot_query}
            tfidf_dokumen_preprocessed = ambil_data_tfidf('','','')
            print(tfidf_dokumen_preprocessed)
            TFIDF = {**tfidf_dokumen_preprocessed, 'preprocessed_query': tfidf_preprocessed_query}
            result = kombinasiTfidfWord2vec(TFIDF, Word2vec)
            squared_results = {}
            for doc, doc_result in result.items():
                squared_results[doc] = square_values(doc_result)

            
            sum_of_squared_results = {}
            for doc, doc_result in squared_results.items():
                sum_of_squared_results[doc] = sum(doc_result.values())

            
            query_result_multiplied = calculate_query_document_multiplication(result['preprocessed_query'], result)

            sum_per_document = sum_values_per_document(query_result_multiplied)
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

            cosine_similarities_sorted = sorted(cosine_similarities, key=lambda x: x[1], reverse=True)
           
            top_5_results = cosine_similarities_sorted[1:6]
            detailed_results = []
            for result in top_5_results:
                id_jamu = result[0].split('_')[-1]
                jamu_details = dokumen[dokumen['ID_JAMU'] == int(id_jamu)].to_dict(orient='records')[0]
                bobot_word2vec_doc = bobot_word2vec.get(f'vektor_word2vec_dokumen_{id_jamu}', {})
                bobot_tfidf_doc = tfidf_dokumen_preprocessed.get(f'dokumen_preprocessed_{id_jamu}', {})
                detailed_results.append((result[0], result[1], jamu_details, bobot_word2vec_doc,bobot_tfidf_doc))   
            if data_jamu:
                cursor.execute("SELECT komentar.*, user.username FROM komentar JOIN user ON user.id_user = komentar.id_user WHERE ID_JAMU = %s", (id,))
                data_komentar = cursor.fetchall()
                return render_template('detail_jamu1.html', jamu=data_jamu, komentar=data_komentar, top_5_results=detailed_results)
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

@bp.route('/tambah_komentar', methods=['POST'])
def tambah_komentar():
    try:
        if request.method == 'POST':
            if 'username' not in session or 'password' not in session:
                return redirect(url_for('login'))

            username = session['username']
            password = session['password']
            user = current_app.cek_login(username,password)
            if user and user['level_user'] != 'user':
                return "Anda tidak memiliki izin untuk menambah komentar"
            id_user = user['id_user']
            komentar = request.form['komentar']
            id_jamu = request.form['id_jamu']
            tgl_komen = datetime.datetime.now()
            connection = current_app.koneksi()
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                
                if 'id_komentar_balasan' in request.form:
                    id_komentar_balasan = request.form['id_komentar_balasan']
                    cursor.execute("INSERT INTO komentar (id_user, id_jamu, isi_komentar, id_komentar_balasan) VALUES (%s, %s, %s, %s)", (username, id_jamu, komentar, id_komentar_balasan))
                else:
                    username = request.form['username']
                    cursor.execute("INSERT INTO komentar (id_user, id_jamu, isi_komentar) VALUES (%s, %s, %s)", (username, id_jamu, komentar))
                
                connection.commit()
                return redirect(url_for('lihat_detail', id=id_jamu))
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()
            
# Route untuk menampilkan formulir edit data jamu
@bp.route('/edit/<int:id>', methods=['GET'])
def edit_form(id):
    if 'username' not in session or 'password' not in session:
        return redirect(url_for('login'))

    username = session['username']
    password = session['password']
    user =  current_app.cek_login(username,password)
    if user and user['level_user'] != 'user':
        return "Anda tidak memiliki izin untuk menambah data jamu."
    try:
        connection = current_app.koneksi()
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
@bp.route('/edit/<int:id>', methods=['POST'])
def edit_data(id):
    if request.method == 'POST':
        if 'username' not in session or 'password' not in session:
            return redirect(url_for('login'))

        username = session['username']
        password = session['password']
        user = current_app.cek_login(username,password)
        if user and user['level_user'] != 'user':
            return "Anda tidak memiliki izin untuk menambah data jamu."
        
        nama_jamu = request.form['nama_jamu']
        khasiat = request.form['khasiat']
        kandungan = request.form['kandungan']
        aturan_minum = request.form['aturan_minum']
        efek_samping = request.form['efek_samping']
        jenis = request.form['jenis']
        produsen = request.form['produsen']
        lokasi_pemasaran = request.form['lokasi_pemasaran']
        lokasi_produksi = request.form['lokasi_produksi']
        kabupaten = request.form['kabupaten']
        perizinan = request.form['perizinan']

        id_user = user['id_user']



        # preprcessing
        metadata = nama_jamu +' '+ khasiat + ' ' + kandungan
        preprocessed_metadata = preprocess_metadata(metadata)
        
        if 'bukti' not in request.files:
            return "File bukti tidak ditemukan"
        
        bukti = request.files['bukti']
        
        if bukti.filename == '':
            return "Tidak ada file yang dipilih"
        
        if bukti and cek_ekstensi(bukti.filename):
            filename = secure_filename(bukti.filename)
            bukti.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            try:
                connection = current_app.koneksi()
                if connection.is_connected():
                    cursor = connection.cursor()
                    tgl_insert = datetime.datetime.now()
                    cursor.execute("INSERT INTO validasi_update (id_jamu, id_user, bukti_up, tgl_masuk_up, nama_jamu_up, khasiat_up, kandungan_up,aturan_minum_up,efek_samping_up,jenis,produsen_up,lokasi_pemasaran_up,lokasi_produksi_up,kabupaten_up,perizinan_up, METADATA, PREPRO_METADATA) VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s,%s, %s, %s, %s, %s, %s,%s, %s)",
                                   (id, id_user, filename, tgl_insert, nama_jamu, khasiat, kandungan,aturan_minum,efek_samping,jenis,produsen,lokasi_pemasaran,lokasi_produksi,kabupaten,perizinan, metadata, preprocessed_metadata))
                    connection.commit()
            except Exception as e:
                print("Error:", e)
            finally:
                if 'connection' in locals():
                    connection.close()
        else:
            return "Ekstensi file tidak diizinkan"
    return redirect(url_for('home.index'))

# Route untuk menampilkan formulir edit data jamu
@bp.route('/hapus/<int:id>', methods=['GET'])
def hapus_form(id):
    try:
        connection = current_app.koneksi()
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
@bp.route('/hapus/<int:id>', methods=['POST'])
def hapus_jamu(id):
    if request.method == 'POST':
        if 'username' not in session or 'password' not in session:
            return redirect(url_for('login'))

        username = session['username']
        password = session['password']
        user =  current_app.cek_login(username,password)
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
            bukti.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
    try:
        connection = current_app.koneksi()
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