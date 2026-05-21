#!/bin/bash
# Создание React Native проекта + подключение TDLib
# Запустить после setup-tdlib.sh: bash setup-rn.sh

set -e

PROJECT_DIR="$HOME/projects/telegram-kids"
RN_DIR="$PROJECT_DIR/mobile-app"
TDLIB_LIBS="$HOME/td/example/android/tdlib/libs"
TDLIB_JAVA="$HOME/td/example/android/tdlib/java"
TEMP_DIR="/tmp/TelegramKidsInit"

echo ""
echo "================================================="
echo "  Telegram Kids — React Native + TDLib setup"
echo "================================================="

# ── Проверка TDLib ────────────────────────────────────────────────────────────
if [ ! -f "$TDLIB_LIBS/arm64-v8a/libtdjni.so" ]; then
    echo "ОШИБКА: TDLib не собран. Сначала: bash setup-tdlib.sh"
    exit 1
fi
echo "✓ TDLib найден"

# ── 1. Инициализация React Native проекта ────────────────────────────────────
echo ""
echo "[1/5] Создаём React Native 0.74 проект..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Инициализируем без --skip-install чтобы получить android/
npx react-native@0.74.2 init TelegramKids \
    --directory "$TEMP_DIR/TelegramKids" \
    --skip-git-init \
    --install-pods=false

# Проверяем что android/ создался
if [ ! -d "$TEMP_DIR/TelegramKids/android" ]; then
    echo "ОШИБКА: android/ не создался. Проверьте вывод выше."
    exit 1
fi
echo "✓ React Native проект создан"

# ── 2. Копируем android/ и ios/ ───────────────────────────────────────────────
echo ""
echo "[2/5] Копируем android/ ios/ в проект..."
rm -rf "$RN_DIR/android" "$RN_DIR/ios" "$RN_DIR/node_modules" 2>/dev/null || true
cp -r "$TEMP_DIR/TelegramKids/android" "$RN_DIR/"
cp -r "$TEMP_DIR/TelegramKids/ios"     "$RN_DIR/" 2>/dev/null || true
rm -rf "$TEMP_DIR"
echo "✓ android/ скопирован"

# ── 3. package.json ───────────────────────────────────────────────────────────
echo ""
echo "[3/5] package.json с зависимостями..."
cat > "$RN_DIR/package.json" << 'EOF'
{
  "name": "TelegramKids",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "android": "react-native run-android",
    "start": "react-native start",
    "lint": "eslint ."
  },
  "dependencies": {
    "react": "18.2.0",
    "react-native": "0.74.2",
    "@react-navigation/native": "^6.1.17",
    "@react-navigation/stack": "^6.3.29",
    "@react-navigation/bottom-tabs": "^6.5.20",
    "react-native-screens": "^3.31.1",
    "react-native-safe-area-context": "^4.10.1",
    "react-native-gesture-handler": "^2.16.2",
    "react-native-reanimated": "^3.12.0",
    "@react-native-async-storage/async-storage": "^1.23.1",
    "@react-native-community/netinfo": "^11.3.1",
    "react-native-vector-icons": "^10.1.0",
    "react-native-fast-image": "^8.6.3",
    "react-native-video": "^6.3.3",
    "react-native-audio-recorder-player": "^3.6.10",
    "react-native-document-picker": "^9.1.1",
    "react-native-image-crop-picker": "^0.40.3",
    "react-native-vision-camera": "^4.3.2",
    "lottie-react-native": "^6.7.0",
    "react-native-mmkv": "^2.12.2",
    "zustand": "^4.5.2",
    "i18next": "^23.11.5",
    "react-i18next": "^14.1.2",
    "react-native-localize": "^3.2.1",
    "dayjs": "^1.11.11",
    "@notifee/react-native": "^9.0.0"
  },
  "devDependencies": {
    "@babel/core": "^7.20.0",
    "@babel/preset-env": "^7.20.0",
    "@babel/runtime": "^7.20.0",
    "@react-native/babel-preset": "0.74.84",
    "@react-native/eslint-config": "0.74.84",
    "@react-native/metro-config": "0.74.84",
    "eslint": "^8.19.0"
  }
}
EOF
echo "✓ package.json создан"

