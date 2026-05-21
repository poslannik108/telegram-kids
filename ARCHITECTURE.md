# Telegram Kids — архитектурные решения

## Почему TDLib (не GramJS, не Telethon на мобиле)

TDLib — официальная C++ библиотека Telegram, используется во всех официальных клиентах.
Медиафайлы (фото, видео, аудио, кружочки) идут НАПРЯМУЮ между телефоном и Telegram CDN.
Через наш сервер проходят только события управления (вступил в чат, написал боту).

GramJS отклонён: нестабилен при обновлениях MTProto, требует полифиллов в RN.
Telethon на сервере как прокси: двойной трафик, дорого, медленно.

## Двухкомпонентная архитектура

```
[Телефон ребёнка]
  TDLib (libtdjni.so) ←→ Серверы Telegram (медиа, сообщения)
  React Native UI
  WebSocket клиент    ←→ Наш сервер (только события управления)

[Наш сервер]
  main.py — бот родителя (python-telegram-bot)
  api_server.py — FastAPI + WebSocket
  db.py — SQLite → PostgreSQL при росте

[Телефон родителя]
  Обычный Telegram + наш бот
```

## Мобильное приложение — структура

```
mobile-app/
├── android/
│   ├── app/src/main/jniLibs/     ← libtdjni.so (все ABI)
│   └── app/src/main/java/
│       ├── org/drinkless/tdlib/  ← TdApi.java, Client.java (от TDLib)
│       └── com/telegramkids/     ← TdLibModule.kt, TdLibPackage.kt
├── src/
│   ├── TdLib.js                  ← singleton, все вызовы TDLib
│   ├── store/                    ← Zustand: chats, messages, auth, ui
│   ├── screens/                  ← экраны (по одному файлу)
│   ├── components/               ← переиспользуемые компоненты
│   ├── hooks/                    ← useChats, useMessages, useTdLib
│   └── utils/                    ← форматирование, файлы, медиа
```

## TdLib.js — главный принцип

Singleton. Все взаимодействия с TDLib ТОЛЬКО через него.
Экраны не вызывают TDLib напрямую — только через store или hooks.

```js
// Правильно:
const chats = useChats()  // Zustand store, данные уже там

// Неправильно:
TdLib.send({ '@type': 'getChats' })  // не из экрана напрямую
```

TdLib.js обрабатывает ВСЕ обновления (updateNewMessage, updateChatLastMessage и т.д.)
и пишет их в Zustand store. Экраны только читают store.

## Zustand store — структура

```js
// store/auth.js
{ status: 'unauthorized'|'wait_code'|'wait_password'|'ready', user: {...} }

// store/chats.js
{ chats: Map<chatId, Chat>, order: chatId[], loading: bool }

// store/messages.js
{ messages: Map<chatId, Message[]>, loading: Map<chatId, bool> }

// store/ui.js
{ theme: 'dark'|'light', pendingRequests: [] }
```

## Родительский контроль — точки перехвата в мобильном приложении

При попытке ребёнка сделать что-то ограниченное:
1. TdLib.js перехватывает событие ДО выполнения
2. Отправляет запрос на наш сервер через WebSocket
3. Показывает PendingScreen (ожидание решения родителя)
4. Сервер уведомляет родителя через бота
5. Родитель жмёт Разрешить/Запретить
6. Сервер отвечает через WebSocket
7. PendingScreen закрывается, действие выполняется или блокируется

Точки перехвата:
- Вступление в новый чат/канал → проверка перед joinChat
- Начало переписки с незнакомым → проверка перед первым сообщением
- Добавление бота → проверка перед открытием

## Дизайн-система

**Принцип:** UX-паттерны Telegram (расположение, жесты, навигация) + собственная визуальная идентичность.
UX-паттерны авторским правом не защищаются. Логотипы и иконки Telegram — не используем.

**Цвета:**
```
Фон основной:        #17212b
Фон вторичный:       #0e1621
Фон элементов:       #1e2d3d
Акцент (наш):        #2E86AB   ← не Telegram blue (#5288c1)
Пузырь входящий:     #182533
Пузырь исходящий:    #1B5E8A
Текст основной:      #ffffff
Текст вторичный:     #aaaaaa
Разделитель:         #2b3a4a
```

**Иконки:** Material Icons (Google, Apache 2.0) — не иконки Telegram.
**Логотип:** свой (создать отдельно — щит + силуэты детей).
**Шрифт:** системный (SF Pro / Roboto).

**Расположение элементов — как в Telegram:**
- Список чатов: главный экран, вертикальный список
- Переписка: пузыри, поле ввода внизу, кнопка отправки справа
- Stories: горизонтальная лента вверху ChatsScreen
- Таб-бар: снизу (Чаты / Контакты / Настройки)
- Свайп влево по чату: архив/удалить
- Long-press на сообщении: реакции + меню

## Соглашения по коду

- Язык: JavaScript (не TypeScript) — проще итерировать
- Стиль: функциональные компоненты, hooks
- Навигация: React Navigation v6 (Stack + BottomTabs)
- Стейт: Zustand (не Redux — проще)
- Медиа кэш: react-native-fast-image (не Image из RN)
- Анимации: Reanimated 3 (не Animated из RN)
- Иконки: react-native-vector-icons (MaterialIcons + MaterialCommunityIcons)
- Цвета: тёмная тема по умолчанию (#17212b фон, #5288c1 акцент)

## Бэкенд — важные детали

- Согласие с политикой: DOI (два клика: бот + ссылка в email)
- Все согласия хранятся с текстом и датой (152-ФЗ)
- Rate limiting: 3 OTP/10мин по IP, 5 писем/сутки, 1 «Готово»/2мин
- Event-based ожидание: asyncio.Event, сервер держит соединение открытым
- Таймаут ожидания решения родителя: 10 минут
- БД: SQLite сейчас, миграция на PostgreSQL при > 1000 пользователей

## Решения которые НЕ менять без обсуждения

1. TDLib вместо GramJS — медиа через CDN напрямую
2. Zustand вместо Redux — проще, меньше boilerplate
3. Телефон ребёнка авторизован в нашем приложении, не в официальном Telegram
4. Родитель использует обычный Telegram + наш бот (не отдельное приложение)
5. DOI для согласия с политикой (требование 152-ФЗ)
6. SQLite с ручными миграциями (достаточно для MVP)
