# Базовий образ Python
FROM python:3.11-slim

# Метадані
LABEL author="Баранова Анастасія, група АІ-231"
LABEL description="Лабораторна робота №4 — Docker"

# Системні залежності
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Змінні середовища
ENV MODE=comfort
ENV POPULATION_SIZE=100
ENV MAX_ITERATIONS=1000
ENV MUTATION_RATE=0.1
ENV APP_MODE=production
ENV PORT=5000
ENV HOST=0.0.0.0

VOLUME ["/app/output"]
EXPOSE 5000

CMD ["python", "main.py"]
