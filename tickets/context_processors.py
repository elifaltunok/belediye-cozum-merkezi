from django.conf import settings


def maptiler_key(request):
    return {'MAPTILER_API_KEY': settings.MAPTILER_API_KEY}