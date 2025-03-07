FROM python:3.10-slim
RUN mkdir /app 
COPY pyproject.toml /app
WORKDIR /app

# Install cron
RUN apt-get update 

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

COPY . /app
VOLUME /mnt/inversebias_data


ENTRYPOINT ["poetry", "run", "python", "-m", "inversebias.api"]