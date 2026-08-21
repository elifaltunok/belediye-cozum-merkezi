from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.home, name='home'),
    path('basarili/<str:tracking_code>/', views.ticket_success, name='ticket_success'),
    path('takip/', views.track, name='track'),
    path('harita/', views.public_map, name='public_map'),
    path('talepler/', views.ticket_list, name='ticket_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('panel/', views.staff_panel, name='staff_panel'),
    path('panel/<int:pk>/', views.staff_ticket_detail, name='staff_ticket_detail'),
    path('giris/', auth_views.LoginView.as_view(template_name='tickets/login.html'), name='login'),
    path('cikis/', auth_views.LogoutView.as_view(), name='logout'),
]