import psycopg2
import logging
import configparser

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read("config/config.ini")

HOST=config['postgres']['host']
PORT=config['postgres']['port']
DB=config['postgres']['database']
USER=config['postgres']['user']
PWD=config['postgres']['password']

def get_connection():
    try:
        return psycopg2.connect(
            host='localhost',
            port=PORT,
            dbname=DB,
            user=USER,
            password=PWD
        )
        
    except:
        return psycopg2.connect(
            host=HOST,
            port=PORT,
            dbname=DB,
            user=USER,
            password=PWD
        )

def execute_sql(sql_query):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(sql_query)
        conn.commit()
        logging.info("Create table successfully!")
    except Exception as e:
        logging.error(f"Error creating table: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def create_table():
    sql_query_staging_table = '''
        CREATE TABLE IF NOT EXISTS staging_table(
            job_name TEXT,
            job_link TEXT,
            salary TEXT,
            company_name TEXT,
            update TEXT,
            update_date TIMESTAMP WITH TIME ZONE,
            job_location VARCHAR(30),
            remaining_time TEXT,
            due_date TIMESTAMP WITH TIME ZONE
        )
    '''

    sql_query_jobs_table = '''
        CREATE TABLE IF NOT EXISTS jobs_table(
            job_name TEXT,
            job_link TEXT,
            salary TEXT,
            company_name TEXT,
            posted_date TIMESTAMP WITH TIME ZONE,
            job_location VARCHAR(30),
            remaining_time TEXT,
            due_date TIMESTAMP WITH TIME ZONE
        )
    '''

    execute_sql(sql_query_staging_table)
    execute_sql(sql_query_jobs_table)

if __name__ == '__main__':
    create_table()
