#!/bin/bash
# Telegram Kids — установка Android-окружения + сборка TDLib
# Запустить: bash setup-android.sh
# Время: ~20 мин установка + ~90–120 мин сборка TDLib

set -e

ANDROID_HOME="$HOME/android-sdk"
NDK_VERSION="26.1.10909125"
CMAKE_VERSION="3.22.1"
PROJECT_DIR="$HOME/projects/telegram-kids"
TD_DIR="$HOME/td"

export ANDROID_HOME
export ANDROID_NDK="$ANDROID_HOME/ndk/$NDK_VERSION"
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$JAVA_HOME/bin:$PATH"

echo ""
echo "================================================="
echo "  Telegram Kids — Android + TDLib setup"
echo "================================================="

# ── 1. Системные пакеты ───────────────────────────────────────────────────────
echo ""
echo "[1/7] Системные пакеты..."
sudo apt-get update -qq
sudo apt-get install -y \
    openjdk-17-jdk-headless \
    cmake gperf ccache php-cli \
    build-essential git curl unzip wget python3
echo "      OK: $(java -version 2>&1 | head -1)"

# ── 2. Android command-line tools ────────────────────────────────────────────
echo ""
echo "[2/7] Android SDK command-line tools..."
if [ ! -f "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]; then
    mkdir -p "$ANDROID_HOME/cmdline-tools"
    cd /tmp
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip \
        -O cmdline-tools.zip
    unzip -q -o cmdline-tools.zip -d "$ANDROID_HOME/cmdline-tools"
    mv "$ANDROID_HOME/cmdline-tools/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest" 2>/dev/null || true
    rm cmdline-tools.zip
fi
echo "      OK"

# ── 3. SDK, NDK, CMake ───────────────────────────────────────────────────────
echo ""
echo "[3/7] Android SDK, NDK r26, CMake (10–15 мин)..."
yes | sdkmanager --licenses > /dev/null 2>&1 || true
sdkmanager --install \
    "platform-tools" \
    "platforms;android-34" \
    "build-tools;34.0.0" \
    "ndk;${NDK_VERSION}" \
    "cmake;${CMAKE_VERSION}"
echo "      OK: NDK = $ANDROID_NDK"

# ── 4. Переменные окружения ───────────────────────────────────────────────────
echo ""
echo "[4/7] Переменные окружения в .bashrc..."
if ! grep -q "ANDROID_HOME" "$HOME/.bashrc"; then
    cat >> "$HOME/.bashrc" << ENVEOF

# Android SDK
export ANDROID_HOME="$HOME/android-sdk"
export ANDROID_NDK="$HOME/android-sdk/ndk/${NDK_VERSION}"
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="\$ANDROID_HOME/cmdline-tools/latest/bin:\$ANDROID_HOME/platform-tools:\$JAVA_HOME/bin:\$PATH"
ENVEOF
fi
echo "      OK"

# ── 5. Клонирование TDLib (полный клон — нужен для генерации файлов) ──────────
echo ""
echo "[5/7] Клонируем TDLib..."
if [ ! -d "$TD_DIR/.git" ]; then
    git clone https://github.com/tdlib/td.git "$TD_DIR"
else
    echo "      уже скачан, обновляем..."
    cd "$TD_DIR" && git pull
fi
echo "      OK"

# ── 6. Нативная сборка для генерации auto-файлов ─────────────────────────────
echo ""
echo "[6/7] Нативная сборка (генерация auto-файлов)..."
cd "$TD_DIR"
rm -rf build-native
mkdir build-native
cd build-native
cmake -DCMAKE_BUILD_TYPE=Release .. > /tmp/tdlib-native-cmake.log 2>&1
cmake --build . --target prepare_cross_compiling -j$(nproc) > /tmp/tdlib-native-build.log 2>&1
echo "      OK — auto-файлы сгенерированы"

# ── 7. Кросс-компиляция TDLib для Android ────────────────────────────────────
echo ""
echo "[7/7] Сборка TDLib для Android (ARM64, ARM, x86_64, x86)..."
echo "      ~60–90 минут. Можно свернуть терминал."
echo ""

OUT_DIR="$PROJECT_DIR/mobile-app/android/tdlib"
mkdir -p "$OUT_DIR"

cd "$TD_DIR"
rm -rf build-android
mkdir build-android
cd build-android

for ABI in arm64-v8a armeabi-v7a x86_64 x86; do
    echo "      [$ABI] начинаем..."
    mkdir -p "$ABI"
    cd "$ABI"

    cmake \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
        -DANDROID_ABI="$ABI" \
        -DANDROID_PLATFORM=android-21 \
        -DCMAKE_INSTALL_PREFIX="$OUT_DIR/$ABI" \
        -DTD_ENABLE_JNI=ON \
        -DANDROID_STL=c++_shared \
        ../../ > /tmp/tdlib-cmake-$ABI.log 2>&1

    cmake --build . --target install -j$(nproc) > /tmp/tdlib-build-$ABI.log 2>&1
    cd ..
    echo "      [$ABI] готово ✓"
done

# ── Итог ─────────────────────────────────────────────────────────────────────
echo ""
echo "================================================="
echo "  ГОТОВО!"
echo ""
echo "  TDLib .so файлы:"
find "$OUT_DIR" -name "*.so" | sort
echo ""
echo "  Следующий шаг: запустите в этом терминале:"
echo "  cd ~/projects/telegram-kids && bash setup-rn.sh"
echo "================================================="
