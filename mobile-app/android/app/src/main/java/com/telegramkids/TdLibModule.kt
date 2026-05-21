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
        } catch (e: Exception) { promise.reject("INIT_ERROR", e.message) }
    }

    @ReactMethod fun send(jsonRequest: String, promise: Promise) { promise.resolve(null) }
    @ReactMethod fun addListener(eventName: String) {}
    @ReactMethod fun removeListeners(count: Int) {}

    private fun sendEvent(obj: TdApi.Object) {
        reactContext.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            .emit("tdlib_update", obj.toString())
    }
}
