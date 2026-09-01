from django.core.mail import send_mail
from django.conf import settings

STATUS_EMAIL_SUBJECTS = {
    'IN_PROGRESS': 'Talebiniz İnceleniyor',
    'RESOLVED': 'Talebiniz Çözüldü',
}


def send_status_notification(ticket, resolution):
    if not ticket.email:
        return

    subject_text = STATUS_EMAIL_SUBJECTS.get(resolution.new_status)
    if not subject_text:
        return

    message = (
        f"Sayın vatandaşımız,\n\n"
        f'"{ticket.title}" başlıklı talebinizin (Takip Kodu: {ticket.tracking_code}) durumu güncellendi.\n\n'
        f"Yeni Durum: {ticket.get_status_display()}\n"
    )

    if resolution.note:
        message += f"\nPersonel Notu: {resolution.note}\n"

    message += (
        f"\nTalebinizi şu adresten takip edebilirsiniz:\n"
        f"{settings.SITE_URL}/takip/\n\n"
        f"Akıllı Kent Sahada"
    )

    if resolution.new_status == 'RESOLVED':
        message += f"\nDeneyiminizi değerlendirmek için: {settings.SITE_URL}/degerlendir/{ticket.tracking_code}/\n"

    send_mail(
        subject=f"[Akıllı Kent Sahada] {subject_text} — {ticket.tracking_code}",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[ticket.email],
        fail_silently=True,
    )