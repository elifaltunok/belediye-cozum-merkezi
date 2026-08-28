from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Avg, F, DurationField, ExpressionWrapper, Max
from django.db.models.functions import TruncMonth
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from datetime import timedelta
from django.utils import timezone

from .models import (
    Ticket, Category, Resolution, SolutionCenter, SectoralStatistic,
    SECTOR_CHOICES, UNIT_CHOICES, PhoneVerification,
    DynamicField, DynamicFieldResponse, FormFieldAuditLog,
)
from .forms import TicketForm, ResolutionForm, TrackingForm
from .notifications import notify_status_change
from .sms import generate_otp, send_otp_sms
from .reports import build_tickets_excel, build_dashboard_pdf, build_ticket_pdf

CATEGORY_ICON_KEYWORDS = {
    'kaldırım': 'bi-cone-striped',
    'yol': 'bi-signpost-split-fill',
    'çöp': 'bi-trash3-fill',
    'temizlik': 'bi-trash3-fill',
    'park': 'bi-tree-fill',
    'yeşil': 'bi-tree-fill',
    'su': 'bi-droplet-fill',
    'kanalizasyon': 'bi-droplet-fill',
    'trafik': 'bi-sign-turn-right-fill',
    'ulaşım': 'bi-bus-front-fill',
    'aydınlatma': 'bi-lightbulb-fill',
    'gürültü': 'bi-volume-up-fill',
    'hayvan': 'bi-heart-fill',
    'otopark': 'bi-p-square-fill',
    'elektrik': 'bi-lightning-charge-fill',
    'kanal': 'bi-water',
}

OTP_VALID_MINUTES = 5
OTP_RESEND_SECONDS = 60

def get_category_icon(category):
    name_lower = category.name.lower()
    for keyword, icon in CATEGORY_ICON_KEYWORDS.items():
        if keyword in name_lower:
            return icon
    return UNIT_ICONS.get(category.default_unit, 'bi-three-dots')

CATEGORY_COLOR_PALETTE = [
    '#2563eb',  # mavi
    '#dc2626',  # kırmızı
    '#16a34a',  # yeşil
    '#f59e0b',  # amber
    '#7c3aed',  # mor
    '#0891b2',  # teal
    '#db2777',  # pembe
    '#ea580c',  # turuncu
    '#4338ca',  # indigo
    '#059669',  # zümrüt
    '#c026d3',  # fuşya
    '#65a30d',  # lime
]


def get_category_color(category_id):
    return CATEGORY_COLOR_PALETTE[category_id % len(CATEGORY_COLOR_PALETTE)]

UNIT_ICONS = {
    'FEN_ISLERI': 'bi-cone-striped',
    'TEMIZLIK': 'bi-trash3-fill',
    'PARK_BAHCE': 'bi-tree-fill',
    'SU_KANAL': 'bi-droplet-fill',
    'ZABITA': 'bi-shield-check',
    'DIGER': 'bi-three-dots',
}


def home(request):
    stats = {
        'total': Ticket.objects.count(),
        'resolved': Ticket.objects.filter(status='RESOLVED').count(),
        'districts': Ticket.objects.values('district').distinct().count(),
        'centers': SolutionCenter.objects.count(),
    }

    browse_categories = [
        {'id': c.id, 'name': c.name, 'icon': get_category_icon(c), 'color': get_category_color(c.id)}
        for c in Category.objects.all()[:6]
    ]

    recent_resolved = Ticket.objects.filter(status='RESOLVED').select_related('category').prefetch_related('resolutions').order_by('-updated_at')[:6]

    return render(request, 'tickets/home.html', {
        'stats': stats,
        'browse_categories': browse_categories,
        'recent_resolved': recent_resolved,
    })


def public_ticket_detail(request, tracking_code):
    ticket = get_object_or_404(
        Ticket.objects.select_related('category').prefetch_related('resolutions'),
        tracking_code=tracking_code
    )
    resolution = ticket.resolutions.first()

    return render(request, 'tickets/public_ticket_detail.html', {
        'ticket': ticket,
        'resolution': resolution,
    })

