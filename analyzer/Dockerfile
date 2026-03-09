FROM python:3.14-slim
LABEL maintainer="tdezwart@my.bcit.ca"
WORKDIR /app

COPY --from=shared shared_requirements.txt .
RUN pip install --no-cache-dir -r shared_requirements.txt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R nobody:nogroup /app
USER nobody

EXPOSE 8110

ENTRYPOINT ["python"]
CMD ["app.py"]