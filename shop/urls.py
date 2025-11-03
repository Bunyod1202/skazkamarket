from django.urls import path
from . import views

urlpatterns = [
    path('categories', views.categories, name='api_categories'),
    path('products', views.products, name='api_products'),
    path('order', views.create_order, name='api_order'),
    path('my-orders', views.my_orders, name='api_my_orders'),
]
