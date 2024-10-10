# 💼 JobScraper: Automated Job Data Pipeline

JobScraper is a web scraping and data pipeline project designed to automatically extract job postings from the TOPCV website(a website that posts job listings in Vietnam). The extracted data is cleaned, transformed, and stored in a structured database for easy querying and analysis. This project provides insights into the current job market and can be extended for data visualization and reporting purposes.

## Overview
Let's break down the ETL process step-by-step:

1. **Data Scraping**: Initially, data is collected from the [TOPCV](https://www.topcv.vn/viec-lam-it) website
2. **Data Processing**: After gathering the data, it undergoes a thorough cleaning and transformation process before being stored in the PostgreSQL database.
3. **Scheduling with Airflow**: All tasks—ranging from data scraping and cleaning to transformation and storage in the PostgreSQL database—are seamlessly orchestrated using Airflow, ensuring efficient workflow management.

<p align="center">
    <img width=80% height=80% src="assets/pipeline.gif" />

## Achievements
- Stored new jobs daily in the PostgreSQL database to keep an updated repository.
- Clean the 'title' and 'salary' columns to enhance query performance and ensure accurate data retrieval.
- Create a 'deadline_date' column to facilitate easy tracking of job deadlines.
- Utilize a stored procedure to update the 'deadline' column daily, for example, changing 'Còn 24 ngày để ứng tuyển' to 'Còn 23 ngày để ứng tuyển' the following day.

## ⚙️ Local Setup
### Prerequisites
- Install [Docker](https://www.docker.com/products/docker-desktop/) for running Airflow
- Install [Python](https://www.python.org/)
- Install [PostgreSQL](https://www.postgresql.org/download/)

You can clone, fork, or download this GitHub repository on your local machine using the following command:
** **
        git clone https://github.com/lnynhi02/web-scraping-etl-pipeline.git

**Here is the overall structure of the project:**
** **
        web-scraping-etl-pipeline/
        ├── airflow/
        │   ├── dags/
        │   │   └── topcv_flow.py
        │   └── Dockerfile
        ├── config/
        │   └── config.ini
        ├── pipelines/
        │   ├── create_table.py
        │   ├── topcv_pipeline.py
        │   └── utils.py
        ├── tmp/
        │   ├── last_processed_time.json
        │   └── postgres_query.sql
        ├── .env
        ├── docker-compose.yaml
        └── requirements.txt

## 💻 Deployment
### **```Postgres Setup```**
Before setting-up our airflow configurations, let’s create the Postgres database that will persist our data. I prefer using the **pgAdmin 4** tool for this, however any other Postgres development platform can do the job.

When installing postgres, you need to setup a password that we will need later to connect to the database from the Spark environment. **You must remember the password to reconnect to the database servers**. You can also leave the port at 5432. If your installation has succeeded, you can start pgadmin and you should observe something like this window:
<p align="center">
  <img width=80% height=80%" src="https://www.w3schools.com/postgresql/screenshot_postgresql_pgadmin4_4.png">

Since we have many columns for the table we want to create, we opted to use a script with **psycopg2**, a PostgreSQL database adapter for Python, to create the table and add its columns. And we have installed the **psycopg2-binary** package in the `requirements.txt`

You can run the Python script with the following command:
** ** 
        python pipelines/create_table.py

I use `config.ini` to access the database configurations, allowing you to modify the application settings easily. Alternatively, if you prefer to use a different method, you can make slight adjustments to the script accordingly. The `config.ini` file looks as follow:
** **
    [database]
    host=change_me
    port=5432
    user=postgres
    password=change_me
    database=change_me

### **```Airflow Setup```**
Let’s take a look at the Directed Acyclic Graph (DAG) that will outline the sequence and dependencies of tasks, enabling Airflow to manage their execution.
** ** 
        from airflow.providers.postgres.operators.postgres import PostgresOperator
        from airflow.operators.python import PythonOperator
        from airflow import DAG
        import airflow.utils.dates
        import logging
        import sys
        import os

        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pipelines'))
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

- The dag includes all the tasks that are imported from the ``topcv_pipeline.py``
- The tasks are set to execute daily.
- The first task is the **Scrape Data Task**. This task scrapes data from the *TOPCV* website into a staging table in Postgres database, initiating the data processing workflow.
- The second task, **Clean Data Task**, will retrieve new, unprocessed jobs from the staging table, clean the 'title' and 'salary' fields by using ``clean_title()`` and ``clean_salary()`` function from ``utils.py``, and then push the cleaned data into XCom for later transformation.
- The third task is the **Transform Data Task**, which pulls cleaned data from XCom, uses the ``transform_salary()`` from ``utils.py`` to calculate the average salary, and then pushes the results back to XCom.
- The fourth task, **Write SQL Query Task**, pulls transformed data from XCom and then generates INSERT SQL commands for each job, saving them to ``postgres_query.sql`` for use with the ``PostgresOperator`` in downstream task.
- The fifth task, **Check SQL File Task**, checks whether the ``postgres_query.sql`` file contains any SQL commands. If it does, the downstream tasks will be executed; if the file is empty, the downstream tasks will be skipped.
- The final task is the **Write To Postgres Task**. It uses the **PostgresOperator** for execution, running the SQL commands from the ``postgres_query.sql`` file and storing the jobs in the PostgreSQL database.

Now, we just need to run Airflow in Docker. However, we need to create some environment variables that will be used by docker-compose.
- Linux:
** **
        echo -e "AIRFLOW_UID=$(id -u)" > .env

- Windows, you need to find the UID by the command ``whoami /user``. Next, you take the 4 numbers at the end and run the following command:
** ** 
        Set-Content -Path .env -Value "AIRFLOW_UID=xxxx"

- Finally, create the network with ``docker network create airflow`` and start Airflow in Docker by running ``docker-compose up -d``.

Now you can access the Airflow UI at ``localhost:8080``. Use the username ``airflow`` and the password ``airflow`` to log in, and you can activate the DAG now. You can check the log of each task to see what is going on.