def new_ticket(request):
    initial = {}
    preselected_category = request.GET.get('category')
    if preselected_category:
        initial['category'] = preselected_category

    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        phone = request.POST.get('phone', '').strip()
        verified_phones = request.session.get('verified_phones', [])

        if not phone or phone not in verified_phones:
            messages.error(request, "Devam etmeden önce telefon numaranızı doğrulamanız gerekiyor.")
        elif form.is_valid():
            ticket = form.save(commit=False)
            ticket.phone = phone
            ticket.save()
            messages.success(request, f"Talebiniz alındı! Takip Kodunuz: {ticket.tracking_code}")
            return redirect('tickets:ticket_success', tracking_code=ticket.tracking_code)
    else:
        form = TicketForm(initial=initial)

    quick_categories = [
        {'id': c.id, 'name': c.name, 'icon': get_category_icon(c), 'color': get_category_color(c.id)}
        for c in Category.objects.all()
    ]

    return render(request, 'tickets/new_ticket.html', {
        'form': form,
        'quick_categories': quick_categories,
        'preselected_category': preselected_category,
    })

def ticket_success(request, tracking_code):
    ticket = get_object_or_404(Ticket, tracking_code=tracking_code)
    return render(request, 'tickets/ticket_success.html', {'ticket': ticket})


@staff_member_required
def dashboard(request):
    # Durum dağılımı
    status_qs = list(Ticket.objects.values('status').annotate(count=Count('id')).order_by('status'))
    status_dict = dict(Ticket.STATUS_CHOICES)
    status_labels = [status_dict.get(row['status'], row['status']) for row in status_qs]
    status_data = [row['count'] for row in status_qs]

    # İlçe dağılımı (en çok talep gelen 15 ilçe)
    district_qs = list(Ticket.objects.values('district').annotate(count=Count('id')).order_by('-count')[:15])
    district_labels = [row['district'] for row in district_qs]
    district_data = [row['count'] for row in district_qs]

    # Kategori dağılımı (en çok talep gelen 10 kategori)
    category_qs = list(Ticket.objects.values('category__name').annotate(count=Count('id')).order_by('-count')[:10])
    category_labels = [row['category__name'] for row in category_qs]
    category_data = [row['count'] for row in category_qs]

    # Sektör bazlı canlı talep dağılımı (%) — geçmiş İBB verisiyle karşılaştırma
    sector_qs = list(Ticket.objects.values('category__sector').annotate(count=Count('id')))
    total_tickets = sum(row['count'] for row in sector_qs) or 1
    live_sector_pct = {row['category__sector']: round(row['count'] * 100 / total_tickets, 2) for row in sector_qs}

    historical_qs = list(
        SectoralStatistic.objects.filter(period_type='YEARLY')
        .values('sector').annotate(avg_pct=Avg('percentage'))
    )
    historical_sector_pct = {row['sector']: float(row['avg_pct']) for row in historical_qs}

    sector_codes = [code for code, _ in SECTOR_CHOICES if code != 'DIGER']
    sector_labels = [label for code, label in SECTOR_CHOICES if code != 'DIGER']
    live_sector_data = [live_sector_pct.get(code, 0) for code in sector_codes]
    historical_sector_data = [historical_sector_pct.get(code, 0) for code in sector_codes]

    # Aylık talep trendi
    trend_qs = list(
        Ticket.objects.annotate(month=TruncMonth('created_at'))
        .values('month').annotate(count=Count('id')).order_by('month')
    )
    trend_labels = [row['month'].strftime('%Y-%m') for row in trend_qs]
    trend_data = [row['count'] for row in trend_qs]

    # Birim performansı (Resolution kayıtlarına göre)
    unit_qs = list(Resolution.objects.values('assigned_unit').annotate(count=Count('id')).order_by('-count'))
    unit_dict = dict(UNIT_CHOICES)
    unit_labels = [unit_dict.get(row['assigned_unit'], row['assigned_unit']) for row in unit_qs]
    unit_data = [row['count'] for row in unit_qs]

    resolved_durations = Resolution.objects.filter(new_status='RESOLVED').annotate(
        duration=ExpressionWrapper(F('created_at') - F('ticket__created_at'), output_field=DurationField())
    ).aggregate(avg_duration=Avg('duration'))

    avg_duration = resolved_durations['avg_duration']
    avg_resolution_hours = round(avg_duration.total_seconds() / 3600, 1) if avg_duration else None

    recent_activity = Resolution.objects.select_related('ticket', 'handled_by').order_by('-created_at')[:5]

    context = {
        'total_tickets': Ticket.objects.count(),
        'pending_count': Ticket.objects.filter(status='PENDING').count(),
        'resolved_count': Ticket.objects.filter(status='RESOLVED').count(),
        'solution_center_count': SolutionCenter.objects.count(),

        'status_labels': json.dumps(status_labels, ensure_ascii=False),
        'status_data': json.dumps(status_data),

        'district_labels': json.dumps(district_labels, ensure_ascii=False),
        'district_data': json.dumps(district_data),

        'category_labels': json.dumps(category_labels, ensure_ascii=False),
        'category_data': json.dumps(category_data),

        'sector_labels': json.dumps(sector_labels, ensure_ascii=False),
        'live_sector_data': json.dumps(live_sector_data),
        'historical_sector_data': json.dumps(historical_sector_data),

        'trend_labels': json.dumps(trend_labels, ensure_ascii=False),
        'trend_data': json.dumps(trend_data),

        'unit_labels': json.dumps(unit_labels, ensure_ascii=False),
        'unit_data': json.dumps(unit_data),

        'avg_resolution_hours': avg_resolution_hours,
        'recent_activity': recent_activity,
    }
    return render(request, 'tickets/dashboard.html', context)


