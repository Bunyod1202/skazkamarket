from django.contrib import admin
from .models import Category, Product, UserProfile, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'name_ru')
    search_fields = ('name_uz', 'name_ru')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'name_ru', 'category', 'price', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name_uz', 'name_ru')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'full_name', 'phone', 'language', 'created_at')
    search_fields = ('telegram_id', 'full_name', 'phone')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total', 'status', 'created_at')
    list_filter = ('status',)
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
