FROM apache/airflow:2.8.0

ENV AIRFLOW_HOME=/opt/airflow
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow"
WORKDIR $AIRFLOW_HOME

COPY ../requirements.txt /opt/airflow/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

USER root
RUN apt-get update --fix-missing && \
    apt-get install -y \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxcb1 libxkbcommon0 \
    libatspi2.0-0 libx11-6 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 xvfb x11-utils nano \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install pyvirtualdisplay playwright
RUN playwright install chromium