from django.urls import path
from . import views

urlpatterns = [
    path('', views.trip_list, name='trip_list'),
    path('create/', views.trip_create, name='trip_create'),
    path('<int:pk>/', views.trip_detail, name='trip_detail'),
    path('<int:pk>/route/', views.route_optimizer, name='route_optimizer'),
    path('<int:pk>/invite/', views.trip_invite, name='trip_invite'),
    path('<int:trip_pk>/poi/add/', views.poi_add, name='poi_add'),
    path('poi/<int:pk>/delete/', views.poi_delete, name='poi_delete'),
    path('register/', views.register, name='register'),
]
