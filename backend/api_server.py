"""
FamilyGuard API Server
REST API для мобильного приложения ребёнка
Запускается вместе с основным backend
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
import os
import uuid
from datetime import datetime
import main as backend
from telethon import TelegramClient
from telethon.sessions import StringSession

# Персистентные Telethon-клиенты: user_id (str) -> TelegramClient
_child_clients: dict[str, TelegramClient] = {}

app = FastAPI(title="FamilyGuard API")

API_SECRET = os.getenv("API_SECRET", "change_this_secret_key")
API_ID = int(os.getenv("API_ID", "12345678"))
API_HASH = os.getenv("API_HASH", "your_api_hash_here")

# Временные Telethon-клиенты для процесса логина (phone -> {client, phone_code_hash})
_auth_sessions: dict = {}


def verify_token(x_api_key: str = Header(...)):
    if x_api_key != API_SECRET and not backend.db.get_setting(f"token_{x_api_key}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def get_child_client(x_api_key: str) -> tuple[TelegramClient, str]:
    """
    Возвращает (TelegramClient, user_id) для аутентифицированного ребёнка.
    Переиспользует открытое соединение; пересоздаёт если сессия упала.
    """
    user_id = backend.db.get_setting(f"token_{x_api_key}")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    client = _child_clients.get(user_id)
    if client is None or not client.is_connected():
        session_str = backend.db.get_setting(f"session_{user_id}")
        if not session_str:
            raise HTTPException(status_code=401, detail="Session not found. Re-login required.")
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            raise HTTPException(status_code=401, detail="Session expired. Re-login required.")
        _child_clients[user_id] = client

    return client, user_id


# ============================================================
# МОДЕЛИ
# ============================================================

class JoinChatRequest(BaseModel):
    chat_identifier: str  # @username или ссылка-приглашение


class BotRequest(BaseModel):
    bot_username: str


class SendMessageRequest(BaseModel):
    chat_id: int
    text: str


class PhoneRequest(BaseModel):
    phone: str


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str
    phone_code_hash: str


# ============================================================
# ЭНДПОИНТЫ
# ============================================================

@app.get("/health")
async def health():
    return {"status": "ok", "service": "FamilyGuard"}


DECISION_TIMEOUT = 600  # 10 минут


async def _wait_for_decision(event: asyncio.Event, request: Request, request_id: str) -> str:
    """
    Ждёт события от родителя.
    Возвращает 'ok' | 'disconnected' | 'timeout'.
    Очищает pending_events в любом исходе.
    """
    loop = asyncio.get_event_loop()
    deadline = loop.time() + DECISION_TIMEOUT
    try:
        while not event.is_set():
            if await request.is_disconnected():
                return "disconnected"
            if loop.time() >= deadline:
                backend.db.update_request_status(request_id, "timeout")
                return "timeout"
            await asyncio.sleep(0.3)
        return "ok"
    finally:
        backend.pending_events.pop(request_id, None)


@app.post("/join-chat")
async def join_chat(req: JoinChatRequest, request: Request, x_api_key: str = Header(...)):
    """Запрос на вступление в чат. Ждёт решения родителя без polling."""
    verify_token(x_api_key)
    _, user_id = await get_child_client(x_api_key)
    child = backend.db.get_child_by_telegram_id(user_id)
    if not child:
        raise HTTPException(404, "Child not found")

    if backend.db.is_blocked("chat", req.chat_identifier, child_id=child["id"]):
        return {"allowed": False, "reason": "blocked"}

    parent = backend.db.get_parent_by_id(child["parent_id"])
    request_id = f"join_{child['id']}_{int(datetime.now().timestamp())}"
    backend.db.save_pending_request(request_id, {
        "type": "join_chat", "chat_name": req.chat_identifier,
        "chat_identifier": req.chat_identifier, "status": "pending",
    }, child_id=child["id"])

    event = asyncio.Event()
    backend.pending_events[request_id] = event
    if backend.parent_app:
        await backend.notify_parent_join_request(
            backend.parent_app, parent["telegram_id"], request_id, req.chat_identifier
        )

    reason = await _wait_for_decision(event, request, request_id)
    if reason in ("disconnected", "timeout"):
        return {"allowed": False, "reason": reason}
    result = backend.db.get_pending_request(request_id)
    return {"allowed": result["status"] == "approved", "reason": result["status"]}


@app.post("/use-bot")
async def use_bot(req: BotRequest, request: Request, x_api_key: str = Header(...)):
    """Запрос на использование бота. Ждёт решения родителя без polling."""
    verify_token(x_api_key)
    _, user_id = await get_child_client(x_api_key)
    child = backend.db.get_child_by_telegram_id(user_id)
    if not child:
        raise HTTPException(404, "Child not found")

    if backend.db.is_blocked("bot", req.bot_username, child_id=child["id"]):
        return {"allowed": False, "reason": "blocked"}

    parent = backend.db.get_parent_by_id(child["parent_id"])
    request_id = f"bot_{child['id']}_{int(datetime.now().timestamp())}"
    backend.db.save_pending_request(request_id, {
        "type": "use_bot", "bot_name": req.bot_username,
        "bot_username": req.bot_username, "status": "pending",
    }, child_id=child["id"])

    event = asyncio.Event()
    backend.pending_events[request_id] = event
    if backend.parent_app:
        await backend.notify_parent_bot_request(
            backend.parent_app, parent["telegram_id"], request_id,
            req.bot_username, req.bot_username
        )

    reason = await _wait_for_decision(event, request, request_id)
    if reason in ("disconnected", "timeout"):
        return {"allowed": False, "reason": reason}
    result = backend.db.get_pending_request(request_id)
    return {"allowed": result["status"] == "approved", "reason": result["status"]}


@app.get("/dialogs")
async def get_dialogs(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    client, user_id = await get_child_client(x_api_key)
    child = backend.db.get_child_by_telegram_id(user_id)
    child_id = child["id"] if child else None
    dialogs = await client.get_dialogs(limit=50)
    result = []
    for d in dialogs:
        entity = d.entity
        is_bl = backend.db.is_blocked("chat", str(entity.id), child_id=child_id)
        result.append({
            "id": entity.id,
            "name": d.name,
            "unread_count": d.unread_count,
            "is_blocked": is_bl,
            "type": "bot" if getattr(entity, "bot", False) else "chat",
        })
    return result


@app.get("/messages/{chat_id}")
async def get_messages(chat_id: int, limit: int = 30, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    client, user_id = await get_child_client(x_api_key)
    child = backend.db.get_child_by_telegram_id(user_id)
    child_id = child["id"] if child else None
    if backend.db.is_blocked("chat", str(chat_id), child_id=child_id):
        raise HTTPException(status_code=403, detail="Chat is blocked")
    messages = await client.get_messages(chat_id, limit=limit)
    return [
        {"id": m.id, "text": m.text or "", "date": m.date.isoformat(),
         "out": m.out, "sender_id": m.sender_id}
        for m in messages
    ]


@app.post("/send-message")
async def send_message(req: SendMessageRequest, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    client, user_id = await get_child_client(x_api_key)
    child = backend.db.get_child_by_telegram_id(user_id)
    child_id = child["id"] if child else None
    if backend.db.is_blocked("chat", str(req.chat_id), child_id=child_id):
        raise HTTPException(status_code=403, detail="Chat is blocked")
    await client.send_message(req.chat_id, req.text)
    return {"success": True}


@app.get("/blocked")
async def get_blocked(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    _, user_id = await get_child_client(x_api_key)
    child = backend.db.get_child_by_telegram_id(user_id)
    child_id = child["id"] if child else None
    return backend.db.get_all_blocked(child_id=child_id)


# ============================================================
# АВТОРИЗАЦИЯ РЕБЁНКА
# ============================================================

@app.post("/auth/request-code")
async def auth_request_code(req: PhoneRequest, request: Request, x_api_key: str = Header(...)):
    """Шаг 1: отправить код подтверждения на Telegram по номеру телефона"""
    verify_token(x_api_key)

    # Лимит: 3 запроса с одного IP за 10 минут
    ip = request.client.host
    allowed, retry_after = backend.db.rate_check(f"otp_req:{ip}", max_attempts=3, window_seconds=600)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Слишком много запросов. Повторите через {retry_after} сек."
        )

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        result = await client.send_code_request(req.phone)
    except Exception as e:
        await client.disconnect()
        raise HTTPException(status_code=400, detail=str(e))
    _auth_sessions[req.phone] = {
        "client": client,
        "phone_code_hash": result.phone_code_hash,
    }
    return {"phone_code_hash": result.phone_code_hash}


@app.post("/auth/verify-code")
async def auth_verify_code(req: VerifyCodeRequest, x_api_key: str = Header(...)):
    """Шаг 2: подтвердить код, выдать токен сессии"""
    verify_token(x_api_key)

    # Проверяем блокировку (5 неверных попыток → блок 30 мин)
    rl_key = f"otp_ver:{req.phone}"
    is_blocked, retry_after = backend.db.rate_is_blocked(rl_key)
    if is_blocked:
        raise HTTPException(
            status_code=429,
            detail=f"Слишком много неверных попыток. Повторите через {retry_after // 60} мин."
        )

    session_data = _auth_sessions.get(req.phone)
    if not session_data:
        raise HTTPException(status_code=400, detail="Сначала запросите код повторно")
    client = session_data["client"]
    try:
        user = await client.sign_in(
            req.phone, req.code, phone_code_hash=req.phone_code_hash
        )
    except Exception as e:
        # Неверный код — засчитываем попытку
        blocked, retry_after = backend.db.rate_fail(rl_key, max_attempts=5, block_seconds=1800)
        detail = str(e)
        if blocked:
            detail = f"Слишком много неверных попыток. Повторите через {retry_after // 60} мин."
        raise HTTPException(status_code=400, detail=detail)

    # Успех — сбрасываем счётчик попыток
    backend.db.rate_reset(rl_key)

    session_string = client.session.save()
    token = str(uuid.uuid4())

    backend.db.set_setting(f"token_{token}", str(user.id))
    backend.db.set_setting(f"session_{user.id}", session_string)
    backend.db.set_setting(f"phone_{user.id}", req.phone)
    # Связка телефон → telegram_id нужна боту для нахождения ребёнка при нажатии «Готово»
    backend.db.set_setting(f"phone_to_tg_{req.phone}", str(user.id))

    await client.disconnect()
    del _auth_sessions[req.phone]

    child = backend.db.get_child_by_telegram_id(str(user.id))
    is_linked = child is not None and child["is_linked"]
    return {"token": token, "user_id": str(user.id), "is_linked": is_linked}


@app.get("/auth/status")
async def auth_status(x_api_key: str = Header(...)):
    """Проверить, привязал ли родитель этого ребёнка"""
    verify_token(x_api_key)
    user_id = backend.db.get_setting(f"token_{x_api_key}")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    child = backend.db.get_child_by_telegram_id(user_id)
    is_linked = child is not None and child["is_linked"]
    return {"is_linked": is_linked}


@app.get("/contacts")
async def get_contacts(x_api_key: str = Header(...)):
    """Список контактов ребёнка"""
    verify_token(x_api_key)
    from telethon.tl.functions.contacts import GetContactsRequest
    client, _ = await get_child_client(x_api_key)
    result = await client(GetContactsRequest(hash=0))
    contacts = []
    for user in result.users:
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        contacts.append({
            "id": user.id,
            "name": name or "Без имени",
            "username": user.username or "",
            "phone": user.phone or "",
        })
    return contacts


# ============================================================
# ПОДТВЕРЖДЕНИЕ EMAIL (открывается из письма)
# ============================================================

@app.get("/verify-email/{token}", response_class=HTMLResponse)
async def verify_email(token: str):
    result = backend.db.verify_email_token(token)

    if not result:
        return HTMLResponse("""
        <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#17212b;color:#fff">
        <h2>❌ Ссылка недействительна или истекла</h2>
        <p>Вернитесь в бот и запросите новое письмо.</p>
        </body></html>
        """, status_code=400)

    parent = result["parent"]
    child  = result["child"]

    # Второй opt-in завершён — помечаем согласие как подтверждённое
    backend.db.confirm_policy_consent(parent["id"])

    # Отправляем родителю сообщение в бот с инструкцией по установке приложения
    if backend.parent_app:
        try:
            await backend.cb_email_confirmed_from_web(
                chat_id=int(parent["telegram_id"]),
                child=child,
                app=backend.parent_app,
            )
        except Exception as e:
            pass

    backend.db.log_registration_event(
        "email_confirmed_doi", parent_id=parent["id"], child_id=child["id"]
    )

    return HTMLResponse(f"""
    <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#17212b;color:#fff">
    <h2>✅ Email подтверждён!</h2>
    <p>Вернитесь в бот <b>Telegram Kids</b> — там уже появилась инструкция по установке приложения.</p>
    </body></html>
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