# ── 4. TDLib .so → jniLibs ───────────────────────────────────────────────────
echo ""
echo "[4/5] Копируем TDLib .so и Java классы..."
JNI_DIR="$RN_DIR/android/app/src/main/jniLibs"
mkdir -p "$JNI_DIR"

for ABI in arm64-v8a armeabi-v7a x86_64 x86; do
    if [ -d "$TDLIB_LIBS/$ABI" ]; then
        mkdir -p "$JNI_DIR/$ABI"
        cp "$TDLIB_LIBS/$ABI"/*.so "$JNI_DIR/$ABI/"
        echo "      $ABI: $(ls $JNI_DIR/$ABI/*.so | wc -l) файлов"
    fi
done

JAVA_OUT="$RN_DIR/android/app/src/main/java/org/drinkless/tdlib"
mkdir -p "$JAVA_OUT"
cp -r "$TDLIB_JAVA/org/drinkless/tdlib/"* "$JAVA_OUT/"
echo "✓ TdApi.java, Client.java скопированы"

# ── 5. Нативный модуль TdLib (Kotlin) ────────────────────────────────────────
echo ""
echo "[5/5] Нативный модуль TdLibModule..."
KOTLIN_DIR="$RN_DIR/android/app/src/main/java/com/telegramkids"
mkdir -p "$KOTLIN_DIR"

cat > "$KOTLIN_DIR/TdLibModule.kt" << 'KOTLIN'
package com.telegramkids

import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule
import org.drinkless.tdlib.Client
import org.drinkless.tdlib.TdApi

class TdLibModule(private val reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private var client: Client? = null

    override fun getName() = "TdLib"

    @ReactMethod
    fun initialize(promise: Promise) {
        try {
            Client.setLogVerbosityLevel(0)
            client = Client.create({ update -> sendEvent(update) }, null, null)
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("INIT_ERROR", e.message)
        }
    }

    @ReactMethod
    fun send(jsonRequest: String, promise: Promise) {
        promise.resolve(null) // заглушка — реализуем в Фазе 1
    }

    @ReactMethod
    fun addListener(eventName: String) {}

    @ReactMethod
    fun removeListeners(count: Int) {}

    private fun sendEvent(obj: TdApi.Object) {
        reactContext
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            .emit("tdlib_update", obj.toString())
    }
}
KOTLIN

cat > "$KOTLIN_DIR/TdLibPackage.kt" << 'KOTLIN'
package com.telegramkids

import com.facebook.react.ReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.uimanager.ViewManager

class TdLibPackage : ReactPackage {
    override fun createNativeModules(ctx: ReactApplicationContext): List<NativeModule> =
        listOf(TdLibModule(ctx))
    override fun createViewManagers(ctx: ReactApplicationContext): List<ViewManager<*, *>> =
        emptyList()
}
KOTLIN

echo "✓ TdLibModule.kt, TdLibPackage.kt созданы"

# ── Установка npm зависимостей ────────────────────────────────────────────────
echo ""
echo "Устанавливаем npm зависимости (~5 мин)..."
cd "$RN_DIR"
npm install --legacy-peer-deps

echo ""
echo "================================================="
echo "  ГОТОВО!"
echo ""
echo "  .so файлы:"
find "$RN_DIR/android/app/src/main/jniLibs" -name "*.so" | grep -v debug | sort
echo ""
echo "  Следующий шаг: подключите Android-телефон по USB"
echo "  (включить Режим разработчика + USB-отладку)"
echo "  затем:"
echo "  cd ~/projects/telegram-kids/mobile-app"
echo "  npx react-native run-android"
echo "================================================="