@login_required
def staff_panel(request):
    profile = getattr(request.user, 'staff_profile', None)

    if profile is None and not request.user.is_superuser:
        messages.error(request, "Hesabınıza tanımlı bir birim bulunamadı. Lütfen yöneticinizle iletişime geçin.")
        return redirect('tickets:home')

    tickets = Ticket.objects.all()
    if profile is not None:
        tickets = tickets.filter(current_unit=profile.unit)

    status_filter = request.GET.get('status')
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    tickets = tickets.select_related('category').order_by('-created_at')

    return render(request, 'tickets/staff_panel.html', {
        'tickets': tickets,
        'profile': profile,
        'status_choices': Ticket.STATUS_CHOICES,
        'selected_status': status_filter,
    })


@login_required
def staff_ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    profile = getattr(request.user, 'staff_profile', None)

    if profile is not None and ticket.current_unit != profile.unit and not request.user.is_superuser:
        messages.error(request, "Bu talep sizin biriminize ait değil.")
        return redirect('tickets:staff_panel')

    if request.method == 'POST':
        form = ResolutionForm(request.POST, request.FILES)
        if form.is_valid():
            resolution = form.save(commit=False)
            resolution.ticket = ticket
            resolution.handled_by = request.user
            resolution.assigned_unit = ticket.current_unit or 'DIGER'
            resolution.previous_status = ticket.status
            resolution.save()

            ticket.status = resolution.new_status
            ticket.save()

            notify_status_change(ticket, resolution)

            messages.success(request, "Talep durumu güncellendi.")
            return redirect('tickets:staff_ticket_detail', pk=ticket.pk)
    else:
        form = ResolutionForm(initial={'new_status': ticket.status})

    resolutions = ticket.resolutions.select_related('handled_by').order_by('-created_at')

    return render(request, 'tickets/staff_ticket_detail.html', {
        'ticket': ticket,
        'form': form,
        'resolutions': resolutions,
    })

