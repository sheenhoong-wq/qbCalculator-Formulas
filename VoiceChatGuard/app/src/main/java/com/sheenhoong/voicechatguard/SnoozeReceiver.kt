package com.sheenhoong.voicechatguard

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 处理通知按钮：
 *  - 倒计时确认通知：「不挂断」（取消本次 + 暂停30分钟）/「立即挂断」
 *  - 拦截结果通知：「暂停30分钟 / 1小时」/「立即恢复」
 */
class SnoozeReceiver : BroadcastReceiver() {
    companion object {
        const val ACTION_SNOOZE = "com.sheenhoong.voicechatguard.SNOOZE"
        const val ACTION_RESUME = "com.sheenhoong.voicechatguard.RESUME"
        const val ACTION_KEEP = "com.sheenhoong.voicechatguard.KEEP"
        const val ACTION_HANGUP_NOW = "com.sheenhoong.voicechatguard.HANGUP_NOW"
        const val EXTRA_MINUTES = "minutes"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val prefs = context.getSharedPreferences(VoiceChatGuardService.PREFS, Context.MODE_PRIVATE)
        val nm = context.getSystemService(NotificationManager::class.java)

        when (intent.action) {
            ACTION_HANGUP_NOW -> PendingHangup.executeNow(context)

            ACTION_KEEP -> {
                PendingHangup.cancel(context)
                snooze(context, prefs, nm, intent.getIntExtra(EXTRA_MINUTES, 30))
            }

            ACTION_SNOOZE ->
                snooze(context, prefs, nm, intent.getIntExtra(EXTRA_MINUTES, 30))

            ACTION_RESUME -> {
                prefs.edit().remove(VoiceChatGuardService.KEY_SNOOZE_UNTIL).commit()
                nm.cancel(VoiceChatGuardService.NOTIFICATION_ID)
            }
        }
    }

    private fun snooze(
        context: Context,
        prefs: android.content.SharedPreferences,
        nm: NotificationManager,
        minutes: Int
    ) {
        val until = System.currentTimeMillis() + minutes * 60_000L
        prefs.edit().putLong(VoiceChatGuardService.KEY_SNOOZE_UNTIL, until).commit()

        val untilText = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(until))
        val resumeIntent = Intent(context, SnoozeReceiver::class.java)
            .setAction(ACTION_RESUME)
        val resumePi = PendingIntent.getBroadcast(
            context, 3, resumeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val n = Notification.Builder(context, VoiceChatGuardService.CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_silent_mode)
            .setContentTitle(context.getString(R.string.snoozed_notif_title))
            .setContentText(context.getString(R.string.snoozed_notif_text, untilText))
            .setAutoCancel(true)
            .addAction(
                Notification.Action.Builder(
                    null, context.getString(R.string.action_resume), resumePi
                ).build()
            )
            .build()
        nm.notify(VoiceChatGuardService.NOTIFICATION_ID, n)
    }
}
