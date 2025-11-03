from django.contrib import admin
from django.conf import settings
import requests
from .models import Category, Product, UserProfile, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'name_ru', 'name_en', 'sort_order', 'image')
    list_editable = ('sort_order',)
    search_fields = ('name_uz', 'name_ru', 'name_en')
    ordering = ('sort_order', 'id')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'name_ru', 'name_en', 'category', 'price', 'is_active', 'sort_order')
    list_filter = ('category', 'is_active')
    search_fields = ('name_uz', 'name_ru', 'name_en')
    list_editable = ('sort_order',)
    ordering = ('sort_order', 'id')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'username', 'full_name', 'phone', 'language', 'created_at')
    search_fields = ('telegram_id', 'username', 'full_name', 'phone')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total', 'status', 'created_at')
    list_filter = ('status',)
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    list_editable = ('status',)

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            try:
                old_status = Order.objects.get(pk=obj.pk).status
            except Order.DoesNotExist:
                old_status = None
        super().save_model(request, obj, form, change)
        if change and old_status != obj.status:
            self._notify_status_change(obj)

    @staticmethod
    def _notify_status_change(order: Order):
        token = getattr(settings, 'BOT_TOKEN', '')
        chat_id = getattr(order.user, 'telegram_id', '') if order.user_id else ''
        if not token or not chat_id:
            return
        # Localize minimal status names
        lang = (getattr(order.user, 'language', 'UZ') or 'UZ').upper()
        status_map = {
            'new':        {'UZ': 'Yangi',        'RU': 'Новый',       'EN': 'New'},
            'processing': {'UZ': 'Jarayonda',    'RU': 'В обработке', 'EN': 'Processing'},
            'done':       {'UZ': 'Tugallandi',   'RU': 'Готов',       'EN': 'Done'},
            'cancelled':  {'UZ': 'Bekor qilindi','RU': 'Отменён',     'EN': 'Cancelled'},
        }
        st_txt = status_map.get(order.status, {}).get(lang, order.status)
        texts = {
            'UZ': f"📦 Buyurtma #{order.id} status yangilandi: {st_txt}",
            'RU': f"📦 Заказ #{order.id} обновлён: {st_txt}",
            'EN': f"📦 Order #{order.id} updated: {st_txt}",
        }
        text = texts.get(lang, texts['EN'])
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
        except Exception:
            pass

    readonly_fields = ()