def track(request):
    ticket = None
    searched = False

    if request.method == 'POST':
        searched = True
        search_type = request.POST.get('search_type', 'code')

        if search_type == 'phone':
            phone = request.POST.get('phone_number', '').strip()
            if phone:
                ticket = Ticket.objects.filter(phone=phone).select_related('category').prefetch_related('resolutions').order_by('-created_at').first()
        else:
            code = request.POST.get('tracking_code', '').strip().upper()
            if code:
                ticket = Ticket.objects.filter(tracking_code=code).select_related('category').prefetch_related('resolutions').first()

    return render(request, 'tickets/track.html', {
        'ticket': ticket,
        'searched': searched,
    })


def public_map(request):
    tickets = Ticket.objects.select_related('category').exclude(location__isnull=True)
    status_dict = dict(Ticket.STATUS_CHOICES)

    ticket_features = [
        {
            'tracking_code': t.tracking_code,
            'title': t.title,
            'district': t.district,
            'category': t.category.name,
            'status': t.status,
            'status_display': status_dict.get(t.status, t.status),
            'lat': t.location.y,
            'lng': t.location.x,
        }
        for t in tickets
    ]

    centers = SolutionCenter.objects.all()
    center_features = [
        {
            'name': c.name,
            'district': c.district,
            'address': c.address,
            'lat': c.location.y,
            'lng': c.location.x,
        }
        for c in centers
    ]

    return render(request, 'tickets/public_map.html', {
        'tickets_json': json.dumps(ticket_features, ensure_ascii=False),
        'centers_json': json.dumps(center_features, ensure_ascii=False),
        'ticket_count': len(ticket_features),
        'center_count': len(center_features),
    })


def ticket_list(request):
    tickets = Ticket.objects.select_related('category').order_by('-created_at')

    district = request.GET.get('district', '').strip()
    category_id = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')

    if district:
        tickets = tickets.filter(district__icontains=district)
    if category_id:
        tickets = tickets.filter(category_id=category_id)
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    paginator = Paginator(tickets, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'tickets/ticket_list.html', {
        'page_obj': page_obj,
        'categories': Category.objects.all(),
        'status_choices': Ticket.STATUS_CHOICES,
        'selected_district': district,
        'selected_category': category_id,
        'selected_status': status_filter,
    })
@require_GET
def nearby_tickets(request):
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'results': []})

    point = Point(lng, lat, srid=4326)

    nearby = (
        Ticket.objects.exclude(status__in=['RESOLVED', 'REJECTED'])
        .filter(location__distance_lte=(point, D(m=150), 'spheroid'))
        .annotate(distance=Distance('location', point, spheroid=True))
        .select_related('category')
        .order_by('distance')[:5]
    )

    results = [
        {
            'tracking_code': t.tracking_code,
            'title': t.title,
            'category': t.category.name,
            'status_display': t.get_status_display(),
            'support_count': t.support_count,
            'distance_m': round(t.distance.m),
        }
        for t in nearby
    ]

    return JsonResponse({'results': results})

@require_POST
def support_ticket(request, tracking_code):
    ticket = get_object_or_404(Ticket, tracking_code=tracking_code)

    supported = request.session.get('supported_tickets', [])
    if tracking_code in supported:
        return JsonResponse({'status': 'already_supported', 'support_count': ticket.support_count})

    ticket.support_count += 1
    ticket.save(update_fields=['support_count'])

    supported.append(tracking_code)
    request.session['supported_tickets'] = supported

    return JsonResponse({'status': 'ok', 'support_count': ticket.support_count})


