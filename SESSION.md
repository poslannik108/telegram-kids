# Текущая сессия — состояние проекта

## Статус: ожидание завершения сборки TDLib

### Что сделано (все предыдущие сессии)

**Бэкенд (Python) — полностью готов:**
- `main.py` — бот родителя с полным регистрационным флоу (ConversationHandler):
  имя ребёнка → дата рождения → статус родства → телефон → имя/email родителя
  → политика конфиденциальности (DOI) → ссылки на скачивание → код привязки
- `db.py` — SQLite: parents, children, linking_codes, privacy_policy_versions,
  privacy_policy_consents, email_verification_tokens, rate_limits, registration_logs
- `api_server.py` — FastAPI: per-child Telethon сессии, event-based ожидание
  решения родителя (asyncio.Event, без polling), auth endpoints
- Rate limiting на всех точках входа
- DOI email верификация с аудит-историей

**Мобильное приложение (React Native) — базовые экраны:**
- LoginScreen, AwaitingLinkScreen, ChatsScreen, MessagesScreen,
  ContactsScreen, SettingsScreen, PendingScreen (делает реальный API-вызов)
- api.js с динамическими headers и всеми endpoints
> ВАЖНО: эти экраны написаны под старую REST-архитектуру.
> После подключения TDLib они будут полностью переписаны.

**Инфраструктура:**
- GitHub: https://github.com/poslannik108/telegram-kids
- SSH ключ настроен
- TDLib собран: arm64-v8a ✓, armeabi-v7a ✓, x86_64 (в процессе), x86 (ожидает)
- setup-android.sh, setup-tdlib.sh, setup-rn.sh — готовы

---

## Следующая сессия — начать отсюда

**Команда пользователю перед началом:**
```bash
# Убедиться что TDLib собран:
find ~/td/example/android/tdlib/libs -name "libtdjni.so" | sort

# Если 4 файла — запустить:
bash ~/projects/telegram-kids/setup-rn.sh
```

**Первая задача:**
1. Убедиться что `setup-rn.sh` завершился успешно
2. Создать нативный модуль TdLib для React Native (Kotlin)
3. Написать `mobile-app/src/TdLib.js` — singleton клиент
4. Реализовать авторизацию через TDLib (LoginScreen v2)

**Контекст который важно помнить:**
- Мобильное приложение должно подключаться к Telegram НАПРЯМУЮ через TDLib
- Наш сервер — только для родительского контроля (события, блокировки)
- Медиа идёт напрямую Telegram CDN ↔ телефон, через наш сервер НЕ проходит
- Архитектура стейта: Zustand (уже в package.json)
- Минимальная версия Android: API 21 (Android 5.0)

---

## Открытые вопросы
- [ ] Как пользователь будет тестировать? Физический телефон?
- [ ] ADB подключение: USB или WiFi?

---

*Обновляется в конце каждой сессии*
