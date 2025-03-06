FROM python:3.10-slim
RUN mkdir /app 
COPY pyproject.toml /app
WORKDIR /app

# Install cron
RUN apt-get update && apt-get -y install cron

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

COPY . /app
VOLUME /mnt/inversebias_data

# Create crontab file
RUN echo "0 */4 * * * cd /app && /usr/local/bin/poetry run python -m inversebias.pipeline && /usr/local/bin/poetry run python -m inversebias.data.storage --upload && /usr/local/bin/poetry run python -m inversebias.data.storage --download >> /var/log/cron.log 2>&1" > /etc/cron.d/inversebias-cron && \
    chmod 0644 /etc/cron.d/inversebias-cron && \
    crontab /etc/cron.d/inversebias-cron && \
    touch /var/log/cron.log

# Create startup script that passes environment variables to cron
RUN echo '#!/bin/bash\nprintenv > /etc/environment\ncron\npoetry run python -m inversebias.api' > /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]