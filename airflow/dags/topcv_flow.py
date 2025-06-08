from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from airflow import DAG
import airflow.utils.dates
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from topcv_pipeline import scrape_data, clean_data, transform_data, write_sql_query, check_sql_file

logging.basicConfig(level=logging.INFO)
TEMPLATE_SEARCH_PATH = os.path.join(os.path.dirname(__file__), '..', 'tmp')

default_args = {
    'owner': 'airflow',
    'start_date': airflow.utils.dates.days_ago(1)
}

with DAG(
    'job_scraper',
    default_args=default_args,
    template_searchpath=TEMPLATE_SEARCH_PATH,
    schedule_interval='@daily',
    catchup=False
) as dag:
    scrape_data_task = PythonOperator(
        task_id='scrape_data_task',
        python_callable=scrape_data,
        provide_context=True,
        op_kwargs={'url': 'https://www.topcv.vn/viec-lam-it'},
    )

    clean_data_task = PythonOperator(
        task_id='clean_data_task',
        python_callable=clean_data,
        provide_context=True
    )

    transform_data_task = PythonOperator(
        task_id='transform_data_task',
        python_callable=transform_data,
        provide_context=True
    )

    write_sql_query_task = PythonOperator(
        task_id='write_sql_query_task',
        python_callable=write_sql_query,
        provide_context=True
    )

    check_sql_file_task = PythonOperator(
        task_id='check_sql_file_task',
        python_callable=check_sql_file,
        provide_context=True
    )

    write_to_postgres_task = PostgresOperator(
        task_id='write_to_postgres_task',
        postgres_conn_id='postgres_conn',
        sql='postgres_query.sql',
        trigger_rule='all_success'
    )

scrape_data_task >> clean_data_task >> transform_data_task >> write_sql_query_task >> check_sql_file_task >> write_to_postgres_task
