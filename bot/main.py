import os
import logging
import requests
from dotenv import load_dotenv
from telebot import TeleBot, types


load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')

if not BOT_TOKEN:
    raise SystemExit('BOT_TOKEN is not set in environment/.env')

bot = TeleBot(BOT_TOKEN, parse_mode='HTML')
logging.basicConfig(level=logging.INFO)

# Per-user state in memory
# { chat_id: {stage, language, phone, full_name, cart:{product_id: qty}} }
STATE = {}

# Simple products cache
PRODUCTS_CACHE = {'items': []}


def get_state(chat_id):
    st = STATE.get(chat_id)
    if not st:
        st = {'stage': 'language', 'cart': {}}
        STATE[chat_id] = st
    if 'cart' not in st:
        st['cart'] = {}
    return st


def lang_label(st, uz, ru):
    return ru if st.get('language') == 'RU' else uz


def cart_count(st):
    return sum(st.get('cart', {}).values())


def load_products():
    url = BASE_URL.rstrip('/') + '/api/products'
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    PRODUCTS_CACHE['items'] = data.get('products', [])
    return PRODUCTS_CACHE['items']


def products():
    if not PRODUCTS_CACHE['items']:
        return load_products()
    return PRODUCTS_CACHE['items']


def send_catalog(chat_id, page=1, message_id=None):
    st = get_state(chat_id)
    items = products()
    per = 6
    total_pages = max(1, (len(items) + per - 1) // per)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per
    chunk = items[start:start+per]

    kb = types.InlineKeyboardMarkup()
    for p in chunk:
        name = p['name_ru'] if st.get('language') == 'RU' else p['name_uz']
        price = p['price']
        label = f"Add: {name} - {price}"
        kb.add(types.InlineKeyboardButton(label, callback_data=f"add:{p['id']}:pg{page}"))

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton('Prev', callback_data=f'pg:{page-1}'))
    nav.append(types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data='noop'))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton('Next', callback_data=f'pg:{page+1}'))
    if nav:
        kb.row(*nav)
    kb.add(types.InlineKeyboardButton(f"Cart ({cart_count(st)})", callback_data='cart'))

    text = lang_label(st, 'Katalogdan mahsulot tanlang:', 'Выберите товары из каталога:')
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
        except Exception:
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=kb)
    else:
        bot.send_message(chat_id, text, reply_markup=kb)


def send_cart(chat_id, message_id=None):
    st = get_state(chat_id)
    cart = st.get('cart', {})
    by_id = {p['id']: p for p in products()}
    total = 0.0
    lines = []
    for pid, qty in cart.items():
        p = by_id.get(int(pid))
        if not p:
            continue
        price = float(p['price'])
        total += price * qty
        name = p['name_ru'] if st.get('language') == 'RU' else p['name_uz']
        lines.append(f"{name} x{qty}")
    if lines:
        text = '\n'.join(lines) + f"\n\n{lang_label(st, 'Jami', 'Итого')}: {int(total) if float(total).is_integer() else total}"
    else:
        text = lang_label(st, 'Savat bo\'sh.', 'Корзина пуста.')

    kb = types.InlineKeyboardMarkup()
    if lines:
        kb.add(
            types.InlineKeyboardButton(lang_label(st, 'Tozalash', 'Очистить'), callback_data='clear'),
            types.InlineKeyboardButton(lang_label(st, 'Buyurtma berish', 'Оформить'), callback_data='checkout'),
        )
    kb.add(types.InlineKeyboardButton(lang_label(st, 'Katalog', 'Каталог'), callback_data='open'))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
        except Exception:
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=kb)
    else:
        bot.send_message(chat_id, text, reply_markup=kb)


def start_keyboard():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row(types.KeyboardButton('UZ'), types.KeyboardButton('RU'))
    return mk


def contact_keyboard():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    mk.add(types.KeyboardButton('Send phone / Отправить телефон', request_contact=True))
    return mk


def is_https(url: str) -> bool:
    return url.lower().startswith('https://')


def main_menu_keyboard(st):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    webapp_url = BASE_URL.rstrip('/') + '/webapp/'
    orders_url = BASE_URL.rstrip('/') + '/order/'

    # Localized labels styled like wide menu buttons
    menu_text = lang_label(st, '✏️ MAVZUNI TANLAYMIZ ◻️', '✏️ ВЫБРАТЬ РАЗДЕЛ ◻️')
    orders_text = lang_label(st, '🧾 BUYURTMALARIM', '🧾 МОИ ЗАКАЗЫ')

    # WebApp buttons when HTTPS; plain text fallback on HTTP
    if is_https(webapp_url):
        menu_btn = types.KeyboardButton(menu_text, web_app=types.WebAppInfo(webapp_url))
    else:
        menu_btn = types.KeyboardButton(menu_text)

    if is_https(orders_url):
        orders_btn = types.KeyboardButton(orders_text, web_app=types.WebAppInfo(orders_url))
    else:
        orders_btn = types.KeyboardButton(orders_text)

    mk.row(menu_btn)
    mk.row(orders_btn)
    return mk


def after_onboarding_message(chat_id):
    st = get_state(chat_id)
    bot.send_message(
        chat_id,
        lang_label(st, 'Xush kelibsiz! Pastdagi menyudan tanlang.', 'Добро пожаловать! Выберите действие ниже.'),
        reply_markup=main_menu_keyboard(st),
    )


@bot.message_handler(commands=['start'])
def handle_start(msg):
    chat_id = msg.chat.id
    STATE[chat_id] = {'stage': 'language', 'cart': {}}
    bot.send_message(chat_id, 'Tilni tanlang / Выберите язык', reply_markup=start_keyboard())


