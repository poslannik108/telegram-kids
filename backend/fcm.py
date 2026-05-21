"""
FCM push-уведомления для детского приложения.
Используется вместо WebSocket — сервер stateless.
"""

import os
import logging
import json

logger = logging.getLogger(__name__)

_fcm_app = None


def init_fcm():
    """Инициализирует Firebase Admin SDK. Вызывать один раз при старте."""
    global _fcm_app
    creds_path = os.getenv("FIREBASE_CREDENTIALS", "firebase-credentials.json")
    creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON", "")

    try:
        import firebase_admin
        from firebase_admin import credentials

        if creds_json:
            cred = credentials.Certificate(json.loads(creds_json))
        elif os.path.exists(creds_path):
            cred = credentials.Certificate(creds_path)
        else:
            logger.warning("Firebase credentials not found — push notifications disabled")
            return False

        _fcm_app = firebase_admin.initialize_app(cred)
        logger.info("✅ Firebase Admin SDK initialized")
        return True
    except Exception as e:
        logger.error(f"Firebase init failed: {e}")
        return False


def send_decision(fcm_token: str, request_id: str, status: str) -> bool:
    """
    Отправляет data message ребёнку с решением родителя.
    Data message — тихий push, приложение обрабатывает его само
    (работает и в foreground, и в background).
    """
    if not _fcm_app or not fcm_token:
        return False
    try:
        from firebase_admin import messaging
        message = messaging.Message(
            data={
                "type": "request_decision",
                "request_id": request_id,
                "status": status,          # "approved" | "rejected" | "blocked"
            },
            android=messaging.AndroidConfig(priority="high"),
            token=fcm_token,
        )
        messaging.send(message)
        logger.info(f"FCM sent: request={request_id} status={status}")
        return True
    except Exception as e:
        logger.error(f"FCM send failed: {e}")
        return False


def send_link_code(fcm_token: str, code: str) -> bool:
    """Отправляет код привязки ребёнку (на этапе регистрации)."""
    if not _fcm_app or not fcm_token:
        return False
    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(
                title="Код подтверждения",
                body=f"Ваш код: {code}",
            ),
            data={"type": "link_code", "code": code},
            android=messaging.AndroidConfig(priority="high"),
            token=fcm_token,
        )
        messaging.send(message)
        return True
    except Exception as e:
        logger.error(f"FCM link_code failed: {e}")
        return False
