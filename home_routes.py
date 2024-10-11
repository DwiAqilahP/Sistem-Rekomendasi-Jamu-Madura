import pandas as pd
from flask import Blueprint,current_app, render_template, request, session
import datetime
import re  
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

bp= Blueprint('home', __name__)

def data_preprocessing():
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM jamu"
            cursor.execute(query)
            prepro_metadata = cursor.fetchall()
            
            # Menghapus spasi berlebihan dan menggunakan koma sebagai pemisah
            prepro_list1 = [' '.join(doc['PREPRO_METADATA'].split()) for doc in prepro_metadata]
            return prepro_list1,prepro_metadata
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

def ambil_data_word2vec(kabupaten_filters, jenis_filters, perizinan_filters):
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            word2vec_dict = {}
            where_conditions = []
            if kabupaten_filters:
                kabupaten_values = ",".join([f"'{value}'" for value in kabupaten_filters])
                where_conditions.append(f"(kabupaten IN ({kabupaten_values}))")

            if jenis_filters:
                jenis_values = ",".join([f"'{value}'" for value in jenis_filters])
                where_conditions.append(f"(jenis IN ({jenis_values}))")

            if perizinan_filters:
                perizinan_values = ",".join([f"'{value}'" for value in perizinan_filters])
                where_conditions.append(f"(perizinan IN ({perizinan_values}))")

            where_clause_str = " AND ".join(where_conditions)
            
            query = "SELECT word2vec.id_jamu, bobot FROM word2vec JOIN jamu ON word2vec.id_jamu = jamu.id_jamu"
            if where_clause_str:
                query += f" WHERE {where_clause_str};"
            else:
                query += ";"
            
            cursor.execute(query)
            word2vec_results = cursor.fetchall()
            
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
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            word2vec_dict = {}
            where_conditions = []
            if kabupaten_filters:
                kabupaten_values = ",".join([f"'{value}'" for value in kabupaten_filters])
                where_conditions.append(f"(kabupaten IN ({kabupaten_values}))")

            if jenis_filters:
                jenis_values = ",".join([f"'{value}'" for value in jenis_filters])
                where_conditions.append(f"(jenis IN ({jenis_values}))")

            if perizinan_filters:
                perizinan_values = ",".join([f"'{value}'" for value in perizinan_filters])
                where_conditions.append(f"(perizinan IN ({perizinan_values}))")

            # Gabungkan semua kondisi dengan klausa "AND"
            where_clause_str = " AND ".join(where_conditions)
            
            query = "SELECT tfidf.id_jamu, term, bobot FROM tfidf JOIN jamu ON tfidf.id_jamu = jamu.id_jamu"
            if where_clause_str:
                query += f" WHERE {where_clause_str};"
            else:
                query += ";"
            
            cursor.execute(query)
            word2vec_results = cursor.fetchall()
            
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

def preprocessing(text):
    # Case folding
    text = text.lower()
    # Hapus angka
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'\W+', ' ', text)

    # Tokenization
    tokens = word_tokenize(text)

    # Stopword removal
    stop_re = set(stopwords.words('indonesian'))
    stop_word = [token for token in tokens if token not in stop_re]

    # Stemming
    stemm = StemmerFactory().create_stemmer()
    stemming_token = [stemm.stem(token) for token in stop_word]
    cleaned_text = ' '.join(stemming_token)  
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

    return cleaned_text.strip()

def preprocess_query(query):
    preprocessed_tokens = preprocessing(query)
    return preprocessed_tokens

def preprocess_metadata(metadata):
    preprocessed_tokens = preprocessing(metadata)
    return preprocessed_tokens

def train_word2vec_model(dokumen):
    token_dokumen = [word_tokenize(doc.lower()) for doc in dokumen]
    model = Word2Vec(sentences=token_dokumen, vector_size=100, window=15, min_count=1, sg=1)
    return model

# Ekstraksi fitur word2vec untuk dokumen
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

# Ekstraksi fitur word2vec untuk query
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
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor()

            cursor.execute("DELETE FROM word2vec")
            cursor.execute("ALTER TABLE word2vec AUTO_INCREMENT = 1")
            cursor.execute("DELETE FROM tfidf")
            cursor.execute("ALTER TABLE tfidf AUTO_INCREMENT = 1")

            prepro_list1,prepro_metadata=data_preprocessing()
            dokumen_preprocessed = prepro_list1

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

            model = train_word2vec_model(dokumen_preprocessed)

            fitur_dokumen = extract_document_features(model, dokumen_preprocessed)

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
            tfidf[term] = round(tf * default_idf, 6)
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
    # print('dict1=',dict1)
    # print("dict2=",dict2)
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
            multiplied_dict[key] = 0 
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
    return sum_per_document

