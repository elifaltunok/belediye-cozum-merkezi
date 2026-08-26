from .emails import send_status_notification
from .sms import send_status_sms


def notify_status_change(ticket, resolution):
    if resolution.new_status not in ['IN_PROGRESS', 'RESOLVED']:
        return

    send_status_notification(ticket, resolution)
    send_status_sms(ticket, resolution)