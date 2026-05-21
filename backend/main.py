"""
Telegram Kids — бот родителя
Регистрация, привязка детей, уведомления, разрешения.
"""

import asyncio
import logging
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import aiosmtplib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters,
)
from db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN   = os.getenv("BOT_TOKEN", "your_bot_token_here")
SMTP_HOST   = os.getenv("SMTP_HOST", "smtp.yandex.ru")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER   = os.getenv("SMTP_USER", "noreply@telegram-kids.ru")
SMTP_PASS   = os.getenv("SMTP_PASS", "your_smtp_password")
SMTP_FROM   = os.getenv("SMTP_FROM", "Telegram Kids <noreply@telegram-kids.ru>")
SERVER_URL  = os.getenv("SERVER_URL", "https://telegram-kids.ru")

PRIVACY_POLICY_URL = f"{SERVER_URL}/privacy"
APP_ANDROID_URL    = "https://play.google.com/store/apps/details?id=ru.telegramkids"
APP_IOS_URL        = "https://apps.apple.com/app/telegram-kids/id0000000000"

db = Database()
parent_app: Application = None       # инициализируется в build_app(), используется из api_server
pending_events: dict = {}            # request_id -> asyncio.Event, сигнализирует /join-chat и /use-bot

# ============================================================
# СОСТОЯНИЯ ДИАЛОГА РЕГИСТРАЦИИ
# ============================================================

(
    STATE_CHILD_NAME,
    STATE_CHILD_BIRTH,
    STATE_RELATIONSHIP,
    STATE_RELATIONSHIP_OTHER,
    STATE_CHILD_PHONE,
    STATE_PARENT_NAME,
    STATE_PARENT_EMAIL,
    STATE_POLICY_CONFIRM,
    STATE_EMAIL_VERIFY,
    STATE_AWAITING_READY,
    STATE_LINK_CODE,
) = range(11)

RELATIONSHIP_MAIN = ["Мама", "Папа", "Другой"]
RELATIONSHIP_OTHER = ["Мама", "Папа", "Отчим", "Мачеха", "Бабушка", "Дедушка", "Друг", "Опекун"]

PRIVACY_POLICY_TEXT = """📄 *Политика конфиденциальности*

Настоящая Политика конфиденциальности разработана в соответствии с Федеральным законом № 152-ФЗ «О персональных данных».

*1. Оператор*
ИП / ООО «Telegram Kids», сайт: telegram-kids.ru

*2. Цель обработки*
Предоставление услуги родительского контроля в Telegram.

*3. Состав персональных данных*
— Telegram ID, имя, e-mail родителя
— Имя, дата рождения, номер телефона и Telegram ID ребёнка

*4. Правовое основание*
Обработка осуществляется на основании согласия субъекта персональных данных (ст. 9 152-ФЗ).

*5. Срок хранения*
Данные хранятся до удаления аккаунта либо до отзыва согласия.

*6. Права субъекта*
Вы вправе получить доступ к своим данным, потребовать их исправления или удаления, а также отозвать согласие, направив запрос на info@telegram-kids.ru.

*7. Передача третьим лицам*
Данные не передаются третьим лицам, за исключением случаев, предусмотренных законодательством РФ.

Полный текст: [telegram-kids.ru/privacy](https://telegram-kids.ru/privacy)"""


# ============================================================
# EMAIL
# ============================================================

