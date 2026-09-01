from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.home, name='home'),
    path('basvuru/', views.new_ticket, name='new_ticket'),
    path('basarili/<str:tracking_code>/', views.ticket_success, name='ticket_success'),
    path('takip/', views.track, name='track'),
    path('harita/', views.public_map, name='public_map'),
    path('talepler/', views.ticket_list, name='ticket_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('panel/', views.staff_panel, name='staff_panel'),
    path('panel/<int:pk>/', views.staff_ticket_detail, name='staff_ticket_detail'),
    path('giris/', auth_views.LoginView.as_view(template_name='tickets/login.html'), name='login'),
    path('cikis/', auth_views.LogoutView.as_view(), name='logout'),
    path('cozum/<str:tracking_code>/', views.public_ticket_detail, name='public_ticket_detail'),
    path('api/yakin-talepler/', views.nearby_tickets, name='nearby_tickets'),
    path('destekle/<str:tracking_code>/', views.support_ticket, name='support_ticket'),
    path('api/otp/gonder/', views.request_otp, name='request_otp'),
    path('api/otp/dogrula/', views.verify_otp, name='verify_otp'),
    path('api/kategori-alanlari/<int:category_id>/', views.category_fields, name='category_fields'),
    path('form-yonetimi/', views.form_builder_list, name='form_builder_list'),
    path('form-yonetimi/<int:category_id>/', views.form_builder_edit, name='form_builder_edit'),
    path('form-yonetimi/<int:category_id>/alan-ekle/', views.form_field_create, name='form_field_create'),
    path('form-yonetimi/alan/<int:field_id>/guncelle/', views.form_field_update, name='form_field_update'),
    path('form-yonetimi/alan/<int:field_id>/sil/', views.form_field_delete, name='form_field_delete'),
    path('form-yonetimi/<int:category_id>/sirala/', views.form_field_reorder, name='form_field_reorder'),
    path('rapor/excel/', views.export_tickets_excel, name='export_tickets_excel'),
    path('rapor/pdf/', views.export_dashboard_pdf, name='export_dashboard_pdf'),
    path('rapor/talep/<int:pk>/pdf/', views.export_ticket_pdf, name='export_ticket_pdf'),
    path('degerlendir/<str:tracking_code>/', views.rate_ticket, name='rate_ticket'),
    path('yorum-ekle/<str:tracking_code>/', views.add_citizen_comment, name='add_citizen_comment'),
    path('panel/<int:pk>/yorum-ekle/', views.add_staff_comment, name='add_staff_comment'),
]