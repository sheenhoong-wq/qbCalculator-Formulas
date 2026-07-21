package com.sheenhoong.voicechatguard

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var resumeButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        resumeButton = findViewById(R.id.resumeButton)

        findViewById<Button>(R.id.openSettingsButton).setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        resumeButton.setOnClickListener {
            getSharedPreferences(VoiceChatGuardService.PREFS, Context.MODE_PRIVATE)
                .edit().remove(VoiceChatGuardService.KEY_SNOOZE_UNTIL).apply()
            refreshStatus()
        }

        // Android 13+ 通知权限（用于「已拦截」提醒和暂停按钮）
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 100
            )
        }
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    private fun refreshStatus() {
        val snoozeUntil = getSharedPreferences(VoiceChatGuardService.PREFS, Context.MODE_PRIVATE)
            .getLong(VoiceChatGuardService.KEY_SNOOZE_UNTIL, 0L)
        val snoozed = System.currentTimeMillis() < snoozeUntil

        statusText.text = when {
            !isServiceEnabled() -> getString(R.string.status_disabled)
            snoozed -> {
                val untilText =
                    SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(snoozeUntil))
                getString(R.string.status_snoozed, untilText)
            }
            else -> getString(R.string.status_enabled)
        }
        resumeButton.visibility =
            if (snoozed && isServiceEnabled()) View.VISIBLE else View.GONE
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