async def send_verification_email(to_email: str, parent_name: str, verify_url: str):
    msg = MIMEMultipart("alternative")
    msg["From"]    = SMTP_FROM
    msg["To"]      = to_email
    msg["Subject"] = "Подтвердите согласие — Telegram Kids"

    text_body = (
        f"Здравствуйте, {parent_name}!\n\n"
        f"Для подтверждения вашего согласия с Политикой конфиденциальности перейдите по ссылке:\n"
        f"{verify_url}\n\n"
        f"Ссылка действительна 24 часа.\n\n"
        f"С уважением,\nКоманда Telegram Kids"
    )
    html_body = (
        f"<p>Здравствуйте, <b>{parent_name}</b>!</p>"
        f"<p>Для подтверждения вашего согласия с Политикой конфиденциальности нажмите кнопку:</p>"
        f'<p><a href="{verify_url}" style="background:#5288c1;color:#fff;padding:12px 24px;'
        f'border-radius:8px;text-decoration:none;font-size:16px;">✅ Подтвердить</a></p>'
        f"<p>Или перейдите по ссылке:<br><a href=\"{verify_url}\">{verify_url}</a></p>"
        f"<p>Ссылка действительна 24 часа.</p>"
        f"<p>С уважением,<br>Команда Telegram Kids</p>"
    )
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASS,
        use_tls=True,
    )


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def kb(buttons: list[list[tuple]]) -> InlineKeyboardMarkup:
    """Shortcut для создания клавиатуры. buttons = [[(text, data), ...], ...]"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t, callback_data=d) for t, d in row]
        for row in buttons
    ])


def kb_reply(labels: list[str], cols: int = 2) -> InlineKeyboardMarkup:
    """Раскладывает список строк в клавиатуру по cols колонок."""
    rows = []
    for i in range(0, len(labels), cols):
        rows.append([
            InlineKeyboardButton(label, callback_data=f"pick_{label}")
            for label in labels[i:i + cols]
        ])
    return InlineKeyboardMarkup(rows)


def consent_message(ctx_data: dict) -> str:
    parent = ctx_data.get("parent", {})
    child_name = ctx_data.get("child_name", "")
    child_birth = ctx_data.get("child_birth", "")
    child_phone = ctx_data.get("child_phone", "")
    relationship = ctx_data.get("relationship", "")
    telegram_id = ctx_data.get("parent_telegram_id", "")

    return (
        f"{PRIVACY_POLICY_TEXT}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Для завершения нам необходимо ваше согласие на хранение и обработку персональных данных.\n\n"
        f"*Ваши данные:* {parent.get('name', '—')}, Telegram ID {telegram_id}, "
        f"степень родства: {relationship}\n"
        f"*Данные ребёнка:* Имя: {child_name}, Дата рождения: {child_birth}, "
        f"Номер телефона: {child_phone}\n"
        f"*Цель обработки:* предоставление услуги по родительскому контролю в Telegram.\n"
        f"*Срок действия согласия:* до удаления аккаунта.\n\n"
        f"Нажимая кнопку «Согласен», вы подтверждаете, что ознакомлены с условиями "
        f"и даёте согласие на хранение и обработку вышеуказанных данных."
    )


# ============================================================
# КОМАНДА /start
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.effective_user.id)
    parent = db.get_parent_by_telegram_id(tg_id)

    if parent:
        children = db.get_children(parent["id"])
        count = len(children)
        linked = sum(1 for c in children if c["is_linked"])
        text = (
            f"👨‍👩‍👧 *Telegram Kids*\n\n"
            f"Детей подключено: {linked}/{count}\n\n"
            f"Что хотите сделать?"
        )
        keyboard = kb([
            [("➕ Добавить ребёнка", "add_child"), ("👧 Мои дети", "my_children")],
        ])
    else:
        text = (
            "👨‍👩‍👧 *Telegram Kids* — родительский контроль\n\n"
            "Здесь вы можете подключить детей к родительскому контролю "
            "и следить за их безопасностью в Telegram."
        )
        keyboard = kb([[("➕ Добавить ребёнка", "add_child")]])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ============================================================
# НАЧАЛО РЕГИСТРАЦИИ РЕБЁНКА
# ============================================================

async def cb_add_child(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)

    parent = db.get_or_create_parent(tg_id)
    context.user_data["parent"] = parent
    context.user_data["parent_telegram_id"] = tg_id
    context.user_data["is_first_child"] = len(db.get_children(parent["id"])) == 0

    await query.edit_message_text(
        "Введите *имя ребёнка*:",
        parse_mode="Markdown"
    )
    return STATE_CHILD_NAME


async def state_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Пожалуйста, введите имя.")
        return STATE_CHILD_NAME

    context.user_data["child_name"] = name
    await update.message.reply_text(
        f"Имя: *{name}*\n\nВведите *дату рождения* ребёнка (например, 15.03.2015):",
        parse_mode="Markdown"
    )
    return STATE_CHILD_BIRTH


async def state_child_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birth = update.message.text.strip()
    context.user_data["child_birth"] = birth
    child_name = context.user_data["child_name"]

    await update.message.reply_text(
        f"Дата рождения: *{birth}*\n\nКто вы для *{child_name}*?",
        parse_mode="Markdown",
        reply_markup=kb_reply(RELATIONSHIP_MAIN, cols=3)
    )
    return STATE_RELATIONSHIP


async def state_relationship(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    picked = query.data.replace("pick_", "")

    if picked == "Другой":
        await query.edit_message_text(
            "Выберите вашу роль:",
            reply_markup=kb_reply(RELATIONSHIP_OTHER, cols=2)
        )
        return STATE_RELATIONSHIP_OTHER

    context.user_data["relationship"] = picked
    child_name = context.user_data["child_name"]
    await query.edit_message_text(
        f"Роль: *{picked}*\n\nВведите *номер телефона* {child_name} "
        f"(к которому привязан Telegram-аккаунт ребёнка):",
        parse_mode="Markdown"
    )
    return STATE_CHILD_PHONE


async def state_relationship_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    picked = query.data.replace("pick_", "")

    context.user_data["relationship"] = picked
    child_name = context.user_data["child_name"]
    await query.edit_message_text(
        f"Роль: *{picked}*\n\nВведите *номер телефона* {child_name} "
        f"(к которому привязан Telegram-аккаунт ребёнка):",
        parse_mode="Markdown"
    )
    return STATE_CHILD_PHONE


async def state_child_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    context.user_data["child_phone"] = phone

    if context.user_data.get("is_first_child"):
        parent = context.user_data["parent"]
        if not parent.get("name"):
            await update.message.reply_text(
                "Номер сохранён.\n\nТак как это первый ребёнок, введите *ваше имя*:",
                parse_mode="Markdown"
            )
            return STATE_PARENT_NAME
        if not parent.get("email"):
            # Имя уже есть (повторный вход), но email пропущен — собираем только его
            await update.message.reply_text(
                "Номер сохранён.\n\nВведите ваш *e-mail* для подтверждения согласия:",
                parse_mode="Markdown"
            )
            return STATE_PARENT_EMAIL

    return await _show_policy(update.message, context)


async def state_parent_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    tg_id = context.user_data["parent_telegram_id"]
    db.update_parent(tg_id, name=name)
    context.user_data["parent"]["name"] = name

    await update.message.reply_text(
        f"Имя сохранено: *{name}*\n\nВведите ваш *e-mail*:",
        parse_mode="Markdown"
    )
    return STATE_PARENT_EMAIL


async def state_parent_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    tg_id = context.user_data["parent_telegram_id"]
    db.update_parent(tg_id, email=email)
    context.user_data["parent"]["email"] = email

    return await _show_policy(update.message, context)


async def _show_policy(msg, context: ContextTypes.DEFAULT_TYPE):
    text = consent_message(context.user_data)
    keyboard = kb([[("✅ Согласен", "policy_agree"), ("❌ Не согласен", "policy_decline")]])
    await msg.reply_text(text, parse_mode="Markdown", reply_markup=keyboard,
                         disable_web_page_preview=True)
    return STATE_POLICY_CONFIRM


# ============================================================
# ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ
# ============================================================

async def cb_policy_agree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tg_id = context.user_data["parent_telegram_id"]
    parent = db.get_parent_by_telegram_id(tg_id)
    child_name = context.user_data["child_name"]

    # Сохраняем запись о согласии
    policy = db.get_current_policy()
    if policy:
        db.save_policy_consent(
            parent_id=parent["id"],
            policy_version_id=policy["id"],
            consent_text=consent_message(context.user_data)
        )

    # Сохраняем ребёнка в БД
    child_id = db.add_child(
        parent_id=parent["id"],
        name=context.user_data["child_name"],
        birth_date=context.user_data["child_birth"],
        phone=context.user_data["child_phone"],
        relationship=context.user_data["relationship"],
    )
    context.user_data["child_id"] = child_id

    db.log_registration_event(
        "child_added", parent_id=parent["id"], child_id=child_id,
        details=f"name={child_name}, phone={context.user_data['child_phone']}"
    )

    # Rate-лимиты проверяем ДО создания токена, чтобы не инвалидировать рабочую ссылку
    email = parent.get("email", "")
    today = datetime.now().strftime("%Y-%m-%d")
    cd_ok, cd_wait   = db.rate_check(f"email_cd:{email}",          max_attempts=1, window_seconds=60)
    day_ok, day_wait = db.rate_check(f"email_day:{email}:{today}", max_attempts=5, window_seconds=86400)

    if not cd_ok:
        await query.edit_message_text(
            f"⏳ Письмо уже отправлено. Повторная отправка возможна через {cd_wait} сек.",
            parse_mode="Markdown",
            reply_markup=kb([[("🔄 Я уже подтвердил", "check_email_verify")]])
        )
        return STATE_EMAIL_VERIFY
    if not day_ok:
        await query.edit_message_text(
            "⛔ Превышен дневной лимит отправки писем (5 в сутки). Попробуйте завтра или свяжитесь с поддержкой.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    # Создаём токен только если лимиты пройдены
    token = db.create_email_token(parent["id"], child_id)
    verify_url = f"{SERVER_URL}/verify-email/{token}"
    email_sent = False

    try:
        await send_verification_email(email, parent.get("name") or "Пользователь", verify_url)
        email_sent = True
        db.log_registration_event(
            "email_sent", parent_id=parent["id"], child_id=child_id,
            details=f"to={email}"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")
        db.log_registration_event(
            "email_send_failed", parent_id=parent["id"], child_id=child_id,
            details=f"to={email} error={e}"
        )
        email_sent = False

    if email_sent:
        text = (
            f"✅ Согласие зафиксировано.\n\n"
            f"Для подтверждения вашего согласия, пожалуйста, перейдите по ссылке, "
            f"которая была отправлена Вам на *{email}*, и нажмите «Подтвердить».\n\n"
            f"После этого возвращайтесь сюда."
        )
        keyboard = kb([[("🔄 Я уже подтвердил", "check_email_verify")]])
    else:
        # Если письмо не ушло — даём прямую ссылку
        text = (
            f"✅ Согласие зафиксировано.\n\n"
            f"⚠️ Не удалось отправить письмо на {email}. "
            f"Подтвердите согласие по ссылке:\n{verify_url}"
        )
        keyboard = kb([[("🔄 Я уже подтвердил", "check_email_verify")]])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return STATE_EMAIL_VERIFY


async def cb_check_email_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Родитель нажимает «Я уже подтвердил» — проверяем статус в БД."""
    query = update.callback_query

    child_id = context.user_data.get("child_id")
    if not child_id:
        await query.answer()
        await query.edit_message_text("Ошибка: начните заново с /start.")
        return ConversationHandler.END

    tg_id = context.user_data["parent_telegram_id"]
    parent = db.get_parent_by_telegram_id(tg_id)
    child = db.get_child_by_id(child_id)
    is_verified = db.is_email_token_verified(parent["id"], child_id)

    if is_verified:
        await query.answer()
        await _show_install_instructions(query, child, edit=True)
        return STATE_AWAITING_READY
    else:
        # show_alert=True — единственный вызов answer для этого запроса
        await query.answer(
            "Письмо ещё не подтверждено. Проверьте папку «Спам».", show_alert=True
        )
        return STATE_EMAIL_VERIFY


