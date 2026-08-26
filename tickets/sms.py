import random
from django.conf import settings


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_sms(phone, code):
    backend = getattr(settings, 'SMS_BACKEND', 'console')
    message = f"Akıllı Kent Sahada doğrulama kodunuz: {code}"

    if backend == 'console':
        print(f"\n{'=' * 50}\nSMS (TEST MODU) -> {phone}\n{message}\n{'=' * 50}\n")
        return True

    print(f"[UYARI] SMS_BACKEND='{backend}' henüz tanımlı değil, mesaj gönderilmedi.")
    return False

STATUS_SMS_TEMPLATES = {
    'IN_PROGRESS': 'Sayın vatandaşımız, {code} takip kodlu talebiniz inceleniyor.',
    'RESOLVED': 'Sayın vatandaşımız, {code} takip kodlu talebiniz çözüldü. Detay: {url}',
}


def send_status_sms(ticket, resolution):
    if not ticket.phone:
        return

    template = STATUS_SMS_TEMPLATES.get(resolution.new_status)
    if not template:
        return

    url = f"{settings.SITE_URL}/cozum/{ticket.tracking_code}/"
    message = template.format(code=ticket.tracking_code, url=url)

    backend = getattr(settings, 'SMS_BACKEND', 'console')
    if backend == 'console':
        print(f"\n{'=' * 50}\nSMS (TEST MODU) -> {ticket.phone}\n{message}\n{'=' * 50}\n")
        return True

    print(f"[UYARI] SMS_BACKEND='{backend}' henüz tanımlı değil, mesaj gönderilmedi.")
    return False