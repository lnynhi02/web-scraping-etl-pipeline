from utils import clean_title, clean_salary, transform_salary, caculate_dates

from airflow.exceptions import AirflowSkipException
from playwright.sync_api import sync_playwright
from psycopg2.extras import DictCursor
from pyvirtualdisplay import Display
from datetime import datetime
import configparser
import psycopg2
import pendulum
import logging
import time
import json
import os

logging.basicConfig(level=logging.INFO)

LAST_PROCESSED_FILE = os.path.join(os.path.dirname(__file__), '..', 'tmp', 'last_processed_time.json')

def read_last_processed_time():
    try:
        with open(LAST_PROCESSED_FILE, "r") as file:
            return datetime.fromisoformat(json.load(file)['last_processed'])
    except Exception as e:
        logging.error(f"Error reading last processed time from file: {e} -> So we will return None")
        return None

def write_last_processed_time(last_processed):
    try:
        with open(LAST_PROCESSED_FILE, "w") as file:
            json.dump({'last_processed': last_processed.isoformat()}, file)
    except Exception as e:
        logging.error(f"Error writing last processed time to file: {e}")

def get_connection():
    config_file = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_file)

    try:
        return psycopg2.connect(
            host=config['postgres']['host'],
            port=config['postgres']['port'],
            dbname=config['postgres']['database'],
            user=config['postgres']['user'],
            password=config['postgres']['password']
        )
    except Exception as e:
        logging.error(f"Error creating connection to Postgres: {e}")

def scrape_data(**kwargs):
    url = kwargs['url']

    display = Display(visible=0, size=(1920, 1080))
    display.start()

    scraped_jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto(url)
            time.sleep(3)

            jobs = page.query_selector_all("div.job-item-2.job-item-default.bg-highlight.job-ta")
            for job in jobs:
                title = job.query_selector("h3.title").inner_text().strip()
                link = job.query_selector("a").get_attribute("href")
                salary = job.query_selector("label.title-salary").inner_text().strip()
                company = job.query_selector("a.company").inner_text().strip()
                update = job.query_selector("label.deadline").inner_text().strip()
                location = job.query_selector("label.address").inner_text().strip()
                deadline = job.query_selector("label.time").inner_text().strip()

                posted_date, due_date = caculate_dates(update, deadline)
                scraped_jobs.append({
                    'job_name': title,
                    'job_link': link,
                    'salary': salary,
                    'company_name': company,
                    'update': update,
                    'posted_date': posted_date,
                    'job_location': location,
                    'remaining_time': deadline,
                    'due_date': due_date
                })
            
            browser.close()

        write_to_staging_table(scraped_jobs)

    except Exception as e:
        logging.error(f"Error scraping data: {e}")

    finally:
        display.stop()

def write_to_staging_table(scraped_jobs):
    # Write to Staging Table: Keeping a copy of the original data for recovery purposes
    conn = get_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    try:
        for job in scraped_jobs:
            cur.execute("""INSERT INTO staging_table VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
            (job['job_name'], job['job_link'], job['salary'], job['company_name'], job['update'], job['update_date'], job['job_location'], job['remaining_time'], job['due_date']))
    except Exception as e:
        logging.error(f"Error writing data to staging table: {e}")
    finally:
        conn.commit()
        cur.close()
        conn.close()

def clean_data(**kwargs):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Filter New Jobs: Select only jobs with update_date greater than last_processed_time
    query = "SELECT * FROM staging_table"
    last_processed_time = read_last_processed_time()

    if last_processed_time:
        query += " WHERE update_date > %s"
        cur.execute(query, (last_processed_time,))
    elif last_processed_time is None:
        cur.execute(query)

    # Using Pendulum for timezone management before pushing to XCom
    scraped_jobs = cur.fetchall()
    cleaned_jobs = []
    for job in scraped_jobs:        
        cleaned_jobs.append({
            'job_name': clean_title(job['job_name']),
            'job_link': job['job_link'],
            'salary': clean_salary(job['salary']),
            'company_name': job['company_name'],
            'posted_date': pendulum.instance(job['posted_date']).in_timezone('Asia/Ho_Chi_Minh'),
            'job_location': job['job_location'],
            'remaining_time': job['remaining_time'],
            'due_date': pendulum.instance(job['due_date']).in_timezone('Asia/Ho_Chi_Minh')
        })

        logging.info(f"Job '{job['job_name']}' has update time: {job['posted_date']}")

    logging.info(f"Cleaned {len(cleaned_jobs)} job(s)")

    conn.commit()
    cur.close()
    conn.close()

    kwargs['ti'].xcom_push(key='cleaned_data', value=cleaned_jobs)

def transform_data(**kwargs):
    cleaned_jobs = kwargs['ti'].xcom_pull(key='cleaned_data', task_ids='clean_data_task')

    transformed_jobs = []
    for job in cleaned_jobs:
        transformed_jobs.append({
            'job_name': job['job_name'],
            'job_link': job['job_link'],
            'salary': transform_salary(job['salary']),
            'company_name': job['company_name'],
            'posted_date': pendulum.instance(job['posted_date']).in_timezone('Asia/Ho_Chi_Minh'),
            'job_location': job['job_location'],
            'remaining_time': job['remaining_time'],
            'due_date': pendulum.instance(job['due_date']).in_timezone('Asia/Ho_Chi_Minh')
        })

    logging.info(f"Transformed {len(transformed_jobs)} job(s)")

    kwargs['ti'].xcom_push(key='transformed_data', value=transformed_jobs)

def write_sql_query(**kwargs):
    transformed_jobs = kwargs['ti'].xcom_pull(key='transformed_data', task_ids='transform_data_task')
    postgres_sql_file = os.path.join(os.path.dirname(__file__), '..', 'tmp', 'postgres_query.sql')

    try:
        with open(postgres_sql_file, "w") as file:
            if not transformed_jobs:
                logging.info("There are no available jobs to write")
            else:
                last_processed = transformed_jobs[0]['update']
                for job in transformed_jobs:
                    file.write(
                        f"INSERT INTO jobs_table VALUES ("
                        f"'{job['job_name']}', "
                        f"'{job['job_link']}', "
                        f"'{job['salary']}', "
                        f"'{job['company_name']}', "
                        f"'{job['posted_date']}', "
                        f"'{job['job_location']}', "
                        f"'{job['remaining_time']}', "
                        f"'{job['due_date']}');\n"
                    )
                    if job['posted_date'] > last_processed:
                        last_processed = job['posted_date']

                logging.info(f"Wrote {len(transformed_jobs)} jobs to the SQL file")
                write_last_processed_time(last_processed)
                logging.info("Successfully update the last processed time")
    except Exception as e: 
        logging.error(f"Error writing SQL query to file{e}")

def check_sql_file(**kwargs):
    postgres_sql_file = os.path.join(os.path.dirname(__file__), '..', 'tmp', 'postgres_query.sql')

    if os.path.exists(postgres_sql_file) and os.path.getsize(postgres_sql_file) > 0:
        logging.info("SQL file is not empty. Start to write to Postgres database")
    else:
        logging.info("No SQL queries to execute.")
        raise AirflowSkipException("Skipping task because SQL file is empty")