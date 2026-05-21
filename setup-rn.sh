#!/bin/bash
# React Native + TDLib setup
# Запустить после setup-tdlib.sh: bash setup-rn.sh

set -e

PROJECT_DIR="$HOME/projects/telegram-kids"
RN_DIR="$PROJECT_DIR/mobile-app"
TDLIB_LIBS="$HOME/td/example/android/tdlib/libs"
TDLIB_JAVA="$HOME/td/example/android/tdlib/java"

echo ""
echo "================================================="
echo "  Telegram Kids — React Native + TDLib setup"
echo "================================================="

if [ ! -f "$TDLIB_LIBS/arm64-v8a/libtdjni.so" ]; then
    echo "ОШИБКА: TDLib не собран. Сначала: bash setup-tdlib.sh"
    exit 1
fi
echo "✓ TDLib найден"

# ── 1. Шаблон android/ из npm-кэша ───────────────────────────────────────────
# react-native init на Linux падает из-за отсутствия cocoapods (только macOS).
# Обходим это: берём шаблон из кэша npx — он там есть после любого запуска init.
echo ""
echo "[1/5] Получаем шаблон android/ из npm-кэша..."

TEMPLATE=$(find ~/.npm/_npx -path "*/react-native/template" -maxdepth 8 2>/dev/null | head -1)

if [ -z "$TEMPLATE" ] || [ ! -d "$TEMPLATE/android" ]; then
    echo "    Кэш пуст, качаем (займёт ~2 мин)..."
    cd /tmp && mkdir -p _rn_cache && cd _rn_cache
    npx react-native@0.74.7 init _Init 2>/dev/null || true
    TEMPLATE=$(find ~/.npm/_npx -path "*/react-native/template" -maxdepth 8 2>/dev/null | head -1)
    rm -rf /tmp/_rn_cache
fi

if [ -z "$TEMPLATE" ] || [ ! -d "$TEMPLATE/android" ]; then
    echo "ОШИБКА: шаблон не найден"
    exit 1
fi
echo "      ✓ $TEMPLATE"

# ── 2. Копируем android/ ─────────────────────────────────────────────────────
echo ""
echo "[2/5] android/..."
rm -rf "$RN_DIR/android" "$RN_DIR/node_modules" 2>/dev/null || true
cp -r "$TEMPLATE/android" "$RN_DIR/"
cp "$TEMPLATE/index.js" "$TEMPLATE/babel.config.js" \
   "$TEMPLATE/metro.config.js" "$TEMPLATE/app.json" "$RN_DIR/" 2>/dev/null || true
find "$RN_DIR/android" -type f | xargs sed -i 's/HelloWorld/TelegramKids/g' 2>/dev/null || true
find "$RN_DIR/android" -type f | xargs sed -i 's/helloworld/telegramkids/g' 2>/dev/null || true
sed -i 's/HelloWorld/TelegramKids/g' "$RN_DIR/app.json" 2>/dev/null || true
echo "      ✓"

# ── 3. package.json ───────────────────────────────────────────────────────────
echo ""
echo "[3/5] package.json..."
cat > "$RN_DIR/package.json" << 'EOF'
{
  "name": "TelegramKids",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "android": "react-native run-android",
    "start": "react-native start"
  },
  "dependencies": {
    "react": "18.2.0",
    "react-native": "0.74.7",
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
    "react-native-mmkv": "^2.12.2",
    "zustand": "^4.5.2",
    "i18next": "^23.11.5",
    "react-i18next": "^14.1.2",
    "react-native-localize": "^3.2.1",
    "dayjs": "^1.11.11"
  },
  "devDependencies": {
    "@babel/core": "^7.20.0",
    "@babel/runtime": "^7.20.0",
    "@react-native/babel-preset": "0.74.84",
    "@react-native/metro-config": "0.74.84",
    "eslint": "^8.19.0"
  }
}
EOF
echo "      ✓"

# ── 4. TDLib .so + Java классы ────────────────────────────────────────────────
echo ""
echo "[4/5] TDLib .so и Java классы..."
JNI_DIR="$RN_DIR/android/app/src/main/jniLibs"
mkdir -p "$JNI_DIR"
for ABI in arm64-v8a armeabi-v7a x86_64 x86; do
    [ -d "$TDLIB_LIBS/$ABI" ] && mkdir -p "$JNI_DIR/$ABI" && cp "$TDLIB_LIBS/$ABI"/*.so "$JNI_DIR/$ABI/"
done
JAVA_OUT="$RN_DIR/android/app/src/main/java/org/drinkless/tdlib"
mkdir -p "$JAVA_OUT"
cp -r "$TDLIB_JAVA/org/drinkless/tdlib/"* "$JAVA_OUT/"
echo "      ✓ $(find $JNI_DIR -name '*.so' | wc -l) .so файлов"

# ── 5. Нативный модуль + npm install ─────────────────────────────────────────
echo ""
echo "[5/5] Нативный модуль и npm install..."
KOTLIN_DIR="$RN_DIR/android/app/src/main/java/com/telegramkids"
mkdir -p "$KOTLIN_DIR"
cat > "$KOTLIN_DIR/TdLibModule.kt" << 'KOTLIN'
package com.telegramkids
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule
import org.drinkless.tdlib.Client
import org.drinkless.tdlib.TdApi
class TdLibModule(private val ctx: ReactApplicationContext) : ReactContextBaseJavaModule(ctx) {
    private var client: Client? = null
    override fun getName() = "TdLib"
    @ReactMethod fun initialize(promise: Promise) {
        try { Client.setLogVerbosityLevel(0); client = Client.create({ sendEvent(it) }, null, null); promise.resolve(null) }
        catch (e: Exception) { promise.reject("INIT_ERROR", e.message) }
    }
    @ReactMethod fun send(json: String, promise: Promise) { promise.resolve(null) }
    @ReactMethod fun addListener(e: String) {}
    @ReactMethod fun removeListeners(c: Int) {}
    private fun sendEvent(obj: TdApi.Object) =
        ctx.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java).emit("tdlib_update", obj.toString())
}
KOTLIN
cat > "$KOTLIN_DIR/TdLibPackage.kt" << 'KOTLIN'
package com.telegramkids
import com.facebook.react.ReactPackage; import com.facebook.react.bridge.*; import com.facebook.react.uimanager.ViewManager
class TdLibPackage : ReactPackage {
    override fun createNativeModules(ctx: ReactApplicationContext): List<NativeModule> = listOf(TdLibModule(ctx))
    override fun createViewManagers(ctx: ReactApplicationContext): List<ViewManager<*,*>> = emptyList()
}
KOTLIN

cd "$RN_DIR" && npm install --legacy-peer-deps --silent
echo "      ✓"

echo ""
echo "================================================="
echo "  ГОТОВО! Проект собран."
echo ""
echo "  Подключите Android-телефон по USB (USB debugging)"
echo "  затем:"
echo "  cd ~/projects/telegram-kids/mobile-app"
echo "  npx react-native run-android"
echo "================================================="
