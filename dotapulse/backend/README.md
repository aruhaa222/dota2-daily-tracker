# DotaPulse API (0.1)

Локальный backend для MVP. Он проксирует OpenDota, считает базовые показатели и выдаёт детерминированные подсказки. Настоящей LLM-интеграции и анализа реплеев пока нет.

## Запуск

Требуется Python 3.11+.

```bash
cd dotapulse/backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Проверка: http://127.0.0.1:8000/health  
Swagger: http://127.0.0.1:8000/docs

## API

- `GET /api/v1/players/{account_id}/overview?limit=50`
- `GET /api/v1/players/{account_id}/matches?limit=50`
- `GET /api/v1/players/{account_id}/coach?limit=50`

`limit`: от 1 до 100. Кэш OpenDota в памяти процесса: 60 секунд.

## Тесты

```bash
cd dotapulse/backend
PYTHONPATH=. pytest -q
```

## Перед публичным запуском

- Заменить CORS localhost на точный домен фронтенда.
- Добавить общий rate limit и устойчивый внешний кэш.
- Не хранить OpenDota API key в браузере.
- Добавить интеграционные тесты и мониторинг.
- Проверить актуальные ограничения и доступность OpenDota.
