#!/bin/bash
# Сборка TDLib для Android (правильный путь через официальные скрипты)
# Запустить: bash setup-tdlib.sh
# Время: ~30 мин OpenSSL + ~60 мин TDLib

set -e

ANDROID_HOME="${ANDROID_HOME:-$HOME/android-sdk}"
NDK_VERSION="26.1.10909125"
TD_DIR="$HOME/td"
PROJECT_DIR="$HOME/projects/telegram-kids"
EXAMPLE_DIR="$TD_DIR/example/android"

export ANDROID_HOME
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

echo ""
echo "================================================="
echo "  TDLib для Android — официальный метод"
echo "================================================="

# ── 1. Ninja (нужен для сборки) ───────────────────────────────────────────────
echo ""
echo "[1/4] Установка ninja-build..."
sudo apt-get install -y ninja-build > /dev/null
ninja --version
echo "      OK"

# ── 2. OpenSSL для Android ────────────────────────────────────────────────────
echo ""
echo "[2/4] Сборка OpenSSL для Android (~20–30 мин)..."
cd "$EXAMPLE_DIR"

# Удаляем старые артефакты если есть
rm -rf third-party/openssl 2>/dev/null || true

bash build-openssl.sh \
    "$ANDROID_HOME" \
    "$NDK_VERSION" \
    "third-party/openssl"

echo "      OpenSSL OK"

# ── 3. TDLib (libtdjni.so) ────────────────────────────────────────────────────
echo ""
echo "[3/4] Сборка TDLib — libtdjni.so (~60 мин)..."
cd "$EXAMPLE_DIR"

bash build-tdlib.sh \
    "$ANDROID_HOME" \
    "$NDK_VERSION" \
    "third-party/openssl" \
    "c++_shared" \
    "Java"

echo "      TDLib OK"

# ── 4. Копируем в проект ──────────────────────────────────────────────────────
echo ""
echo "[4/4] Копируем файлы в проект..."

OUT_DIR="$PROJECT_DIR/mobile-app/android/tdlib"
mkdir -p "$OUT_DIR"

# .so библиотеки
cp -r "$EXAMPLE_DIR/tdlib/libs/"* "$OUT_DIR/"

# Java-классы (TdApi.java, Client.java)
mkdir -p "$PROJECT_DIR/mobile-app/android/src/main/java/org/drinkless/tdlib"
cp -r "$EXAMPLE_DIR/tdlib/java/org/drinkless/tdlib/"* \
    "$PROJECT_DIR/mobile-app/android/src/main/java/org/drinkless/tdlib/"

echo ""
echo "================================================="
echo "  ГОТОВО!"
echo ""
echo "  .so файлы:"
find "$OUT_DIR" -name "*.so" | grep -v debug | sort
echo ""
echo "  Java классы:"
find "$PROJECT_DIR/mobile-app/android/src" -name "*.java" | sort
echo ""
echo "  Следующий шаг:"
echo "  cd ~/projects/telegram-kids && bash setup-rn.sh"
echo "================================================="
