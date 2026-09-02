from django.conf import settings
from .models import Ticket

def maptiler_key(request):
    return {'MAPTILER_API_KEY': settings.MAPTILER_API_KEY}

PAGE_TITLES = {
    'home': 'Ana Sayfa',
    'new_ticket': 'Talep Oluştur',
    'track': 'Takip Et',
    'public_map': 'Kent Haritası',
    'ticket_list': 'Tüm Talepler',
    'public_ticket_detail': 'Talep Detayı',
    'dashboard': 'Yönetici Paneli',
    'staff_panel': 'İş Emirlerim',
    'staff_ticket_detail': 'Talep İşlemi',
    'form_builder_list': 'Form Yönetimi',
    'form_builder_edit': 'Form Düzenle',
    'login': 'Personel Girişi',
    'rate_ticket': 'Değerlendirme',
    'article_list': 'Bilgilendirme',
    'article_detail': 'Makale',
    'article_manage_list': 'Makalelerim',
    'article_create': 'Yeni Makale',
}


def maptiler_key(request):
    return {'MAPTILER_API_KEY': settings.MAPTILER_API_KEY}


def site_stats(request):
    return {
        'GLOBAL_TOTAL_TICKETS': Ticket.objects.count(),
        'GLOBAL_RESOLVED_TICKETS': Ticket.objects.filter(status='RESOLVED').count(),
    }


def page_title(request):
    url_name = getattr(request.resolver_match, 'url_name', None) if request.resolver_match else None
    return {'PAGE_TITLE': PAGE_TITLES.get(url_name, '')}