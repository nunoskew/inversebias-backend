FROM python:3.10-slim
RUN mkdir /app 
COPY pyproject.toml /app
WORKDIR /app

# Install cron
RUN apt-get update && apt-get install -y curl

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64 \
SUPERCRONIC=supercronic-linux-amd64 \
SUPERCRONIC_SHA1SUM=cd48d45c4b10f3f0bfdd3a57d054cd05ac96812b

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# You might need to change this depending on where your crontab is located
COPY crontab crontab
COPY . /app
VOLUME /mnt/inversebias_data


