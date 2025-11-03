# Telegram Online Market (Django + Telegram WebApp)

This is a minimal, scalable scaffold for an online market integrated with a Telegram WebApp and a Django backend.

Features
- Telegram bot (pyTelegramBotAPI)
- WebApp frontend (HTML/CSS/JS, Telegram WebApp API)
- Django models: Category, Product, UserProfile, Order, OrderItem
- API endpoints: `/api/products`, `/api/order` (CSRF exempt)
- Admin panel for categories, products, orders
- SQLite database, static/media setup

Folder Structure
- `manage.py` – Django entry
- `config/` – Django project (settings, urls, asgi, wsgi)
- `shop/` – App (models, admin, views, urls)
- `templates/webapp/` – WebApp HTML
- `static/webapp/` – WebApp CSS/JS
- `bot.py` – Telegram bot script
- `requirements.txt` – Python dependencies
- `.env.example` – Environment config template

Prerequisites
- Python 3.10+

Setup
1) Create and activate venv
```
python -m venv .venv
. .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
```

2) Install dependencies
```
pip install -r requirements.txt
```

3) Configure environment
- Copy `.env.example` to `.env` and set values
- Important: set `BOT_TOKEN`, `BASE_URL`, `ADMIN_CHAT_ID`

4) Initialize database
```
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

5) Run Django
```
python manage.py runserver 0.0.0.0:8000
```
- Admin panel: http://localhost:8000/admin/
- WebApp: http://localhost:8000/webapp/

6) Run the Telegram bot (in another terminal)
```
python bot\main.py
```

Usage Flow
- In Telegram, start your bot with `/start`
- Select language, share phone, enter full name
- Open the WebApp via the provided button
- Add products to cart, add a comment, click checkout
- Backend creates an order and sends confirmations to the user and admin chat

Notes
- `/api/products` returns all active products (includes both `name_uz` and `name_ru`). The WebApp picks by Telegram language.
- `/api/order` expects JSON: `{ telegram_id, language, phone, full_name, comment, items: [{product_id, quantity}] }`
- Images can be uploaded via admin; product images are served via `/media/` in DEBUG.
- CSRF is disabled for `/api/order` via `@csrf_exempt`.

Next Steps / Production
- Add auth/validation for initData signature (Telegram spec) if needed.
- Add pagination and categories in product API.
- Move from polling to a webhook for the bot.
- Add i18n for Django admin/content.
