from django.conf import settings
from .models import Ticket

def maptiler_key(request):
    return {'MAPTILER_API_KEY': settings.MAPTILER_API_KEY}

PAGE_TITLES = {
    'home': ('Ana Sayfa', None),
    'new_ticket': ('Talep Oluştur', None),
    'track': ('Takip Et', 'Talepler'),
    'public_map': ('Kent Haritası', 'Talepler'),
    'ticket_list': ('Tüm Talepler', 'Talepler'),
    'public_ticket_detail': ('Talep Detayı', 'Talepler'),
    'dashboard': ('Yönetici Paneli', 'Yönetim'),
    'staff_panel': ('İş Emirlerim', 'Yönetim'),
    'staff_ticket_detail': ('Talep İşlemi', 'Yönetim'),
    'form_builder_list': ('Form Yönetimi', 'Yönetim'),
    'form_builder_edit': ('Form Düzenle', 'Yönetim'),
    'login': ('Personel Girişi', None),
    'rate_ticket': ('Değerlendirme', None),
    'article_list': ('Bilgilendirme', None),
    'article_detail': ('Makale', 'Bilgilendirme'),
    'article_manage_list': ('Makalelerim', 'Yönetim'),
    'article_create': ('Yeni Makale', 'Yönetim'),
}


def page_title(request):
    url_name = getattr(request.resolver_match, 'url_name', None) if request.resolver_match else None
    title, parent = PAGE_TITLES.get(url_name, ('', None))
    return {'PAGE_TITLE': title, 'PAGE_PARENT': parent}

def maptiler_key(request):
    return {'MAPTILER_API_KEY': settings.MAPTILER_API_KEY}


def site_stats(request):
    return {
        'GLOBAL_TOTAL_TICKETS': Ticket.objects.count(),
        'GLOBAL_RESOLVED_TICKETS': Ticket.objects.filter(status='RESOLVED').count(),
    }