@require_POST
def request_otp(request):
    phone = request.POST.get('phone', '').strip()
    if not phone or len(phone) < 10:
        return JsonResponse({'status': 'error', 'message': 'Geçerli bir telefon numarası girin.'}, status=400)

    recent = PhoneVerification.objects.filter(phone=phone).order_by('-created_at').first()
    if recent and (timezone.now() - recent.created_at) < timedelta(seconds=OTP_RESEND_SECONDS):
        wait = OTP_RESEND_SECONDS - int((timezone.now() - recent.created_at).total_seconds())
        return JsonResponse({'status': 'error', 'message': f'Lütfen {wait} saniye sonra tekrar deneyin.'}, status=429)

    code = generate_otp()
    PhoneVerification.objects.create(phone=phone, otp_code=code)
    send_otp_sms(phone, code)

    return JsonResponse({'status': 'ok', 'message': 'Doğrulama kodu gönderildi.'})


@require_POST
def verify_otp(request):
    phone = request.POST.get('phone', '').strip()
    code = request.POST.get('code', '').strip()

    verification = PhoneVerification.objects.filter(
        phone=phone, otp_code=code, is_verified=False
    ).order_by('-created_at').first()

    if not verification:
        return JsonResponse({'status': 'error', 'message': 'Kod geçersiz.'}, status=400)

    if (timezone.now() - verification.created_at) > timedelta(minutes=OTP_VALID_MINUTES):
        return JsonResponse({'status': 'error', 'message': 'Kodun süresi doldu, yeniden gönderin.'}, status=400)

    verification.is_verified = True
    verification.save(update_fields=['is_verified'])

    verified_phones = request.session.get('verified_phones', [])
    if phone not in verified_phones:
        verified_phones.append(phone)
    request.session['verified_phones'] = verified_phones

    return JsonResponse({'status': 'ok', 'message': 'Telefon doğrulandı.'})

def _get_manageable_categories(user):
    if user.is_superuser:
        return Category.objects.all()
    profile = getattr(user, 'staff_profile', None)
    if not profile:
        return Category.objects.none()
    return Category.objects.filter(default_unit=profile.unit)


@login_required
def form_builder_list(request):
    categories = _get_manageable_categories(request.user)
    return render(request, 'tickets/form_builder_list.html', {'categories': categories})


@login_required
def form_builder_edit(request, category_id):
    category = get_object_or_404(_get_manageable_categories(request.user), id=category_id)
    fields = category.dynamic_fields.all().order_by('order')
    logs = category.audit_logs.select_related('performed_by')[:15]
    return render(request, 'tickets/form_builder_edit.html', {'category': category, 'fields': fields, 'logs': logs})


@login_required
@require_POST
def form_field_create(request, category_id):
    category = get_object_or_404(_get_manageable_categories(request.user), id=category_id)
    label = request.POST.get('label', '').strip()
    field_type = request.POST.get('field_type', 'text')
    choices_text = request.POST.get('choices_text', '').strip()
    is_required = request.POST.get('is_required') == 'true'

    if not label:
        return JsonResponse({'status': 'error', 'message': 'Soru metni gerekli.'}, status=400)

    max_order = category.dynamic_fields.aggregate(m=Max('order'))['m'] or 0

    field = DynamicField.objects.create(
        category=category,
        label=label,
        field_type=field_type,
        choices_text=choices_text,
        is_required=is_required,
        order=max_order + 1,
    )
    FormFieldAuditLog.objects.create(
        category=category, field_label=field.label, action='CREATE', performed_by=request.user
    )

    return JsonResponse({
        'status': 'ok',
        'field': {
            'id': field.id,
            'label': field.label,
            'field_type': field.field_type,
            'field_type_display': field.get_field_type_display(),
            'choices_text': field.choices_text or '',
            'is_required': field.is_required,
        }
    })


