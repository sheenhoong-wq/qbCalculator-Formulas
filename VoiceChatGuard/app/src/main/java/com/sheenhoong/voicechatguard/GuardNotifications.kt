package com.sheenhoong.voicechatguard

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.util.Log

/** 通知工具：拦截结果通知 + 挂断前的 5 秒倒计时确认通知 */
object GuardNotifications {

    private const val TAG = "VoiceChatGuard"

    /** 倒计时确认通知（横幅），独立高优先级渠道 */
    const val ALERT_CHANNEL_ID = "guard_countdown"
    const val COUNTDOWN_NOTIFICATION_ID = 1002

    fun ensureChannel(context: Context) {
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(
                VoiceChatGuardService.CHANNEL_ID,
                context.getString(R.string.channel_name),
                NotificationManager.IMPORTANCE_DEFAULT
            )
        )
        nm.createNotificationChannel(
            NotificationChannel(
                ALERT_CHANNEL_ID,
                context.getString(R.string.channel_name_countdown),
                NotificationManager.IMPORTANCE_HIGH
            )
        )
    }

    private fun receiverAction(
        context: Context,
        action: String,
        label: String,
        requestCode: Int,
        minutes: Int? = null
    ): Notification.Action {
        val intent = Intent(context, SnoozeReceiver::class.java).setAction(action)
        if (minutes != null) intent.putExtra(SnoozeReceiver.EXTRA_MINUTES, minutes)
        val pi = PendingIntent.getBroadcast(
            context, requestCode, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return Notification.Action.Builder(null, label, pi).build()
    }

    private fun notifySafely(context: Context, id: Int, n: Notification) {
        try {
            context.getSystemService(NotificationManager::class.java).notify(id, n)
        } catch (e: SecurityException) {
            Log.w(TAG, "无通知权限，跳过通知", e)
        }
    }

    /** 挂断前的倒计时确认：不挂断 / 立即挂断，5 秒无操作自动挂断 */
    fun showCountdown(context: Context, title: String) {
        ensureChannel(context)
        val text = context.getString(R.string.countdown_text)
        val n = Notification.Builder(context, ALERT_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_silent_mode)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setOngoing(true)
            .setCategory(Notification.CATEGORY_CALL)
            .addAction(
                receiverAction(
                    context, SnoozeReceiver.ACTION_KEEP,
                    context.getString(R.string.action_keep), 4, minutes = 30
                )
            )
            .addAction(
                receiverAction(
                    context, SnoozeReceiver.ACTION_HANGUP_NOW,
                    context.getString(R.string.action_hangup_now), 5
                )
            )
            .build()
        notifySafely(context, COUNTDOWN_NOTIFICATION_ID, n)
    }

    fun cancelCountdown(context: Context) {
        context.getSystemService(NotificationManager::class.java)
            .cancel(COUNTDOWN_NOTIFICATION_ID)
    }

    /** 拦截完成的结果通知，带「暂停30分钟/1小时」按钮 */
    fun showIntercepted(context: Context, title: String) {
        ensureChannel(context)
        val text = context.getString(R.string.notif_text)
        val n = Notification.Builder(context, VoiceChatGuardService.CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_silent_mode)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .addAction(
                receiverAction(
                    context, SnoozeReceiver.ACTION_SNOOZE,
                    context.getString(R.string.snooze_30), 1, minutes = 30
                )
            )
            .addAction(
                receiverAction(
                    context, SnoozeReceiver.ACTION_SNOOZE,
                    context.getString(R.string.snooze_60), 2, minutes = 60
                )
            )
            .build()
        notifySafely(context, VoiceChatGuardService.NOTIFICATION_ID, n)
    }
}