def ambil_data_filter():
    try:
        connection = current_app.koneksi()
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("SELECT DISTINCT kabupaten FROM jamu WHERE kabupaten IS NOT NULL AND kabupaten != ''")
            kabupaten = cursor.fetchall()
            # print("Kabupaten:", kabupaten)  

            cursor.execute("SELECT DISTINCT jenis FROM jamu WHERE jenis IS NOT NULL AND jenis != ''")
            jenis = cursor.fetchall()
            # print("Jenis:", jenis)

            cursor.execute("SELECT DISTINCT perizinan FROM jamu WHERE perizinan IS NOT NULL AND perizinan != ''")
            perizinan = cursor.fetchall()
            # print("Perizinan:", perizinan)  

            return kabupaten, jenis, perizinan
    except Exception as e:
        print("Error:", e)
    finally:
        if 'connection' in locals():
            connection.close()

@bp.route("/",methods=["GET", "POST"])
def index():
    if request.method == 'POST':
        cari = request.form['searchInput']
        if cari:
            session['cari'] = cari
        else:
            session.pop('cari', None)
        kabupaten_filters = request.form.getlist('kabupaten')
        jenis_filters = request.form.getlist('jenis')
        perizinan_filters = request.form.getlist('perizinan')

        preprocessed_query = preprocess_query(cari)
        # print(preprocessed_query)
        # prepro_list, data_jamu = ambil_dokumen_prepro(kabupaten_filters, jenis_filters, perizinan_filters)
        # dokumen_preprocessed = prepro_list
        # dokumen_preprocessed = '\n'.join(dokumen_preprocessed)
        # dokumen= pd.DataFrame(data_jamu)
        prepro_list1,prepro_metadata=data_preprocessing()
        dokumen_preprocessed = prepro_list1
        dokumen= pd.DataFrame(prepro_metadata)

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
        # print(tfidf_dokumen_preprocessed)
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

        # Menjumlahkan hasil perkalian menjadi perdokumen
        sum_per_document = sum_values_per_document(query_result_multiplied)

        # print("Jumlah hasil perkalian menjadi perdokumen:")
        # for doc_name, doc_result in sum_per_document.items():
        #     print(f"Dokumen {doc_name}: {doc_result}")

        # print("Hasil perhitungan cosine similarity untuk setiap dokumen:")
        cosine_similarities = []

        # Iterasi melalui hasil perkalian query dengan setiap dokumen
        for doc_name, doc_result in query_result_multiplied.items():
            if doc_name != 'preprocessed_query':
                # Mengambil nilai total hasil perkalian query dengan dokumen dari dictionary sum_per_document
                totalQxD = sum_per_document[doc_name]
                # Menghitung penyebut cosine similarity
                sqrtQD = math.sqrt(sum_of_squared_results['preprocessed_query'] * sum_of_squared_results[doc_name])
                result = totalQxD / sqrtQD if sqrtQD != 0 else 0
                # Menambahkan hasil cosine similarity ke dalam list
                cosine_similarities.append((doc_name, result))

        cosine_similarities_sorted = sorted(cosine_similarities, key=lambda x: x[1], reverse=True)

        top_5_results = cosine_similarities_sorted[:5]

        detailed_results = []
        for result in top_5_results :
            id_jamu = result[0].split('_')[-1]
            jamu_details = dokumen[dokumen['ID_JAMU'] == int(id_jamu)].to_dict(orient='records')[0]
            bobot_word2vec_doc = bobot_word2vec.get(f'vektor_word2vec_dokumen_{id_jamu}', {})
            bobot_tfidf_doc = tfidf_dokumen_preprocessed.get(f'dokumen_preprocessed_{id_jamu}', {})
            detailed_results.append((result[0], result[1], jamu_details, bobot_word2vec_doc,bobot_tfidf_doc))
        return render_template('hasil_pencarian.html',idf=idf,bobot_query=bobot_query,tfidf_preprocessed_query=tfidf_preprocessed_query, cari=cari, preprocessed_query=preprocessed_query, top_5_results=detailed_results)
    else:
        kabupaten, jenis, perizinan = ambil_data_filter()
    return render_template('index.html',kabupaten=kabupaten, jenis=jenis, perizinan=perizinan)
