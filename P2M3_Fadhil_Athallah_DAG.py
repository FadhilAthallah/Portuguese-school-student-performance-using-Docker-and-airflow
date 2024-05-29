from airflow.models import DAG
from airflow.operators.python import PythonOperator
#from airflow.providers.postgres.operators.postgres import PostgresOperator
# from airflow.utils.task_group import TaskGroup
from datetime import datetime
from sqlalchemy import create_engine #koneksi ke postgres
import pandas as pd

from elasticsearch import Elasticsearch
# from elasticsearch.helpers import bulk

def load_csv_to_postgres():
 
    database = "airflow_m3"
    username = "airflow_m3"
    password = "airflow_m3"
    host = "postgres"

    # Membuat URL koneksi PostgreSQL
    postgres_url = f"postgresql+psycopg2://{username}:{password}@{host}/{database}"

    # Gunakan URL ini saat membuat koneksi SQLAlchemy
    engine = create_engine(postgres_url)
    # engine= create_engine("postgresql+psycopg2://airflow:airflow@postgres/airflow")
    conn = engine.connect()

    df = pd.read_csv('/opt/airflow/dags/P2M3_Fadhil_Athallah.csv')
    #df.to_sql(nama_table_db, conn, index=False, if_exists='replace')
    df.to_sql('table_testing', conn, index=False, if_exists='replace')  
    

def ambil_data():
    '''
    Fungsi ini digunakan untuk mengambil data csv dari postgre
    '''
    
    database = "airflow_m3"
    username = "airflow_m3"
    password = "airflow_m3"
    host = "postgres"

    # Membuat URL koneksi PostgreSQL
    postgres_url = f"postgresql+psycopg2://{username}:{password}@{host}/{database}"

    # Gunakan URL ini saat membuat koneksi SQLAlchemy
    engine = create_engine(postgres_url)
    conn = engine.connect()

    df = pd.read_sql_query("select * from table_testing", conn) #nama table sesuaikan sama nama table di postgres
    df.to_csv('/opt/airflow/dags/P2M3_Fadhil_Athallah_new.csv', sep=',', index=False)
    


def preprocessing(): 
    ''' 
    fungsi untuk membersihkan data, proses pembersihana sendiri meliputi penghapsan duplikat, pengisian nilai null, dan pengubahan nama kolom
    
    '''
    # pembisihan data
    data = pd.read_csv("/opt/airflow/dags/P2M3_Fadhil_Athallah_new.csv")

    # bersihkan data 
    data.drop_duplicates(inplace=True)

    # Fungsi untuk normalisasi nama kolom
    def normalize_column_name(col_name):
        '''
        fungsi normalisasi nama kolom dengan mengecilkan, mengganti dan meghapus huruf atau simbol yang tidak dibutuhkan
        '''
        col_name = col_name.lower()  # Mengubah menjadi lowercase
        col_name = col_name.replace(' ', '_')  # Mengganti spasi dengan underscore
        col_name = col_name.replace('|', '')  # Menghapus simbol yang tidak diperlukan
        col_name = col_name.strip()  # Menghapus spasi/tab di awal dan akhir
        return col_name

    # Normalisasi semua nama kolom
    data.columns = [normalize_column_name(col) for col in data.columns]
    # data= data.query('age>=0')
    data.to_csv('/opt/airflow/dags/P2M3_Fadhil_Athallah_clean.csv', index=False)
    
    for col in data.columns:
        if data[col].dtype == 'float64' or data[col].dtype == 'int64':
            data[col].fillna(data[col].mean(), inplace=True)  # Mengisi nilai hilang dengan rata-rata kolom
        else:
            data[col].fillna(data[col].mode()[0], inplace=True)  # Mengisi nilai hilang dengan modus (nilai yang paling sering muncul)
    
    data.to_csv('/opt/airflow/dags/P2M3_Fadhil_Athallah_clean.csv', sep=',', index=False)


def upload_to_elasticsearch():
    '''
    Mengupload data yang sudah dipreproses kedalam elasticsearch
    '''

    es = Elasticsearch("http://elasticsearch:9200")
    df = pd.read_csv('/opt/airflow/dags/P2M3_Fadhil_Athallah_clean.csv')
    
    for i, r in df.iterrows():
        doc = r.to_dict()  # Convert the row to a dictionary
        res = es.index(index="table_m3", id=i+1, body=doc)
        print(f"Response from Elasticsearch: {res}")
        

        
default_args = {
    'owner': 'Fadhil', 
    'start_date': datetime(2023, 12, 24, 12, 00)
}

with DAG(
    "P2M3_Fadhil_DAG_hck", #atur sesuai nama project kalian
    description='Milestone_3',
    schedule_interval='30 6 * * *', #atur schedule untuk menjalankan airflow pada 06:30.
    default_args=default_args, 
    catchup=False
) as dag:

    # Task : 1
    load_csv_task = PythonOperator(
        task_id='load_csv_to_postgres',
        python_callable=load_csv_to_postgres) #sesuaikan dengan nama fungsi yang kalian buat
    
    #task: 2
    ambil_data_pg = PythonOperator(
        task_id='ambil_data_postgres',
        python_callable=ambil_data)
    

    # Task: 3
    '''  Fungsi ini ditujukan untuk menjalankan pembersihan data.'''
    edit_data = PythonOperator(
        task_id='edit_data',
        python_callable=preprocessing)

    # Task: 4
    upload_data = PythonOperator(
        task_id='upload_data_elastic',
        python_callable=upload_to_elasticsearch)

    # proses untuk menjalankan di airflow
    load_csv_task >> ambil_data_pg >> edit_data  >> upload_data
    


