from django.contrib.gis.db import models as gis_models
from django.db import models
import uuid


SECTOR_CHOICES = [
    ('ULASIM', 'Ulaşım'),
    ('CEVRE_KENT_TOPLUM', 'Çevre, Kent ve Toplum Düzeni'),
    ('ISKI', 'İSKİ'),
    ('IGDAS', 'İGDAŞ'),
    ('SAGLIK_SOSYAL', 'Sağlık ve Sosyal Destek'),
    ('IMAR_ALTYAPI', 'İmar ve Altyapı Faaliyetleri'),
    ('DIGER', 'Diğer'),
]

UNIT_CHOICES = [
    ('FEN_ISLERI', 'Fen İşleri'),
    ('TEMIZLIK', 'Temizlik İşleri'),
    ('PARK_BAHCE', 'Park ve Bahçeler'),
    ('SU_KANAL', 'Su ve Kanalizasyon'),
    ('ZABITA', 'Zabıta'),
    ('DIGER', 'Diğer'),
]

STATUS_CHOICES = [
    ('PENDING', 'Beklemede'),
    ('IN_PROGRESS', 'İnceleniyor'),
    ('RESOLVED', 'Çözüldü'),
    ('REJECTED', 'Reddedildi'),
]

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    sector = models.CharField(
        max_length=30,
        choices=SECTOR_CHOICES,
        default='DIGER',
        verbose_name="İBB Sektörü",
        help_text="Dashboard'da İBB açık veri istatistikleriyle karşılaştırma için kullanılır."
    )
    default_unit = models.CharField(
        max_length=30,
        choices=UNIT_CHOICES,
        default='DIGER',
        verbose_name="Sorumlu Birim",
        help_text="Bu kategoride açılan talepler otomatik olarak bu birime düşer."
    )

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"

    def __str__(self):
        return self.name


class Ticket(models.Model):
    STATUS_CHOICES = STATUS_CHOICES

    tracking_code = models.CharField(max_length=12, unique=True, editable=False, verbose_name="Takip Kodu")
    title = models.CharField(max_length=200, verbose_name="Başlık / Konu")
    description = models.TextField(verbose_name="Açıklama / Detay")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='tickets', verbose_name="Kategori")

    district = models.CharField(max_length=100, verbose_name="İlçe")
    neighborhood = models.CharField(max_length=100, blank=True, null=True, verbose_name="Mahalle")

    location = gis_models.PointField(verbose_name="Konum", srid=4326)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Durum")
    current_unit = models.CharField(
        max_length=30,
        choices=UNIT_CHOICES,
        blank=True,
        null=True,
        verbose_name="Atanan Birim"
    )
    image = models.ImageField(upload_to='ticket_images/', blank=True, null=True, verbose_name="Fotoğraf")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        verbose_name = "Talep / Şikayet"
        verbose_name_plural = "Talepler / Şikayetler"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.tracking_code:
            self.tracking_code = f"BEY-{uuid.uuid4().hex[:6].upper()}"
        if is_new and not self.current_unit and self.category_id:
            self.current_unit = self.category.default_unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_code} - {self.title}"


class Resolution(models.Model):
    """Saha personelinin bir talebi çözerken bıraktığı iş kaydı / güncelleme geçmişi"""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='resolutions', verbose_name="İlgili Talep")
    assigned_unit = models.CharField(max_length=30, choices=UNIT_CHOICES, verbose_name="Atanan Birim")
    handled_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_resolutions', verbose_name="İşlemi Yapan Personel"
    )
    note = models.TextField(blank=True, null=True, verbose_name="Saha Notu / Açıklama")
    resolution_image = models.ImageField(upload_to='resolution_images/', blank=True, null=True, verbose_name="Çözüm Sonrası Fotoğraf")
    previous_status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True, verbose_name="Önceki Durum")
    new_status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Yeni Durum")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Kayıt Tarihi")

    class Meta:
        verbose_name = "Çözüm / İş Kaydı"
        verbose_name_plural = "Çözüm / İş Kayıtları"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket.tracking_code} → {self.get_new_status_display()} ({self.assigned_unit})"

class SolutionCenter(models.Model):
    """İBB'nin fiziksel 153 Çözüm Noktaları — vatandaş haritasında referans olarak gösterilir"""

    name = models.CharField(max_length=150, verbose_name="Birim Adı")
    address = models.TextField(verbose_name="Adres")
    address_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Adres Tarifi")
    neighborhood = models.CharField(max_length=100, verbose_name="Mahalle")
    district = models.CharField(max_length=100, verbose_name="İlçe")
    location = gis_models.PointField(verbose_name="Konum", srid=4326)

    class Meta:
        verbose_name = "Çözüm Noktası"
        verbose_name_plural = "Çözüm Noktaları"
        ordering = ['district', 'name']

    def __str__(self):
        return f"{self.name} ({self.district})"


class SectoralStatistic(models.Model):
    """İBB Açık Veri Portalı'ndan alınan geçmiş sektörel şikayet yüzde dağılımı (dashboard karşılaştırması için)"""

    PERIOD_CHOICES = [
        ('YEARLY', 'Yıllık'),
        ('MONTHLY', 'Aylık'),
    ]

    year = models.PositiveIntegerField(verbose_name="Yıl")
    month = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Ay")
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES, verbose_name="Periyot Tipi")
    sector = models.CharField(max_length=30, choices=SECTOR_CHOICES, verbose_name="Sektör")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Yüzde (%)")

    class Meta:
        verbose_name = "Sektörel İstatistik"
        verbose_name_plural = "Sektörel İstatistikler"
        unique_together = ('year', 'month', 'period_type', 'sector')
        ordering = ['year', 'month']

    def __str__(self):
        period = f"{self.year}/{self.month}" if self.month else str(self.year)
        return f"{period} - {self.get_sector_display()}: %{self.percentage}"


class StaffProfile(models.Model):
    """Personelin hangi birimde çalıştığını belirler — panel erişimini bu alana göre filtreleriz"""

    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='staff_profile', verbose_name="Kullanıcı")
    unit = models.CharField(max_length=30, choices=UNIT_CHOICES, verbose_name="Çalıştığı Birim")

    class Meta:
        verbose_name = "Personel Profili"
        verbose_name_plural = "Personel Profilleri"

    def __str__(self):
        return f"{self.user.username} - {self.get_unit_display()}"