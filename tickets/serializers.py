from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Category, Ticket, Resolution, SolutionCenter, SectoralStatistic


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'sector', 'default_unit']


class TicketSerializer(GeoFeatureModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Ticket
        geo_field = 'location'
        fields = [
            'id', 'tracking_code', 'title', 'description', 'category', 'category_name',
            'district', 'neighborhood', 'status', 'current_unit', 'image',
            'created_at', 'updated_at', 'location',
        ]
        read_only_fields = ['tracking_code', 'status', 'current_unit', 'created_at', 'updated_at']


class ResolutionSerializer(serializers.ModelSerializer):
    handled_by_username = serializers.CharField(source='handled_by.username', read_only=True)

    class Meta:
        model = Resolution
        fields = [
            'id', 'ticket', 'assigned_unit', 'handled_by', 'handled_by_username',
            'note', 'resolution_image', 'previous_status', 'new_status', 'created_at',
        ]
        read_only_fields = ['assigned_unit', 'handled_by', 'previous_status', 'created_at']


class SolutionCenterSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = SolutionCenter
        geo_field = 'location'
        fields = ['id', 'name', 'address', 'address_description', 'neighborhood', 'district', 'location']


class SectoralStatisticSerializer(serializers.ModelSerializer):
    sector_display = serializers.CharField(source='get_sector_display', read_only=True)

    class Meta:
        model = SectoralStatistic
        fields = ['id', 'year', 'month', 'period_type', 'sector', 'sector_display', 'percentage']