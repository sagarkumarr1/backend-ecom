"""
orders/tasks.py
Order email notifications.
Celery nahi hai toh directly send karo — same function.
Celery hai toh @shared_task decorator uncomment karo.
"""
from django.core.mail import send_mail
from django.conf import settings


# ── Uncomment if using Celery ──────────────────────────────────────────────
# from celery import shared_task
# @shared_task

def send_order_email(email, order_id, event):
    """
    event: 'placed' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled' | 'refunded'
    """
    messages = {
        'placed': {
            'subject': f"Order Placed — {order_id}",
            'body':    f"Aapka order {order_id} place ho gaya hai! Payment ke baad confirm hoga.",
        },
        'confirmed': {
            'subject': f"Order Confirmed — {order_id}",
            'body':    f"Order {order_id} confirm ho gaya! Hum jald pack karenge.",
        },
        'processing': {
            'subject': f"Order Processing — {order_id}",
            'body':    f"Order {order_id} pack ho raha hai. Jald ship hoga.",
        },
        'shipped': {
            'subject': f"Order Shipped — {order_id}",
            'body':    f"Order {order_id} dispatch ho gaya! 3-5 din mein pahunch jayega.",
        },
        'delivered': {
            'subject': f"Order Delivered — {order_id}",
            'body':    f"Order {order_id} deliver ho gaya! Review zaroor likhein.",
        },
        'cancelled': {
            'subject': f"Order Cancelled — {order_id}",
            'body':    f"Order {order_id} cancel ho gaya. Refund 5-7 din mein aayega.",
        },
        'refunded': {
            'subject': f"Refund Processed — {order_id}",
            'body':    f"Order {order_id} ka refund process ho gaya!",
        },
    }

    msg = messages.get(event, {
        'subject': f"Order Update — {order_id}",
        'body':    f"Aapke order {order_id} mein update aaya hai.",
    })

    try:
        send_mail(
            msg['subject'],
            msg['body'],
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"[ORDER EMAIL ERROR] {e}")
