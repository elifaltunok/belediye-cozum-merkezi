import pandas as pd
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.conf import settings
from tickets.models import SolutionCenter, SectoralStatistic

TURKISH_MONTHS = {
    'OCAK': 1, 'ŞUBAT': 2, 'MART': 3, 'NİSAN': 4,
    'MAYIS': 5, 'HAZİRAN': 6, 'TEMMUZ': 7, 'AĞUSTOS': 8,
    'EYLÜL': 9, 'EKİM': 10, 'KASIM': 11, 'ARALIK': 12,
}


def parse_month(value):
    """Ay değerini hem sayı hem Türkçe isim olarak kabul eder."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().upper()
    return TURKISH_MONTHS.get(text)

# İstanbul için makul koordinat sınırları — bozuk veriyi elemek için
LAT_MIN, LAT_MAX = 40.5, 41.6
LNG_MIN, LNG_MAX = 27.5, 29.8

SECTOR_COLUMN_MAP = {
    'ULAŞIM_YÜZDE': 'ULASIM',
    'ÇEVRE,KENT VE TOPLUM DÜZENİ_YUZDE': 'CEVRE_KENT_TOPLUM',
    'İSKİ_YÜZDE': 'ISKI',
    'İGDAŞ_YÜZDE': 'IGDAS',
    'SAĞLIK VE SOSYAL DESTEK_YÜZDE': 'SAGLIK_SOSYAL',
    'İMAR VE ALTYAPI FAALİYETLERİ_YÜZDE': 'IMAR_ALTYAPI',
}


class Command(BaseCommand):
    help = "İBB Açık Veri Portalı xlsx dosyalarını (153 Çözüm Noktaları ve sektörel istatistikler) veritabanına aktarır."

    def handle(self, *args, **options):
        data_dir = settings.BASE_DIR / 'data'

        self.import_solution_centers(data_dir / '153-konumlar.xlsx')
        self.import_yearly_stats(data_dir / '2022-2023sektorel-dalm-153_2_.xlsx')
        self.import_monthly_stats(data_dir / 'sektorel-dalma-gore-cozum-merkezi-istatistikleri.xlsx')

        self.stdout.write(self.style.SUCCESS('İBB verileri başarıyla içe aktarıldı.'))

    def import_solution_centers(self, path):
        if not path.exists():
            self.stdout.write(self.style.WARNING(f'Dosya bulunamadı, atlanıyor: {path}'))
            return

        df = pd.read_excel(path)
        created, skipped = 0, 0

        for _, row in df.iterrows():
            lat = row['ENLEM']
            lng = row['BOYLAM']

            if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
                self.stdout.write(self.style.WARNING(
                    f"Geçersiz koordinat, atlandı: {row['BİRİM ADI']} (lat={lat}, lng={lng})"
                ))
                skipped += 1
                continue

            SolutionCenter.objects.update_or_create(
                name=row['BİRİM ADI'].strip(),
                defaults={
                    'address': row['ADRES'],
                    'address_description': row.get('ADRES TARİFİ'),
                    'neighborhood': str(row['MAHALLE ']).strip() if pd.notna(row['MAHALLE ']) else '',
                    'district': str(row['İLÇE ']).strip() if pd.notna(row['İLÇE ']) else '',
                    'location': Point(lng, lat, srid=4326),
                }
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Çözüm Noktaları: {created} kayıt işlendi, {skipped} atlandı.'))

    def import_yearly_stats(self, path):
        if not path.exists():
            self.stdout.write(self.style.WARNING(f'Dosya bulunamadı, atlanıyor: {path}'))
            return

        df = pd.read_excel(path)
        count = 0

        for _, row in df.iterrows():
            year = int(row['YIL'])
            for col, sector_code in SECTOR_COLUMN_MAP.items():
                if col in row and pd.notna(row[col]):
                    SectoralStatistic.objects.update_or_create(
                        year=year, month=None, period_type='YEARLY', sector=sector_code,
                        defaults={'percentage': float(row[col])}
                    )
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'Yıllık sektörel istatistik: {count} kayıt işlendi.'))

    def import_monthly_stats(self, path):
        if not path.exists():
            self.stdout.write(self.style.WARNING(f'Dosya bulunamadı, atlanıyor: {path}'))
            return

        df = pd.read_excel(path)
        count = 0

        for _, row in df.iterrows():
            year = int(row['YIL'])
            month = parse_month(row.get('AY'))
            for col, sector_code in SECTOR_COLUMN_MAP.items():
                if col in row and pd.notna(row[col]):
                    SectoralStatistic.objects.update_or_create(
                        year=year, month=month, period_type='MONTHLY', sector=sector_code,
                        defaults={'percentage': float(row[col])}
                    )
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'Aylık sektörel istatistik: {count} kayıt işlendi.'))