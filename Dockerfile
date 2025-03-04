FROM python:3.10-slim
RUN mkdir /app 
COPY pyproject.toml /app
WORKDIR /app
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev
COPY . /app
VOLUME /mnt/inversebias_data

CMD ["poetry","run","python", "-m", "inversebias.api"]