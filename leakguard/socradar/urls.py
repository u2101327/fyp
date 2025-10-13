from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.registerPage, name='register'),
    path('login/', views.loginPage, name='login'),  
    path('logout/', views.logout_view, name='logout'),   
    path('dashboard/', views.dashboard, name='dashboard'),
    path('credentials/add/', views.add_monitored_credential, name='add_monitored_credential'),
]