@bot.message_handler(content_types=['text'])
def handle_text(msg):
    chat_id = msg.chat.id
    text = (msg.text or '').strip()
    st = get_state(chat_id)
    stage = st.get('stage')

    if stage == 'language':
        if text.upper().startswith('UZ'):
            st['language'] = 'UZ'
        elif text.upper().startswith('RU'):
            st['language'] = 'RU'
        else:
            bot.send_message(chat_id, 'Please choose UZ or RU / Пожалуйста, выберите UZ или RU', reply_markup=start_keyboard())
            return
        st['stage'] = 'contact'
        STATE[chat_id] = st
        bot.send_message(chat_id, 'Telefon raqamingizni yuboring / Отправьте ваш телефон', reply_markup=contact_keyboard())
        return

    if stage == 'contact':
        bot.send_message(chat_id, 'Please use the button to send phone / Используйте кнопку для отправки телефона', reply_markup=contact_keyboard())
        return

    if stage == 'name':
        st['full_name'] = text
        st['stage'] = 'done'
        STATE[chat_id] = st
        after_onboarding_message(chat_id)
        return

    # Handle main menu actions from bottom reply keyboard
    text_upper = text.upper()
    if ('MY ORDERS' in text_upper) or ('МОИ ЗАКАЗЫ' in text_upper) or ('BUYURTMALAR' in text_upper):
        orders_url = BASE_URL.rstrip('/') + '/order/'
        if not is_https(orders_url):
            bot.send_message(chat_id, lang_label(st, 'Mening buyurtmalarim: ', 'Мои заказы: ') + orders_url, reply_markup=main_menu_keyboard(st))
        return

    if ('MENU' in text_upper) or ('МЕНЮ' in text_upper) or ('MAVZUNI' in text_upper):
        webapp_url = BASE_URL.rstrip('/') + '/webapp/'
        if not is_https(webapp_url):
            # Send URL as text for non-HTTPS/local
            bot.send_message(chat_id, lang_label(st, 'Menyu: ', 'Меню: ') + webapp_url, reply_markup=main_menu_keyboard(st))
        # If HTTPS and WebApp button is present, pressing it opens the app and does not send text
        return

    after_onboarding_message(chat_id)


@bot.message_handler(content_types=['contact'])
def handle_contact(msg):
    chat_id = msg.chat.id
    st = get_state(chat_id)
    if st.get('stage') != 'contact':
        after_onboarding_message(chat_id)
        return
    phone = msg.contact.phone_number if msg.contact and msg.contact.phone_number else None
    st['phone'] = phone
    st['stage'] = 'name'
    STATE[chat_id] = st
    if st.get('language') == 'RU':
        bot.send_message(chat_id, 'Введите ваше полное имя (ФИО)')
    else:
        bot.send_message(chat_id, 'To‘liq ismingizni kiriting (FIO)')


@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id if call.message else call.from_user.id
    st = get_state(chat_id)
    data = call.data or ''

    try:
        if data == 'noop':
            bot.answer_callback_query(call.id)
            return
        if data == 'open':
            bot.answer_callback_query(call.id)
            send_catalog(chat_id, page=1, message_id=call.message.message_id)
            return
        if data.startswith('pg:'):
            page = int(data.split(':', 1)[1])
            bot.answer_callback_query(call.id)
            send_catalog(chat_id, page=page, message_id=call.message.message_id)
            return
        if data.startswith('add:'):
            parts = data.split(':')
            pid = int(parts[1])
            page_hint = 1
            if len(parts) > 2 and parts[2].startswith('pg'):
                try:
                    page_hint = int(parts[2][2:])
                except Exception:
                    page_hint = 1
            st['cart'][pid] = st['cart'].get(pid, 0) + 1
            bot.answer_callback_query(call.id, lang_label(st, 'Qoshildi', 'Добавлено'))
            send_catalog(chat_id, page=page_hint, message_id=call.message.message_id)
            return
        # Keep inline catalog/cart features available if needed; no changes for orders/menu here now.
        if data == 'clear':
            st['cart'].clear()
            bot.answer_callback_query(call.id, lang_label(st, 'Tozalandi', 'Очищено'))
            send_cart(chat_id, message_id=call.message.message_id)
            return
        if data == 'checkout':
            if not st.get('cart'):
                bot.answer_callback_query(call.id, lang_label(st, 'Savat bosh', 'Пусто'))
                return
            items = [{ 'product_id': int(pid), 'quantity': qty } for pid, qty in st['cart'].items() if qty > 0]
            payload = {
                'telegram_id': str(chat_id),
                'language': st.get('language') or 'UZ',
                'phone': st.get('phone') or '',
                'full_name': st.get('full_name') or '',
                'comment': '',
                'items': items,
            }
            try:
                url = BASE_URL.rstrip('/') + '/api/order'
                r = requests.post(url, json=payload, timeout=15)
                r.raise_for_status()
                _ = r.json()
                st['cart'].clear()
                bot.answer_callback_query(call.id, lang_label(st, 'Yuborildi', 'Отправлено'))
                text = lang_label(st, 'Buyurtma qabul qilindi!', 'Заказ принят!')
                bot.edit_message_text(text, chat_id, call.message.message_id)
            except Exception as e:
                logging.exception('Checkout failed: %s', e)
                bot.answer_callback_query(call.id, lang_label(st, 'Xatolik', 'Ошибка'), show_alert=True)
            return
    except Exception as e:
        logging.exception('Callback error: %s', e)
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass


def main():
    print('Bot started. Listening for updates...')
    try:
        bot.remove_webhook()
    except Exception as e:
        logging.warning('remove_webhook failed: %s', e)
    bot.infinity_polling(skip_pending=True, timeout=60)


if __name__ == '__main__':
    main()
