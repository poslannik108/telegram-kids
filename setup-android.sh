#!/bin/bash
# Telegram Kids — полная установка Android-окружения + сборка TDLib
# Запустить один раз: bash setup-android.sh
# Время: ~20 мин установка + ~90 мин сборка TDLib

set -e  # остановиться при любой ошибке

ANDROID_HOME="$HOME/android-sdk"
NDK_VERSION="26.1.10909125"
CMAKE_VERSION="3.22.1"
BUILD_DIR="$HOME/tdlib-build"
PROJECT_DIR="$HOME/projects/telegram-kids"

echo ""
echo "================================================="
echo "  Telegram Kids — установка Android-окружения"
echo "================================================="
echo ""

# ── 1. Системные зависимости ──────────────────────────────────────────────────
echo ">>> [1/6] Системные пакеты..."
sudo apt-get update -qq
sudo apt-get install -y \
    openjdk-17-jdk-headless \
    cmake gperf ccache \
    build-essential git curl unzip wget \
    php-cli                   # нужен для сборки TDLib
java -version 2>&1 | head -1
echo "    Java OK"

# ── 2. Android command-line tools ────────────────────────────────────────────
echo ""
echo ">>> [2/6] Android SDK command-line tools..."
mkdir -p "$ANDROID_HOME/cmdline-tools"
cd /tmp
wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip \
    -O cmdline-tools.zip
unzip -q -o cmdline-tools.zip -d "$ANDROID_HOME/cmdline-tools"
mv "$ANDROID_HOME/cmdline-tools/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest" 2>/dev/null || true
rm cmdline-tools.zip

export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"
export ANDROID_HOME="$ANDROID_HOME"

echo "    Принимаем лицензии..."
yes | sdkmanager --licenses > /dev/null 2>&1 || true
echo "    SDK tools OK"

# ── 3. Android SDK + NDK + CMake ─────────────────────────────────────────────
echo ""
echo ">>> [3/6] Android SDK, NDK, CMake (может занять 10–15 мин)..."
sdkmanager --install \
    "platform-tools" \
    "platforms;android-34" \
    "build-tools;34.0.0" \
    "ndk;${NDK_VERSION}" \
    "cmake;${CMAKE_VERSION}"
echo "    NDK и CMake установлены"

# ── 4. Переменные окружения в .bashrc ────────────────────────────────────────
echo ""
echo ">>> [4/6] Переменные окружения..."
cat >> "$HOME/.bashrc" << ENVEOF

# Android SDK (добавлено setup-android.sh)
export ANDROID_HOME="$HOME/android-sdk"
export ANDROID_NDK="$HOME/android-sdk/ndk/${NDK_VERSION}"
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="\$ANDROID_HOME/cmdline-tools/latest/bin:\$ANDROID_HOME/platform-tools:\$JAVA_HOME/bin:\$PATH"
ENVEOF
export ANDROID_NDK="$ANDROID_HOME/ndk/${NDK_VERSION}"
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
echo "    .bashrc обновлён"

# ── 5. Клонирование и сборка TDLib ───────────────────────────────────────────
echo ""
echo ">>> [5/6] Клонируем TDLib..."
if [ ! -d "$HOME/td" ]; then
    git clone --depth=1 https://github.com/tdlib/td.git "$HOME/td"
fi
echo "    Клонирование завершено"

echo ""
echo ">>> [6/6] Сборка TDLib для Android (ARM64, ARM, x86_64, x86)..."
echo "    Это займёт ~60–90 минут. Можете свернуть терминал."
echo ""

mkdir -p "$BUILD_DIR"
cd "$HOME/td"

# Скрипт сборки для Android — официальный метод из документации TDLib
mkdir -p jni/tdlib

cd "$HOME/td"
rm -rf build-android
mkdir build-android
cd build-android

# Собираем для всех ABI
for ABI in arm64-v8a armeabi-v7a x86_64 x86; do
    echo "    Сборка для $ABI..."
    mkdir -p "$ABI"
    cd "$ABI"
    cmake \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
        -DANDROID_ABI="$ABI" \
        -DANDROID_PLATFORM=android-21 \
        -DCMAKE_INSTALL_PREFIX="$PROJECT_DIR/mobile-app/android/tdlib/$ABI" \
        -DTD_ENABLE_JNI=ON \
        -DANDROID_STL=c++_shared \
        ../../ > /tmp/tdlib-cmake-$ABI.log 2>&1
    cmake --build . --target install -j$(nproc) > /tmp/tdlib-build-$ABI.log 2>&1
    cd ..
    echo "    $ABI — готово"
done

echo ""
echo "================================================="
echo "  ГОТОВО!"
echo ""
echo "  TDLib собран для: arm64-v8a, armeabi-v7a, x86_64, x86"
echo "  Файлы: $PROJECT_DIR/mobile-app/android/tdlib/"
echo ""
echo "  Следующий шаг: создание React Native проекта."
echo "  Запустите: bash $PROJECT_DIR/setup-rn.sh"
echo "================================================="
