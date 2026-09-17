package pk.zakariasons.zakaria_erp

import android.content.Context
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

// Remembers the server address entered under Connection settings. Kept in the
// app instead of a plugin so Windows builds need no plugin symlinks.
class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val settings = getSharedPreferences("zakaria_erp_settings", Context.MODE_PRIVATE)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "pk.zakariasons.zakaria_erp/settings")
            .setMethodCallHandler { call, result ->
                val key = call.argument<String>("key")
                when {
                    key != "api_server" -> result.error("unsupported", "Unsupported setting", null)
                    call.method == "get" -> result.success(settings.getString(key, null))
                    call.method == "set" -> {
                        settings.edit().putString(key, call.argument<String>("value")).apply()
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
