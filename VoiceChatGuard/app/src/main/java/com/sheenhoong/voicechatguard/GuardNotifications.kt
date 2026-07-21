package com.sheenhoong.voicechatguard

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.util.Log

/** 拦截提醒通知（带「暂停30分钟/1小时」按钮），无障碍服务和通知监听器共用 */
object GuardNotifications {

    private const val TAG = "VoiceChatGuard"

    fun ensureChannel(context: Context) {
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(
                VoiceChatGuardService.CHANNEL_ID,
                context.getString(R.string.channel_name),
                NotificationManager.IMPORTANCE_DEFAULT
            )
        )
    }

    fun showIntercepted(context: Context, title: String) {
        ensureChannel(context)
        val nm = context.getSystemService(NotificationManager::class.java)

        fun snoozeAction(minutes: Int, label: String, requestCode: Int): Notification.Action {
            val intent = Intent(context, SnoozeReceiver::class.java)
                .setAction(SnoozeReceiver.ACTION_SNOOZE)
                .putExtra(SnoozeReceiver.EXTRA_MINUTES, minutes)
            val pi = PendingIntent.getBroadcast(
                context, requestCode, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            return Notification.Action.Builder(null, label, pi).build()
        }

        val text = context.getString(R.string.notif_text)
        val n = Notification.Builder(context, VoiceChatGuardService.CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_silent_mode)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .addAction(snoozeAction(30, context.getString(R.string.snooze_30), 1))
            .addAction(snoozeAction(60, context.getString(R.string.snooze_60), 2))
            .build()

        try {
            nm.notify(VoiceChatGuardService.NOTIFICATION_ID, n)
        } catch (e: SecurityException) {
            Log.w(TAG, "无通知权限，跳过通知", e)
        }
    }
}
