from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Ticket, Resolution, SolutionCenter, SectoralStatistic
from .serializers import (
    CategorySerializer, TicketSerializer, ResolutionSerializer,
    SolutionCenterSerializer, SectoralStatisticSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class SolutionCenterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SolutionCenter.objects.all()
    serializer_class = SolutionCenterSerializer
    permission_classes = [permissions.AllowAny]


class SectoralStatisticViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SectoralStatistic.objects.all()
    serializer_class = SectoralStatisticSerializer
    permission_classes = [permissions.AllowAny]


class TicketViewSet(viewsets.ModelViewSet):
    """
    - Herkes yeni talep oluşturabilir (create).
    - Takip kodu ile tekil sorgulama herkese açık (retrieve, lookup_field=tracking_code).
    - Tüm listeyi görmek ve düzenlemek sadece giriş yapmış personel/yöneticiye açık,
      ve personel sadece kendi biriminin taleplerini görür.
    """
    serializer_class = TicketSerializer
    lookup_field = 'tracking_code'
    lookup_value_regex = '[^/]+'

    def get_permissions(self):
        if self.action in ['create', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Ticket.objects.select_related('category').all()
        user = self.request.user

        if self.action in ['create', 'retrieve']:
            return qs

        if not user.is_authenticated:
            return qs.none()

        if user.is_superuser or user.is_staff:
            return qs

        profile = getattr(user, 'staff_profile', None)
        if profile:
            return qs.filter(current_unit=profile.unit)

        return qs.none()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_resolution(self, request, tracking_code=None):
        """Personelin bir talebe çözüm/iş kaydı eklemesi ve durumu güncellemesi için özel endpoint."""
        ticket = self.get_object()
        profile = getattr(request.user, 'staff_profile', None)

        if not request.user.is_superuser and profile and ticket.current_unit != profile.unit:
            return Response({'detail': 'Bu talep sizin biriminize ait değil.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolution = serializer.save(
            ticket=ticket,
            handled_by=request.user,
            assigned_unit=ticket.current_unit or 'DIGER',
            previous_status=ticket.status,
        )

        ticket.status = resolution.new_status
        ticket.save()

        return Response(ResolutionSerializer(resolution).data, status=status.HTTP_201_CREATED)