async def cb_email_confirmed_from_web(chat_id: int, child: dict, app):
    """Вызывается из api_server после перехода по ссылке в письме."""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Готово", callback_data="child_ready")
    ]])
    await app.bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ Email подтверждён!\n\n"
            f"Установите приложение на телефон *{child['name']}* "
            f"и авторизуйте его по номеру {child['phone']}.\n\n"
            f"После авторизации вернитесь сюда и нажмите *«Готово»*.\n\n"
            f"📲 Скачать приложение:\n"
            f"• [Google Play]({APP_ANDROID_URL})\n"
            f"• [App Store]({APP_IOS_URL})"
        ),
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def _show_install_instructions(query_or_msg, child: dict, edit: bool = False):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Готово", callback_data="child_ready")
    ]])
    text = (
        f"✅ Email подтверждён!\n\n"
        f"Установите приложение на телефон *{child['name']}* "
        f"и авторизуйте его по номеру {child['phone']}.\n\n"
        f"После авторизации вернитесь сюда и нажмите *«Готово»*.\n\n"
        f"📲 Скачать приложение:\n"
        f"• [Google Play]({APP_ANDROID_URL})\n"
        f"• [App Store]({APP_IOS_URL})"
    )
    if edit:
        await query_or_msg.edit_message_text(
            text, parse_mode="Markdown", reply_markup=keyboard,
            disable_web_page_preview=True
        )
    else:
        await query_or_msg.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard,
            disable_web_page_preview=True
        )


