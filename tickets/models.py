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

UNIT_TARGET_HOURS = {
    'FEN_ISLERI': 48,
    'TEMIZLIK': 24,
    'PARK_BAHCE': 72,
    'SU_KANAL': 24,
    'ZABITA': 24,
    'DIGER': 72,
}

STATUS_CHOICES = [
    ('PENDING', 'Beklemede'),
    ('IN_PROGRESS', 'İnceleniyor'),
    ('RESOLVED', 'Çözüldü'),
    ('REJECTED', 'Reddedildi'),
]

class Category(models.Model):
    """	Şikayet kategorileri (Kaldırım, Çöp vb.) — her biri bir İBB sektörüne (sector) ve bir sorumlu birime (default_unit) bağlı"""
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
    """	Ana talep/şikayet kaydı — PointField (GeoDjango) ile coğrafi konum, otomatik takip kodu, otomatik birim ataması"""
    STATUS_CHOICES = STATUS_CHOICES

    tracking_code = models.CharField(max_length=12, unique=True, editable=False, verbose_name="Takip Kodu")
    title = models.CharField(max_length=200, verbose_name="Başlık / Konu")
    description = models.TextField(verbose_name="Açıklama / Detay")
    email = models.EmailField(blank=True, null=True, verbose_name="E-posta (bildirim için)")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon Numarası (Doğrulanmış)")
    support_count = models.PositiveIntegerField(default=1, verbose_name="Destek Sayısı")
    citizen_rating = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Vatandaş Puanı (1-5)")
    citizen_feedback = models.TextField(blank=True, null=True, verbose_name="Vatandaş Geri Bildirimi")
    rating_submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Puanlama Tarihi")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='tickets', verbose_name="Kategori")

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

    def get_priority_level(self):
        if self.support_count >= 10:
            return 'HIGH'
        elif self.support_count >= 4:
            return 'MEDIUM'
        return 'LOW'

    def get_priority_display_info(self):
        levels = {
            'HIGH': {'label': 'Yüksek Öncelik', 'color': 'danger', 'icon': 'bi-exclamation-triangle-fill'},
            'MEDIUM': {'label': 'Orta Öncelik', 'color': 'warning', 'icon': 'bi-exclamation-circle-fill'},
            'LOW': {'label': 'Normal', 'color': 'secondary', 'icon': 'bi-dash-circle'},
        }
        return levels[self.get_priority_level()]

    def __str__(self):
        return f"{self.tracking_code} - {self.title}"


class Resolution(models.Model):
    """Personelin her durum güncellemesinde bıraktığı iş kaydı — önceki/yeni durum, saha notu, çözüm fotoğrafı, işlemi yapan kullanıcı"""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='resolutions', verbose_name="İlgili Talep")
    assigned_unit = models.CharField(max_length=30, choices=UNIT_CHOICES, verbose_name="Atanan Birim")
    handled_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_resolutions', verbose_name="İşlemi Yapan Personel"
    )
    note = models.TextField(blank=True, null=True, verbose_name="Saha Notu / Açıklama")
    internal_note = models.TextField(blank=True, null=True, verbose_name="İç Not (Sadece Personel Görür)")
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
    is_content_editor = models.BooleanField(default=False, verbose_name="Makale Yazma Yetkisi")

    class Meta:
        verbose_name = "Personel Profili"
        verbose_name_plural = "Personel Profilleri"

    def __str__(self):
        return f"{self.user.username} - {self.get_unit_display()}"

class PhoneVerification(models.Model):
    phone = models.CharField(max_length=20, verbose_name="Telefon Numarası")
    otp_code = models.CharField(max_length=6, verbose_name="Doğrulama Kodu")
    is_verified = models.BooleanField(default=False, verbose_name="Doğrulandı mı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    class Meta:
        verbose_name = "Telefon Doğrulama"
        verbose_name_plural = "Telefon Doğrulamaları"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone} - {'Doğrulandı' if self.is_verified else 'Bekliyor'}"


class FormFieldAuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Oluşturuldu'),
        ('UPDATE', 'Güncellendi'),
        ('DELETE', 'Silindi'),
        ('REORDER', 'Sıralandı'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='audit_logs', verbose_name="Kategori")
    field_label = models.CharField(max_length=200, verbose_name="Alan/Soru")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="İşlem")
    performed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name="İşlemi Yapan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Form Değişiklik Kaydı"
        verbose_name_plural = "Form Değişiklik Kayıtları"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.performed_by} — {self.get_action_display()} — {self.field_label}"


