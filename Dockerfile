FROM python:3.11-slim

# Dependências de sistema para PyMySQL e cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Desenvolvimento: Flask dev server
# Produção: substituído pelo CMD do docker-compose.prod.yml
CMD ["python", "run.py"]
