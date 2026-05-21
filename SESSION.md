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

**Первая задача после `setup-rn.sh`:**
1. Фаза 1а — фундамент (в этом порядке):
   a. `feature_flags` в БД + `GET /feature-flags` + `useFeatureFlag.js`
   b. `app_themes` в БД + `GET /theme` + `ThemeProvider.js` + `useTheme.js`
   c. `translations` в БД + `GET /translations/{lang}/{ns}` + `i18n.js` + `useTranslation.js`
2. Только после 1а — нативный модуль TdLib (Kotlin) + `TdLib.js` singleton
3. Только после TdLib — первые экраны (LoginScreen v2)

> ПРАВИЛО: ни один компонент не пишется без useTheme(), useFeatureFlag(), t()
> Хардкодные строки, цвета, флаги — нарушение архитектуры.

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
