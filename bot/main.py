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


def lang_label(st, uz, ru, en=None):
    lang = (st.get('language') or '').upper()
    if lang == 'RU':
        return ru
    if lang == 'EN' and en is not None:
        return en
    return uz


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
        if st.get('language') == 'RU':
            name = p.get('name_ru') or p.get('name_uz')
        elif st.get('language') == 'EN':
            name = p.get('name_en') or p.get('name_uz')
        else:
            name = p.get('name_uz')
        price = p['price']
        label = f"??? {name} ??? {price}"
        kb.add(types.InlineKeyboardButton(label, callback_data=f"add:{p['id']}:pg{page}"))

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton(lang_label(st, 'Orqaga', 'Назад', 'Prev'), callback_data=f'pg:{page-1}'))
    nav.append(types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data='noop'))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton(lang_label(st, 'Keyingi', 'Следующий', 'Next'), callback_data=f'pg:{page+1}'))
    if nav:
        kb.row(*nav)
    kb.add(types.InlineKeyboardButton(lang_label(st, f"Savat ({cart_count(st)})", f"Сумка ({cart_count(st)})", f"Cart ({cart_count(st)})"), callback_data='cart'))

    text = lang_label(st, 'Katalogdan mahsulot tanlang:', 'Каталог товара выберите:', 'Select product from catalog:')
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
        text = '\n'.join(lines) + f"\n\n{lang_label(st, 'Jami', 'Сумма', 'Total')}: {int(total) if float(total).is_integer() else total}"
    else:
        text = lang_label(st, 'Savat bo\'sh.', 'Сумка пуста.', 'Cart is empty.')

    kb = types.InlineKeyboardMarkup()
    if lines:
        kb.add(
            types.InlineKeyboardButton(lang_label(st, 'Tozalash', 'Очистить', 'Clear'), callback_data='clear'),
            types.InlineKeyboardButton(lang_label(st, 'Buyurtma berish', 'Заказать', 'Checkout'), callback_data='checkout'),
        )
    kb.add(types.InlineKeyboardButton(lang_label(st, 'Katalog', 'Каталог', 'Catalog'), callback_data='open'))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
        except Exception:
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=kb)
    else:
        bot.send_message(chat_id, text, reply_markup=kb)


def start_keyboard():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row(types.KeyboardButton('UZ'), types.KeyboardButton('RU'), types.KeyboardButton('EN'))
    return mk


def contact_keyboard(st=None):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    label = lang_label(st or {}, '📱 Telefon raqamni yuborish', '📱 Отправить телефон номер', 'Send phone number')
    mk.add(types.KeyboardButton(label, request_contact=True))
    return mk


def is_https(url: str) -> bool:
    return url.lower().startswith('https://')


def get_main_menu_keyboard(st, chat_id):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    webapp_url = f"{BASE_URL.rstrip('/')}/webapp/?tid={chat_id}&lang={(st.get('language') or 'UZ')}"
    orders_url = f"{BASE_URL.rstrip('/')}/order/?tid={chat_id}&lang={(st.get('language') or 'UZ')}"

    menu_text = lang_label(st, '📃 Menyu', '📃 Меню', '📃 Menu')
    orders_text = lang_label(st, '🛒 Buyurtmalarim', '🛒 Мои заказы', '🛒 My Orders')

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
    mk.row(types.KeyboardButton('🌐 Til / 🌐 Язык / 🌐 Language'))
    return mk

def main_menu_keyboard(st, chat_id):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    webapp_url = f"{BASE_URL.rstrip('/')}/webapp/?tid={chat_id}&lang={(st.get('language') or 'UZ')}"
    orders_url = f"{BASE_URL.rstrip('/')}/order/?tid={chat_id}&lang={(st.get('language') or 'UZ')}"

    # Localized labels styled like wide menu buttons
    menu_text = lang_label(st, '📋 MAXSULOTLARNI TANLASH ', '📋 ВЫБРАТЬ ТОВАРЫ', '📋 CHOOSE PRODUCTS')
    orders_text = lang_label(st, '🛒 BUYURTMALARIM', '🛒 ЗАКАЗЫ', '🛒 MY ORDERS')

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
    mk.row(types.KeyboardButton('🌐 Til / 🌐 Язык / 🌐 Language'))
    return mk


# Quick open helpers for typed commands (Menu / My Orders)
@bot.message_handler(func=lambda m: isinstance(m.text, str) and any(k in m.text.upper() for k in ['MENU', 'МЕНЮ', 'MAVZUNI']))
def quick_open_menu(m):
    chat_id = m.chat.id
    st = get_state(chat_id)
    webapp_url = f"{BASE_URL.rstrip('/')}/webapp/?tid={chat_id}&lang={(st.get('language') or 'UZ')}"
    if not is_https(webapp_url):
        bot.send_message(chat_id, f"Menyu: {webapp_url}", reply_markup=get_main_menu_keyboard(st, chat_id))
    else:
        # send keyboard with WebApp button; user taps it to open
        bot.send_message(chat_id, 'меню', reply_markup=get_main_menu_keyboard(st, chat_id))


