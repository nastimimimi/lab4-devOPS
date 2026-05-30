"""
Веб-інтерфейс для генетичного алгоритму розкладу
Flask-сервер — демонстрація портів та мережі у Docker

Лабораторна робота №4: Docker та Linux CLI
Автор: Баранова Анастасія, група АІ-231
"""

from flask import Flask, jsonify
import os
import threading
import json
from datetime import datetime

app = Flask(__name__)

# Підключення до Redis (якщо доступний)
redis_client = None
try:
    import redis
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True,
        socket_connect_timeout=2
    )
    redis_client.ping()
    print(f" Redis підключено: {redis_host}:{redis_port}")
except Exception as e:
    print(f"  Redis недоступний, працюємо без кешу: {e}")
    redis_client = None

_local_store = {
    "status":  "idle",
    "message": "Сервер запущено. Надішліть POST /run для старту."
}

def get_state():
    if redis_client:
        try:
            data = redis_client.get("schedule_result")
            return json.loads(data) if data else _local_store
        except Exception:
            pass
    return _local_store

def set_state(data):
    global _local_store
    _local_store = data
    if redis_client:
        try:
            redis_client.set("schedule_result", json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

# Зчитуємо режим із змінної середовища
MODE = os.environ.get("MODE", "comfort")
MODE_PARAMS = {
    "comfort": {"pop_size": 100, "max_iter": 1000, "mutation": 0.1},
    "eco":     {"pop_size": 50,  "max_iter": 300,  "mutation": 0.2},
}
params = MODE_PARAMS.get(MODE, MODE_PARAMS["comfort"])


@app.route("/")
def index():
    return jsonify({
        "app":    "Генетичний алгоритм — Автоматизоване складання розкладу занять",
        "author": "Баранова Анастасія, група АІ-231",
        "mode":   MODE,
        "params": params,
        "redis":  "підключено" if redis_client else "не підключено",
        "endpoints": {
            "GET  /":       "Інформація про сервер",
            "GET  /health": "Перевірка роботи сервера",
            "GET  /status": "Статус останнього запуску",
            "POST /run":    "Запустити оптимізацію",
            "GET  /result": "Отримати результат",
        },
        "env": {
            "MODE":     os.environ.get("MODE", "comfort"),
            "PORT":     os.environ.get("PORT", "5000"),
            "APP_MODE": os.environ.get("APP_MODE", "production"),
            "REDIS_HOST": os.environ.get("REDIS_HOST", "localhost"),
        }
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "time":   datetime.now().isoformat(),
        "mode":   MODE,
        "redis":  "ok" if redis_client else "unavailable",
    })


@app.route("/status")
def status():
    return jsonify(get_state())


@app.route("/run", methods=["POST"])
def run_optimization():
    set_state({"status": "running", "message": "Оптимізацію запущено..."})

    def background_task():
        try:
            import sys
            sys.path.insert(0, "/app")
            from main import InputData, GeneticScheduler

            data      = InputData()
            scheduler = GeneticScheduler(data)

            # Застосовуємо параметри поточного режиму
            scheduler.pop_size        = params["pop_size"]
            scheduler.max_generations = params["max_iter"]
            scheduler.mutation_prob   = params["mutation"]

            result = scheduler.run()

            set_state({
                "status":      "done",
                "mode":        MODE,
                "conflicts":   scheduler._count_conflicts(result),
                "gaps":        scheduler._count_gaps(result),
                "generations": len(scheduler.log),
                "best_score":  float(scheduler._fitness(result)),
                "pop_size":    scheduler.pop_size,
                "time":        datetime.now().isoformat(),
            })
        except Exception as e:
            set_state({"status": "error", "message": str(e)})

    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
    return jsonify({
        "status":  "started",
        "mode":    MODE,
        "params":  params,
        "message": "Перевірте GET /status або GET /result для результату",
    })


@app.route("/result")
def result():
    return jsonify(get_state())


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    host  = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("APP_MODE", "production") == "development"
    print(f" Сервер запущено: http://{host}:{port}")
    print(f"   Режим: {MODE} | Параметри: {params}")
    app.run(host=host, port=port, debug=debug)
