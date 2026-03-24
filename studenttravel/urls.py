from django.contrib import admin
from django.urls import path, include
from trips import views as trip_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', trip_views.home, name='home'),
    path('trips/', include('trips.urls')),
    path('expenses/', include('expenses.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]
