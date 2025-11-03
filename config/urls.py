from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('shop.urls')),
    path('webapp/', TemplateView.as_view(template_name='webapp/index.html'), name='webapp'),
    path('orders/', TemplateView.as_view(template_name='webapp/orders.html'), name='orders'),
    path('order/', TemplateView.as_view(template_name='webapp/order.html'), name='order_single'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
