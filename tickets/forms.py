from django import forms
from django.contrib.gis.geos import Point
from .models import Resolution, Ticket

class TicketForm(forms.ModelForm):
    latitude = forms.FloatField(widget=forms.HiddenInput(attrs={'id': 'id_latitude'}))
    longitude = forms.FloatField(widget=forms.HiddenInput(attrs={'id': 'id_longitude'}))

    class Meta:
        model = Ticket
        fields = [
            'title', 'category', 'district', 'neighborhood',
            'description', 'image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Örn: Çukur Sokak Aydınlatma Arızası'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'İlçe'}),
            'neighborhood': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mahalle'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Sorunu detaylıca açıklayınız...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = True
        self.fields['image'].error_messages = {
            'required': 'Lütfen sorunu gösteren bir fotoğraf ekleyin.'
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        lat = self.cleaned_data.get('latitude')
        lng = self.cleaned_data.get('longitude')

        if lat is not None and lng is not None:
            instance.location = Point(lng, lat, srid=4326)

        if commit:
            instance.save()
        return instance

    def save(self, commit=True):
        instance = super().save(commit=False)
        lat = self.cleaned_data.get('latitude')
        lng = self.cleaned_data.get('longitude')
        
        # Enlem ve boylamı GIS Point nesnesine dönüştürüyoruz (lng, lat sırasında olmalı)
        if lat is not None and lng is not None:
            instance.location = Point(lng, lat, srid=4326)
            
        if commit:
            instance.save()
        return instance


class ResolutionForm(forms.ModelForm):
    class Meta:
        model = Resolution
        fields = ['note', 'resolution_image', 'new_status']
        widgets = {
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Saha notunuzu yazın...'}),
            'resolution_image': forms.FileInput(attrs={'class': 'form-control'}),
            'new_status': forms.Select(attrs={'class': 'form-select'}),
        }

class TrackingForm(forms.Form):
    tracking_code = forms.CharField(
        max_length=12,
        label="Takip Kodu",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'BEY-XXXXXX'})
    )