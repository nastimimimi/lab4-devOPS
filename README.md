# Лабораторна робота №4 (CASE)

## Тема
Docker та контейнеризація

## Модель
Автоматизоване складання розкладу занять — Генетичний алгоритм (5 семестр)

## Автор
Баранова Анастасія, група АІ-231

## Варіант
Непарний → MODE=comfort

---

## Структура проєкту
```
lab4-docker/
├── main.py               # Генетичний алгоритм + MODE
├── app.py                # Flask веб-сервер
├── Dockerfile            # Збірка образу
├── docker-compose.yml    # Мережа (app + redis)
├── requirements.txt      # Залежності
├── .dockerignore
└── README.md
```

---

## Режими роботи (MODE)
| MODE    | Популяція | Ітерації | Мутація | Варіант  |
|---------|-----------|----------|---------|----------|
| comfort | 100       | 1000     | 0.1     | Непарний |
| eco     | 50        | 300      | 0.2     | Парний   |

---

## Запуск

### Без Docker
```bash
pip install -r requirements.txt
python main.py
```

### Docker — базовий запуск (MODE=comfort)
```bash
docker build -t schedule-optimizer .
docker run --rm -e MODE=comfort schedule-optimizer
```

### Docker — зі збереженням результатів
```bash
docker run --rm -e MODE=comfort -v $(pwd)/output:/app/output schedule-optimizer
```

### Docker — Flask сервер з портом
```bash
docker run --rm -p 8080:5000 -e MODE=comfort -e APP_MODE=development schedule-optimizer python app.py
```

### Docker Compose — мережа контейнерів
```bash
docker compose up
docker compose down
```

---

## Змінні середовища

| Змінна | Значення за замовчуванням | Опис |
|---|---|---|
| `MODE` | `comfort` | Режим роботи алгоритму |
| `PORT` | `5000` | Порт Flask-сервера |
| `APP_MODE` | `production` | Режим Flask |

---

## API ендпоінти (Flask)

| Метод | Шлях | Опис |
|---|---|---|
| GET | `/` | Інформація про сервіс |
| GET | `/status` | Поточний стан оптимізації |
| POST | `/run` | Запустити оптимізацію |
| GET | `/result` | Отримати результат |

---

## Результати

Після виконання генеруються:
- `schedule.csv` — сформований розклад занять
- `convergence.png` — графік збіжності алгоритму
- `load_distribution.png` — графік навантаження викладачів

---

## Корисні команди Docker

| Команда | Опис |
|---|---|
| `docker build -t назва .` | Зібрати образ |
| `docker run --rm назва` | Запустити контейнер |
| `docker images` | Переглянути всі образи |
| `docker ps -a` | Переглянути всі контейнери |
| `docker logs назва` | Переглянути логи |
| `docker compose up --build` | Зібрати та запустити через Compose |
| `docker compose down` | Зупинити контейнери |
