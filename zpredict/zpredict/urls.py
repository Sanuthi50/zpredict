from django.contrib import admin
from django.urls import path
from django.urls import include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('website/', include('website.urls')),  
    path('gamified/', include('gamified.urls')),  # Gamified version
    path('', include('UI.urls')),             
]