async def cb_policy_decline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = context.user_data.get("parent_telegram_id", "")
    parent = db.get_parent_by_telegram_id(tg_id)
    if parent:
        db.log_registration_event("policy_declined", parent_id=parent["id"])
    await query.edit_message_text(
        "Без согласия с политикой конфиденциальности регистрация невозможна.\n"
        "Нажмите /start чтобы начать заново."
    )
    return ConversationHandler.END


# ============================================================
# КНОПКА «ГОТОВО» → ОТПРАВКА КОДА РЕБЁНКУ
# ============================================================

async def cb_child_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tg_id = str(query.from_user.id)

    # Кулдаун 2 минуты между нажатиями «Готово» — защита от спама кодами ребёнку
    allowed, retry_after = db.rate_check(f"link_gen:{tg_id}", max_attempts=1, window_seconds=120)
    if not allowed:
        await query.answer(
            f"Подождите {retry_after} сек. перед повторной отправкой кода.",
            show_alert=True
        )
        return  # остаёмся в текущем состоянии

    await query.answer()

    child_id = context.user_data.get("child_id")
    child = db.get_child_by_id(child_id)
    if not child:
        await query.edit_message_text("Ошибка: ребёнок не найден. Начните заново с /start.")
        return ConversationHandler.END

    # Ищем Telegram-аккаунт ребёнка по номеру телефона
    child_tg_id = db.get_setting(f"phone_to_tg_{child['phone']}")
    if not child_tg_id:
        await query.edit_message_text(
            f"⚠️ Аккаунт *{child['name']}* ещё не авторизован в приложении.\n\n"
            f"Убедитесь, что {child['name']} установил приложение и вошёл по номеру "
            f"{child['phone']}, затем нажмите «Готово» снова.",
            parse_mode="Markdown",
            reply_markup=kb([[("✅ Готово", "child_ready")]])
        )
        return STATE_AWAITING_READY

    # Генерируем код привязки
    code = db.create_linking_code(child_id)
    db.set_child_telegram_id(child_id, child_tg_id)

    # Отправляем код ребёнку через бота
    await context.application.bot.send_message(
        chat_id=int(child_tg_id),
        text=f"🔑 Код для подтверждения: *{code}*\n\nПодождите, пока родитель введёт его.",
        parse_mode="Markdown"
    )

    db.log_registration_event(
        "link_code_sent", parent_id=context.user_data["parent"]["id"],
        child_id=child_id, details=f"child_tg_id={child_tg_id}"
    )

    await query.edit_message_text(
        f"Код отправлен {child['name']}.\n\nВведите код, который видит *{child['name']}* в своём приложении:",
        parse_mode="Markdown"
    )
    return STATE_LINK_CODE


