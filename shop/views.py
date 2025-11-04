import json
from decimal import Decimal
import requests

from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Product, UserProfile, Order, OrderItem, Category
from django.db.models import Count, Q


def _abs_media_url(request, rel_url: str) -> str:
    """Return absolute https URL for media.

    Preference order:
    1) settings.BASE_URL if it is HTTPS
    2) request.build_absolute_uri (respects SECURE_PROXY_SSL_HEADER)
    This avoids generating http:// links that Telegram blocks in WebView.
    """
    if not rel_url:
        return ''
    base = getattr(settings, 'BASE_URL', '') or ''
    try:
        if base and isinstance(base, str) and base.lower().startswith("https://"):
            base = base.rstrip("/")
            if not rel_url.startswith("/"):
                rel_url = '/' + rel_url
            return f"{base}{rel_url}"
    except Exception:
        pass
    # fallback to request-based absolute url (should be https with proxy headers)
    if not rel_url.startswith("/"):
        rel_url = '/' + rel_url
    return request.build_absolute_uri(rel_url)
def product_to_dict(request, p: Product):
    image_url = _abs_media_url(request, p.image.url) if p.image else ''
    return {
        'id': p.id,
        'name_uz': p.name_uz,
        'name_ru': p.name_ru,
        'name_en': getattr(p, 'name_en', '') or '',
        'price': float(p.price),
        'image': image_url,
        'category_id': p.category_id,
        'sort_order': getattr(p, 'sort_order', 0),
    }


@require_GET
def products(request):
    qs = Product.objects.filter(is_active=True).select_related('category').order_by('sort_order', 'id')
    data = [product_to_dict(request, p) for p in qs]
    return JsonResponse({'products': data})


@require_GET
def categories(request):
    qs = (
        Category.objects
        .annotate(active_count=Count('products', filter=Q(products__is_active=True)))
        .order_by('sort_order', 'id')
    )
    data = [
        {
            'id': c.id,
            'name_uz': c.name_uz,
            'name_ru': c.name_ru,
            'name_en': c.name_en,
            'image': (_abs_media_url(request, c.image.url) if c.image else ''),
            'count': c.active_count,
            'sort_order': getattr(c, 'sort_order', 0),
        }
        for c in qs
    ]
    return JsonResponse({'categories': data})


def send_telegram_message(chat_id: str, text: str):
    token = settings.BOT_TOKEN
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={'chat_id': chat_id, 'text': text})
    except Exception:
        # Fail silently in scaffold
        pass


@csrf_exempt
@require_POST
def create_order(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    telegram_id = str(payload.get('telegram_id', ''))
    if not telegram_id:
        return HttpResponseBadRequest('telegram_id required')

    language = payload.get('language')
    phone = payload.get('phone')
    full_name = payload.get('full_name')
    comment = payload.get('comment') or ''
    address = payload.get('address') or ''
    contact_whatsapp = payload.get('whatsapp') or ''
    contact_email = payload.get('email') or ''
    items = payload.get('items') or []
    username = payload.get('username')

    if not items:
        return HttpResponseBadRequest('Cart is empty')

    user, _ = UserProfile.objects.get_or_create(telegram_id=telegram_id)
    if language:
        user.language = language
    if phone:
        user.phone = phone
    if full_name:
        user.full_name = full_name
    if username:
        user.username = username
    user.save()

    product_ids = [int(i.get('product_id')) for i in items if i.get('product_id')]
    products_map = {p.id: p for p in Product.objects.filter(id__in=product_ids, is_active=True)}

    order_total = Decimal('0.00')
    order = Order.objects.create(
        user=user,
        total=Decimal('0.00'),
        comment=comment,
        address=address,
        contact_whatsapp=contact_whatsapp,
        contact_email=contact_email,
    )

    for it in items:
        pid = int(it.get('product_id'))
        qty = int(it.get('quantity', 0))
        if qty <= 0 or pid not in products_map:
            continue
        product = products_map[pid]
        line_total = Decimal(product.price) * qty
        order_total += line_total
        OrderItem.objects.create(order=order, product=product, quantity=qty, price=product.price)

    order.total = order_total
    order.save()

    # Build messages
    admin_text_lines = [
        f"New order #{order.id}",
        f"User: {user.full_name or ''} ({user.telegram_id})",
        f"Phone: {user.phone or ''}",
        f"WhatsApp: {order.contact_whatsapp or ''}",
        f"Email: {order.contact_email or ''}",
        f"Lang: {user.language or ''}",
        f"Address: {address}",
        f"Comment: {comment}",
        "Items:",
    ]
    for oi in order.items.select_related('product'):
        admin_text_lines.append(f" - {oi.product.name_uz} x{oi.quantity} = {oi.price} * {oi.quantity}")
    admin_text_lines.append(f"Total: {order.total}")
    admin_text = '\n'.join(admin_text_lines)

    user_text = f"вњ… Buyurtma qabul qilindi!\n\n# {order.id} summa: {order.total}"

    send_telegram_message(chat_id=user.telegram_id, text=user_text)
    if getattr(settings, 'ADMIN_CHAT_ID', ''):
        send_telegram_message(chat_id=settings.ADMIN_CHAT_ID, text=admin_text)

    return JsonResponse({'status': 'ok', 'order_id': order.id, 'total': float(order.total)})


@require_GET
def my_orders(request):
    telegram_id = request.GET.get('telegram_id') or ''
    if not telegram_id:
        return JsonResponse({'orders': []})
    try:
        user = UserProfile.objects.get(telegram_id=str(telegram_id))
    except UserProfile.DoesNotExist:
        return JsonResponse({'orders': []})

    orders = (
        Order.objects.filter(user=user)
        .order_by('-created_at')
        .prefetch_related('items__product')
    )
    out = []
    for o in orders:
        items = []
        for it in o.items.all():
            items.append({
                'product_id': it.product_id,
                'product_name_uz': it.product.name_uz,
                'product_name_ru': it.product.name_ru,
                'product_name_en': getattr(it.product, 'name_en', '') or '',
                'quantity': it.quantity,
                'price': float(it.price),
            })
        out.append({
            'id': o.id,
            'total': float(o.total),
            'status': o.status,
            'comment': o.comment or '',
            'created_at': o.created_at.isoformat(),
            'items': items,
        })
    return JsonResponse({'orders': out})


@csrf_exempt
def upsert_user(request):
    if request.method == 'GET':
        telegram_id = request.GET.get('telegram_id') or ''
        if not telegram_id:
            return JsonResponse({'exists': False})
        try:
            user = UserProfile.objects.get(telegram_id=str(telegram_id))
        except UserProfile.DoesNotExist:
            return JsonResponse({'exists': False})
        return JsonResponse({
            'exists': True,
            'user': {
                'telegram_id': user.telegram_id,
                'language': user.language,
                'phone': user.phone,
                'full_name': user.full_name,
                'username': getattr(user, 'username', ''),
            }
        })

    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')

        telegram_id = str(payload.get('telegram_id') or '').strip()
        if not telegram_id:
            return HttpResponseBadRequest('telegram_id required')

        language = payload.get('language')
        phone = payload.get('phone')
        full_name = payload.get('full_name')
        username = payload.get('username')

        user, _ = UserProfile.objects.get_or_create(telegram_id=telegram_id)
        if language:
            user.language = language
        if phone:
            user.phone = phone
        if full_name:
            user.full_name = full_name
        if username:
            user.username = username
        user.save()
        return JsonResponse({'status': 'ok'})

    return HttpResponseBadRequest('Unsupported method')
