FROM python:3.14-slim
LABEL maintainer="tdezwart@my.bcit.ca"
WORKDIR /app

COPY --from=shared shared_requirements.txt .
RUN pip install --no-cache-dir -r shared_requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R nobody:nogroup /app
USER nobody

EXPOSE 8090

ENTRYPOINT ["python"]
CMD ["app.py"]