# ============================================================
# ВВОД КОДА ПРИВЯЗКИ
# ============================================================

async def state_link_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    child_id = context.user_data.get("child_id")
    rl_key = f"link_ver:{child_id}"

    # Проверяем блокировку (5 неверных попыток → блок 30 мин)
    is_blocked, retry_after = db.rate_is_blocked(rl_key)
    if is_blocked:
        await update.message.reply_text(
            f"⛔ Слишком много неверных попыток. Попробуйте через {retry_after // 60} мин."
        )
        return STATE_LINK_CODE

    child = db.verify_linking_code(code)

    if not child:
        blocked, retry_after = db.rate_fail(rl_key, max_attempts=5, block_seconds=1800)
        if blocked:
            await update.message.reply_text(
                f"⛔ Слишком много неверных попыток. Попробуйте через {retry_after // 60} мин."
            )
        else:
            await update.message.reply_text(
                "❌ Неверный или просроченный код. Нажмите «Готово» чтобы отправить новый код.",
                reply_markup=kb([[("✅ Готово", "child_ready")]])
            )
        return STATE_LINK_CODE

    # Успех — сбрасываем счётчик
    db.rate_reset(rl_key)
    db.link_child(child["id"])

    # Уведомляем ребёнка о завершении привязки
    if child.get("telegram_id"):
        await context.application.bot.send_message(
            chat_id=int(child["telegram_id"]),
            text="✅ Твой аккаунт успешно подключён к родительскому контролю. Приложение готово к работе!"
        )

    parent = db.get_parent_by_telegram_id(context.user_data["parent_telegram_id"])
    db.log_registration_event(
        "child_linked", parent_id=parent["id"], child_id=child["id"]
    )

    await update.message.reply_text(
        f"✅ Аккаунт *{child['name']}* успешно добавлен к вашему контролю.",
        parse_mode="Markdown",
        reply_markup=kb([[("👧 Мои дети", "my_children"), ("➕ Ещё ребёнка", "add_child")]])
    )
    context.user_data.clear()
    return ConversationHandler.END


