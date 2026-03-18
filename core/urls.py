from django.contrib import admin
from django.urls import path, include
from core.api import app
from django.conf.urls.static import static
from core.settings import MEDIA_ROOT, MEDIA_URL

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', app.urls)
]

urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)
