from rest_framework.routers import DefaultRouter
from .api_views import (
    CategoryViewSet, TicketViewSet, SolutionCenterViewSet, SectoralStatisticViewSet,
)

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='api-category')
router.register('tickets', TicketViewSet, basename='api-ticket')
router.register('solution-centers', SolutionCenterViewSet, basename='api-solution-center')
router.register('sectoral-statistics', SectoralStatisticViewSet, basename='api-sectoral-statistic')

urlpatterns = router.urls