@login_required
@require_POST
def form_field_update(request, field_id):
    field = get_object_or_404(DynamicField, id=field_id)
    if field.category not in _get_manageable_categories(request.user):
        return JsonResponse({'status': 'error', 'message': 'Yetkiniz yok.'}, status=403)

    field.label = request.POST.get('label', field.label).strip()
    field.field_type = request.POST.get('field_type', field.field_type)
    field.choices_text = request.POST.get('choices_text', '').strip()
    field.is_required = request.POST.get('is_required') == 'true'
    field.save()

    FormFieldAuditLog.objects.create(
        category=field.category, field_label=field.label, action='UPDATE', performed_by=request.user
    )

    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def form_field_delete(request, field_id):
    field = get_object_or_404(DynamicField, id=field_id)
    if field.category not in _get_manageable_categories(request.user):
        return JsonResponse({'status': 'error', 'message': 'Yetkiniz yok.'}, status=403)

    FormFieldAuditLog.objects.create(
        category=field.category, field_label=field.label, action='DELETE', performed_by=request.user
    )
    field.delete()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def form_field_reorder(request, category_id):
    category = get_object_or_404(_get_manageable_categories(request.user), id=category_id)
    order_list = request.POST.getlist('order[]')

    for index, field_id in enumerate(order_list):
        DynamicField.objects.filter(id=field_id, category=category).update(order=index)

    FormFieldAuditLog.objects.create(
        category=category, field_label='(sıralama değişti)', action='REORDER', performed_by=request.user
    )
    return JsonResponse({'status': 'ok'})


@login_required
def export_tickets_excel(request):
    user = request.user
    if user.is_superuser or user.is_staff:
        tickets = Ticket.objects.select_related('category').order_by('-created_at')
    else:
        profile = getattr(user, 'staff_profile', None)
        if not profile:
            return redirect('tickets:staff_panel')
        tickets = Ticket.objects.filter(current_unit=profile.unit).select_related('category').order_by('-created_at')

    buffer = build_tickets_excel(tickets)
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="talepler.xlsx"'
    return response


@staff_member_required
def export_dashboard_pdf(request):
    status_qs = list(Ticket.objects.values('status').annotate(count=Count('id')).order_by('status'))
    status_dict = dict(Ticket.STATUS_CHOICES)
    status_rows = [[status_dict.get(row['status'], row['status']), str(row['count'])] for row in status_qs]

    district_qs = list(Ticket.objects.values('district').annotate(count=Count('id')).order_by('-count')[:15])
    district_rows = [[row['district'], str(row['count'])] for row in district_qs]

    unit_qs = list(Resolution.objects.values('assigned_unit').annotate(count=Count('id')).order_by('-count'))
    unit_dict = dict(UNIT_CHOICES)
    unit_rows = [[unit_dict.get(row['assigned_unit'], row['assigned_unit']), str(row['count'])] for row in unit_qs]

    resolved_durations = Resolution.objects.filter(new_status='RESOLVED').annotate(
        duration=ExpressionWrapper(F('created_at') - F('ticket__created_at'), output_field=DurationField())
    ).aggregate(avg_duration=Avg('duration'))
    avg_duration = resolved_durations['avg_duration']
    avg_resolution_hours = round(avg_duration.total_seconds() / 3600, 1) if avg_duration else None

    context = {
        'generated_at': timezone.now().strftime('%d.%m.%Y %H:%M'),
        'total_tickets': Ticket.objects.count(),
        'pending_count': Ticket.objects.filter(status='PENDING').count(),
        'resolved_count': Ticket.objects.filter(status='RESOLVED').count(),
        'avg_resolution_hours': avg_resolution_hours,
        'status_rows': status_rows,
        'district_rows': district_rows,
        'unit_rows': unit_rows,
    }

    buffer = build_dashboard_pdf(context)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="yonetici-raporu.pdf"'
    return response


@login_required
def export_ticket_pdf(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    profile = getattr(request.user, 'staff_profile', None)

    if not request.user.is_superuser and profile and ticket.current_unit != profile.unit:
        messages.error(request, "Bu talebe erişim yetkiniz yok.")
        return redirect('tickets:staff_panel')

    resolutions = ticket.resolutions.select_related('handled_by').order_by('created_at')
    buffer = build_ticket_pdf(ticket, resolutions)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="talep-{ticket.tracking_code}.pdf"'
    return response