# ============================================================
# СПИСОК ДЕТЕЙ
# ============================================================

async def cb_my_children(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    parent = db.get_parent_by_telegram_id(tg_id)
    if not parent:
        await query.edit_message_text("Нет подключённых детей. Нажмите /start.")
        return

    children = db.get_children(parent["id"])
    if not children:
        await query.edit_message_text(
            "Детей пока нет.",
            reply_markup=kb([[("➕ Добавить ребёнка", "add_child")]])
        )
        return

    text = "👧 *Ваши дети:*\n\n"
    for c in children:
        status = "✅ Привязан" if c["is_linked"] else "⏳ Ожидает привязки"
        text += f"• *{c['name']}* ({c['relationship']}) — {status}\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=kb([[("➕ Добавить ребёнка", "add_child")]])
    )


# ============================================================
# ОТМЕНА
# ============================================================

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Отменено. Нажмите /start чтобы начать заново."
    )
    return ConversationHandler.END


# ============================================================
# УВЕДОМЛЕНИЯ РОДИТЕЛЮ
# ============================================================

async def notify_parent_join_request(app, parent_tg_id: str, request_id: str, chat_name: str):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Разрешить", callback_data=f"approve_{request_id}"),
            InlineKeyboardButton("❌ Запретить", callback_data=f"reject_{request_id}"),
        ],
        [InlineKeyboardButton("🚫 Всегда блокировать", callback_data=f"block_{request_id}")]
    ])
    await app.bot.send_message(
        chat_id=int(parent_tg_id),
        text=f"👦 *Ребёнок хочет вступить в чат*\n\n📢 *{chat_name}*\n\nЧто делаем?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def notify_parent_bot_request(app, parent_tg_id: str, request_id: str,
                                     bot_name: str, bot_username: str):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Разрешить", callback_data=f"approve_{request_id}"),
            InlineKeyboardButton("❌ Запретить", callback_data=f"reject_{request_id}"),
        ],
        [InlineKeyboardButton("🚫 Всегда блокировать", callback_data=f"block_{request_id}")]
    ])
    await app.bot.send_message(
        chat_id=int(parent_tg_id),
        text=f"👦 *Ребёнок хочет использовать бота*\n\n🤖 *{bot_name}* (@{bot_username})\n\nЧто делаем?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# ============================================================
# ОБРАБОТКА КНОПОК РАЗРЕШЕНИЙ
# ============================================================

async def handle_permission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_"):
        request_id = data[8:]
        db.update_request_status(request_id, "approved")
        req = db.get_pending_request(request_id)
        name = req.get("chat_name") or req.get("bot_name", "")
        await query.edit_message_text(f"✅ Разрешено: *{name}*", parse_mode="Markdown")
        if request_id in pending_events:
            pending_events[request_id].set()

    elif data.startswith("reject_"):
        request_id = data[7:]
        db.update_request_status(request_id, "rejected")
        req = db.get_pending_request(request_id)
        name = req.get("chat_name") or req.get("bot_name", "")
        await query.edit_message_text(f"❌ Запрещено: *{name}*", parse_mode="Markdown")
        if request_id in pending_events:
            pending_events[request_id].set()

    elif data.startswith("block_"):
        request_id = data[6:]
        req = db.get_pending_request(request_id)
        if req:
            item_type = "chat" if req["type"] == "join_chat" else "bot"
            item_id = str(req.get("chat_id") or req.get("bot_id", ""))
            item_name = req.get("chat_name") or req.get("bot_name", "")
            child_id = req.get("child_id")
            db.add_blocked(item_type, item_id, item_name, child_id=child_id)
            db.update_request_status(request_id, "rejected")
            await query.edit_message_text(
                f"🚫 Заблокировано навсегда: *{item_name}*", parse_mode="Markdown"
            )
            if request_id in pending_events:
                pending_events[request_id].set()

    elif data.startswith("blockitem_"):
        parts = data.split("_", 3)
        _, _, item_type, rest = parts
        item_id, item_name = rest.split("_", 1)
        db.add_blocked(item_type, item_id, item_name)
        await query.edit_message_text(f"🚫 Заблокировано: *{item_name}*", parse_mode="Markdown")

    elif data.startswith("unblock_"):
        block_id = int(data[8:])
        db.remove_blocked(block_id)
        await query.edit_message_text("✅ Разблокировано")


# ============================================================
# ЗАПУСК
# ============================================================

def build_app() -> Application:
    global parent_app
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler — онбординг ребёнка
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_add_child, pattern="^add_child$")],
        states={
            STATE_CHILD_NAME:         [MessageHandler(filters.TEXT & ~filters.COMMAND, state_child_name)],
            STATE_CHILD_BIRTH:        [MessageHandler(filters.TEXT & ~filters.COMMAND, state_child_birth)],
            STATE_RELATIONSHIP:       [CallbackQueryHandler(state_relationship, pattern="^pick_")],
            STATE_RELATIONSHIP_OTHER: [CallbackQueryHandler(state_relationship_other, pattern="^pick_")],
            STATE_CHILD_PHONE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, state_child_phone)],
            STATE_PARENT_NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, state_parent_name)],
            STATE_PARENT_EMAIL:       [MessageHandler(filters.TEXT & ~filters.COMMAND, state_parent_email)],
            STATE_POLICY_CONFIRM:     [
                CallbackQueryHandler(cb_policy_agree,   pattern="^policy_agree$"),
                CallbackQueryHandler(cb_policy_decline, pattern="^policy_decline$"),
            ],
            STATE_EMAIL_VERIFY: [
                # Кнопка «Я уже подтвердил» (ручная проверка)
                CallbackQueryHandler(cb_check_email_verify, pattern="^check_email_verify$"),
                # Кнопка «Готово», которую бот отправляет автоматически после email-верификации
                CallbackQueryHandler(cb_child_ready, pattern="^child_ready$"),
            ],
            STATE_AWAITING_READY: [
                CallbackQueryHandler(cb_child_ready, pattern="^child_ready$"),
            ],
            STATE_LINK_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_link_code),
                CallbackQueryHandler(cb_child_ready, pattern="^child_ready$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(cb_my_children, pattern="^my_children$"))
    app.add_handler(CallbackQueryHandler(handle_permission_callback,
                                         pattern="^(approve|reject|block|blockitem|unblock)_"))

    parent_app = app
    return app


async def main():
    # Добавляем первую версию политики, если её ещё нет
    if not db.get_current_policy():
        db.save_policy_version("1.0", PRIVACY_POLICY_TEXT, PRIVACY_POLICY_URL)
        logger.info("Политика конфиденциальности v1.0 добавлена в БД")

    app = build_app()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("✅ Бот родителя запущен")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
