# On part de l’image officielle AMC pour avoir la CLI prête
FROM ghcr.io/auto-multiple-choice/auto-multiple-choice:latest

# Python + dépendances
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip \
 && pip3 install --no-cache-dir fastapi uvicorn python-multipart pydantic[dotenv] stripe

WORKDIR /app
COPY requirements.txt /app/requirements.txt
# Si tu as des libs en plus dans requirements.txt, elles seront installées
RUN pip3 install --no-cache-dir -r /app/requirements.txt || true

COPY app.py /app/app.py

ENV AMC_DATA_DIR=/amc/data \
    PYTHONUNBUFFERED=1

RUN mkdir -p /amc/data
EXPOSE 8000
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
