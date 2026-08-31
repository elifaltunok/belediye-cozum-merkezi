from django.contrib.gis.forms.widgets import OSMWidget


class MapTilerWidget(OSMWidget):
    template_name = 'gis/custom_maptiler.html'
    default_lon = 28.9784
    default_lat = 41.0082
    default_zoom = 10