@bot.message_handler(func=lambda m: isinstance(m.text, str) and any(k in m.text.upper() for k in ['MY ORDERS', 'МЙ ЗАКАЗЫ', 'MY ORDERS']))
def quick_open_orders(m):
    chat_id = m.chat.id
    st = get_state(chat_id)
    orders_url = f"{BASE_URL.rstrip('/')}/order/?tid={chat_id}&lang={(st.get('language') or 'UZ')}"
    if not is_https(orders_url):
        bot.send_message(chat_id, f"Buyurtmalarim: {orders_url}", reply_markup=get_main_menu_keyboard(st, chat_id))
    else:
        bot.send_message(chat_id, 'меню', reply_markup=get_main_menu_keyboard(st, chat_id))


# Language change entry: react to the bottom "Language" button at any time
@bot.message_handler(func=lambda m: isinstance(m.text, str) and (
    'language' in m.text.lower() or 'Язык' in m.text.lower() or 'til' in m.text.lower()
))
def handle_language_button(msg):
    chat_id = msg.chat.id
    st = get_state(chat_id)
    st['stage'] = 'change_lang'
    STATE[chat_id] = st
    bot.send_message(chat_id, 'Tilni tanlang / Выберите язык / Choose language', reply_markup=start_keyboard())


# Handle language selection when changing language (without re-onboarding)
@bot.message_handler(func=lambda m: get_state(m.chat.id).get('stage') == 'change_lang')
def handle_change_lang(msg):
    chat_id = msg.chat.id
    st = get_state(chat_id)
    text = (msg.text or '').strip().upper()
    if text.startswith('UZ'):
        st['language'] = 'UZ'
    elif text.startswith('RU'):
        st['language'] = 'RU'
    elif text.startswith('EN'):
        st['language'] = 'EN'
    else:
        bot.send_message(chat_id, 'Please choose UZ / RU / EN', reply_markup=start_keyboard())
        return
    st['stage'] = 'done'
    STATE[chat_id] = st
    try:
        requests.post(BASE_URL.rstrip('/') + '/api/user', json={'telegram_id': str(chat_id), 'language': st.get('language')}, timeout=10)
    except Exception:
        pass
    after_onboarding_message(chat_id)


def after_onboarding_message(chat_id):
    st = get_state(chat_id)
    bot.send_message(
        chat_id,
        lang_label(st, 'Xush kelibsiz! Pastdagi menyudan tanlang.', 'Добро пожаловать! Выберите из меню ниже.', 'Welcome! Select from the menu below.'),
        reply_markup=get_main_menu_keyboard(st, chat_id),
    )


