FROM python:3.14-slim
LABEL maintainer="tdezwart@my.bcit.ca"

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -r -g ${GROUP_ID} appgroup && \
    useradd -r -m -l -u ${USER_ID} -g appgroup appuser

WORKDIR /app
RUN chown appuser:appgroup /app

COPY --chown=appuser:appgroup --from=shared shared_requirements.txt .
RUN pip install --no-cache-dir -r shared_requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=appuser:appgroup requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup . .

EXPOSE 8090

USER appuser
ENTRYPOINT ["python"]
CMD ["app.py"]