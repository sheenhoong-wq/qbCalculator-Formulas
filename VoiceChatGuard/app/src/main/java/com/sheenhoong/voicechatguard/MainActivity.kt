package com.sheenhoong.voicechatguard

import android.content.ComponentName
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        findViewById<Button>(R.id.openSettingsButton).setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
    }

    override fun onResume() {
        super.onResume()
        statusText.text = if (isServiceEnabled()) {
            getString(R.string.status_enabled)
        } else {
            getString(R.string.status_disabled)
        }
    }

    private fun isServiceEnabled(): Boolean {
        val enabled = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        val component = ComponentName(this, VoiceChatGuardService::class.java)
        val full = component.flattenToString()
        val short = component.flattenToShortString()
        return enabled.split(':').any {
            it.equals(full, ignoreCase = true) || it.equals(short, ignoreCase = true)
        }
    }
}