@bot.message_handler(commands=['start'])
def handle_start(msg):
    chat_id = msg.chat.id
    # If profile exists (has phone and full_name), skip onboarding
    try:
        import requests as _rq
        resp = _rq.get(BASE_URL.rstrip('/') + '/api/user', params={'telegram_id': str(chat_id)}, timeout=10)
        if resp.ok:
            info = resp.json()
            if info.get('exists'):
                u = info.get('user') or {}
                if u.get('full_name') and u.get('phone'):
                    st = {'stage': 'done', 'cart': {}, 'language': (u.get('language') or 'UZ')}
                    STATE[chat_id] = st
                    after_onboarding_message(chat_id)
                    return
    except Exception:
        pass
    STATE[chat_id] = {'stage': 'language', 'cart': {}}
    bot.send_message(chat_id, 'Tilni tanlang / Выберите язык / Choose language', reply_markup=start_keyboard())


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
        elif text.upper().startswith('EN'):
            st['language'] = 'EN'
        else:
            bot.send_message(chat_id, 'Please choose UZ / RU / EN ', reply_markup=start_keyboard())
            return
        st['stage'] = 'contact'
        STATE[chat_id] = st
        bot.send_message(chat_id, 'Telefon raqamingizni yuboring / Отправьте свой номер телефона / Send your phone number', reply_markup=contact_keyboard())
        return

    if stage == 'contact':
        bot.send_message(chat_id, 'Telefonni yuborish uchun tugmadan foydalaning / Пожалуйста, используйте кнопку, чтобы отправить телефон / Please use the button to send phone ', reply_markup=contact_keyboard())
        return

    if stage == 'name':
        st['full_name'] = text
        st['stage'] = 'done'
        STATE[chat_id] = st
        # Persist full profile to backend
        try:
            import requests as _rq
            _rq.post(BASE_URL.rstrip('/') + '/api/user', json={
                'telegram_id': str(chat_id),
                'language': st.get('language'),
                'phone': st.get('phone'),
                'full_name': st.get('full_name'),
                'username': (getattr(msg.chat, 'username', None) or '')
            }, timeout=10)
        except Exception:
            pass
        return

    # Handle main menu actions from bottom reply keyboard
    text_upper = text.upper()
    if ('MY ORDERS' in text_upper) or ('ЗАКАЗЫ' in text_upper) or ('BUYURTMALAR' in text_upper):
        orders_url = BASE_URL.rstrip('/') + '/order/'
        if not is_https(orders_url):
            bot.send_message(chat_id, lang_label(st, 'Mening buyurtmalarim: ', 'Заказы: ', 'My orders: ') + orders_url, reply_markup=get_main_menu_keyboard(st, chat_id))
        return

    if ('MENU' in text_upper) or ('МЕНЮ' in text_upper) or ('MAVZUNI' in text_upper):
        webapp_url = BASE_URL.rstrip('/') + '/webapp/'
        if not is_https(webapp_url):
            # Send URL as text for non-HTTPS/local
            bot.send_message(chat_id, lang_label(st, 'Menyu: ', 'Меню: ', 'Menu: ') + webapp_url, reply_markup=get_main_menu_keyboard(st, chat_id))
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
        bot.send_message(chat_id, 'Полное имя введите (ФИО)')
    elif st.get('language') == 'UZ':
        bot.send_message(chat_id, "To'liq ismingizni kiriting (FIO)")
    else: 
        bot.send_message(chat_id, 'Enter your full name (FIO)')
    # Persist phone to backend
    try:
        import requests as _rq
        _rq.post(BASE_URL.rstrip('/') + '/api/user', json={
            'telegram_id': str(chat_id),
            'language': st.get('language'),
            'phone': phone,
            'full_name': ((getattr(msg.from_user, 'first_name', '') or '') + ((' ' + getattr(msg.from_user, 'last_name', '')) if getattr(msg.from_user, 'last_name', None) else '')),
            'username': (getattr(msg.chat, 'username', None) or '')
        }, timeout=10)
    except Exception:
        pass

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
            bot.answer_callback_query(call.id, lang_label(st, "Qo'shildi", "Добавлено", "Added"))
            send_catalog(chat_id, page=page_hint, message_id=call.message.message_id)
            return
        # Keep inline catalog/cart features available if needed; no changes for orders/menu here now.
        if data == 'clear':
            st['cart'].clear()
            bot.answer_callback_query(call.id, lang_label(st, "Tozalandi", "Очищено", "Cleared"))
            send_cart(chat_id, message_id=call.message.message_id)
            return
        if data == 'checkout':
            if not st.get('cart'):
                bot.answer_callback_query(call.id, lang_label(st, "Savat bo'sh", "Корзина пуста", "Cart is empty"))
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
                bot.answer_callback_query(call.id, lang_label(st, "Yuborildi", "Отправлено", "Sent"))
                text = lang_label(st, "Buyurtma qabul qilindi!", "Заказ принят!", "Order placed!")
                bot.edit_message_text(text, chat_id, call.message.message_id)
            except Exception as e:
                logging.exception('Checkout failed: %s', e)
                bot.answer_callback_query(call.id, lang_label(st, "Xatolik", "Ошибка", "Error"), show_alert=True)
            return
    except Exception as e:
        logging.exception('Callback error: %s', e)
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass


def main_menu_keyboard(st, chat_id):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    webapp_url = f"{BASE_URL.rstrip('/')}/webapp/?tid={chat_id}&lang={(st.get('language') or 'UZ')}"
    orders_url = f"{BASE_URL.rstrip('/')}/order/?tid={chat_id}&lang={(st.get('language') or 'UZ')}"

    # Localized labels styled like wide menu buttons (UZ / RU / EN)
    menu_text = lang_label(st, 'MAXSULOTLARNI TANLASH', 'ВЫБЕРИТЕ ТОВАР', 'SELECT PRODUCTS')
    orders_text = lang_label(st, 'BUYURTMALARIM', 'МОИ ЗАКАЗЫ', 'MY ORDERS')

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
    mk.row(types.KeyboardButton('Til / Язык / Language'))
    return mk


def main():
    print('Bot started. Listening for updates...')
    try:
        bot.remove_webhook()
    except Exception as e:
        logging.warning('remove_webhook failed: %s', e)
    bot.infinity_polling(skip_pending=True, timeout=60)


if __name__ == '__main__':
    main()

