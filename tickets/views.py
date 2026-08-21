from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Avg, F, DurationField, ExpressionWrapper
from django.db.models.functions import TruncMonth
import json

from .models import Ticket, Category, Resolution, SolutionCenter, SectoralStatistic, SECTOR_CHOICES, UNIT_CHOICES
from .forms import TicketForm, ResolutionForm, TrackingForm

UNIT_ICONS = {
    'FEN_ISLERI': 'bi-cone-striped',
    'TEMIZLIK': 'bi-trash3-fill',
    'PARK_BAHCE': 'bi-tree-fill',
    'SU_KANAL': 'bi-droplet-fill',
    'ZABITA': 'bi-shield-check',
    'DIGER': 'bi-three-dots',
}


def home(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save()
            messages.success(request, f"Talebiniz alındı! Takip Kodunuz: {ticket.tracking_code}")
            return redirect('tickets:ticket_success', tracking_code=ticket.tracking_code)
    else:
        form = TicketForm()

    quick_categories = [
        {'id': c.id, 'name': c.name, 'icon': UNIT_ICONS.get(c.default_unit, 'bi-three-dots')}
        for c in Category.objects.all()[:8]
    ]

    return render(request, 'tickets/home.html', {'form': form, 'quick_categories': quick_categories})

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
        form = TrackingForm(request.POST)
        searched = True
        if form.is_valid():
            code = form.cleaned_data['tracking_code'].strip().upper()
            ticket = Ticket.objects.filter(tracking_code=code).select_related('category').prefetch_related('resolutions').first()
    else:
        form = TrackingForm()

    return render(request, 'tickets/track.html', {
        'form': form,
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