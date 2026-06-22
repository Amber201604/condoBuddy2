"""Notification service — push notifications via FCM/APNs."""
from typing import List

from app.config import get_settings

settings = get_settings()


async def send_push_notification(
    user_id: str,
    title: str,
    body: str,
    data: dict = None,
):
    """Send push notification via FCM. Placeholder — implement with pyfcm or firebase-admin."""
    # TODO: Integrate with Firebase Cloud Messaging
    print(f"[PUSH] To {user_id}: {title} — {body}")
    return {"success": True}


async def send_bulk_push(
    user_ids: List[str],
    title: str,
    body: str,
    data: dict = None,
):
    """Send push to multiple users."""
    for uid in user_ids:
        await send_push_notification(uid, title, body, data)
    return {"success": True, "count": len(user_ids)}