class DynamicField(models.Model):
    FIELD_TYPES = [
        ('text', 'Kısa Metin'),
        ('textarea', 'Uzun Metin'),
        ('number', 'Sayı'),
        ('date', 'Tarih'),
        ('choice', 'Seçenekli (Tek Seçim)'),
        ('boolean', 'Evet / Hayır'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='dynamic_fields', verbose_name="Kategori")
    label = models.CharField(max_length=200, verbose_name="Soru / Etiket")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text', verbose_name="Alan Tipi")
    choices_text = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="Seçenekler (virgülle ayırın)",
        help_text="Sadece 'Seçenekli' tipi için geçerlidir. Örn: Evet, Hayır, Bilmiyorum"
    )
    is_required = models.BooleanField(default=True, verbose_name="Zorunlu mu")
    order = models.PositiveIntegerField(default=0, verbose_name="Sıra")

    class Meta:
        verbose_name = "Dinamik Form Alanı"
        verbose_name_plural = "Dinamik Form Alanları"
        ordering = ['category', 'order']

    def __str__(self):
        return f"{self.category.name} — {self.label}"

    def get_choices_list(self):
        if not self.choices_text:
            return []
        return [c.strip() for c in self.choices_text.split(',') if c.strip()]


class DynamicFieldResponse(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='dynamic_responses', verbose_name="Talep")
    field = models.ForeignKey(DynamicField, on_delete=models.CASCADE, related_name='responses', verbose_name="Alan")
    value = models.TextField(blank=True, verbose_name="Cevap")

    class Meta:
        verbose_name = "Dinamik Alan Cevabı"
        verbose_name_plural = "Dinamik Alan Cevapları"

    def __str__(self):
        return f"{self.field.label}: {self.value}"


class TicketSupport(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='supporters', verbose_name="Talep")
    ip_address = models.GenericIPAddressField(verbose_name="IP Adresi")
    session_key = models.CharField(max_length=40, verbose_name="Oturum Anahtarı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Talep Desteği"
        verbose_name_plural = "Talep Destekleri"
        unique_together = ('ticket', 'ip_address', 'session_key')

    def __str__(self):
        return f"{self.ticket.tracking_code} — {self.ip_address}"


class TicketComment(models.Model):
    AUTHOR_CHOICES = [
        ('CITIZEN', 'Vatandaş'),
        ('STAFF', 'Personel'),
    ]

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments', verbose_name="Talep")
    author_type = models.CharField(max_length=10, choices=AUTHOR_CHOICES, verbose_name="Yazan")
    staff_user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Personel (varsa)")
    message = models.TextField(verbose_name="Mesaj")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Talep Yorumu"
        verbose_name_plural = "Talep Yorumları"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.ticket.tracking_code} - {self.get_author_type_display()}"


class UnitSLA(models.Model):
    unit = models.CharField(max_length=30, choices=UNIT_CHOICES, unique=True, verbose_name="Birim")
    target_hours = models.PositiveIntegerField(verbose_name="Hedef Çözüm Süresi (Saat)")

    class Meta:
        verbose_name = "Birim Hedef Süresi (SLA)"
        verbose_name_plural = "Birim Hedef Süreleri (SLA)"

    def __str__(self):
        return f"{self.get_unit_display()} — {self.target_hours} saat"

    @classmethod
    def get_target_hours(cls, unit):
        sla = cls.objects.filter(unit=unit).first()
        if sla:
            return sla.target_hours
        return UNIT_TARGET_HOURS.get(unit, 72)
    

class Article(models.Model):
    title = models.CharField(max_length=200, verbose_name="Başlık")
    slug = models.SlugField(max_length=220, unique=True, verbose_name="URL Kısaltması")
    summary = models.CharField(max_length=300, verbose_name="Kısa Özet")
    content = models.TextField(verbose_name="İçerik")
    cover_image = models.ImageField(upload_to='article_images/', blank=True, null=True, verbose_name="Kapak Görseli")
    author = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name="Yazar")
    is_published = models.BooleanField(default=True, verbose_name="Yayında mı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        verbose_name = "Bilgilendirme Makalesi"
        verbose_name_plural = "Bilgilendirme Makaleleri"
        ordering = ['-created_at']

    def __str__(self):
        return self.title