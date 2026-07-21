package com.sheenhoong.voicechatguard

import android.app.Notification
import android.app.PendingIntent
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

/**
 * 监视 WhatsApp 的常驻通话通知，处理「拨打后退出了界面」的情况：
 * 界面不在前台时，无障碍服务看不到退出按钮，但通话/语音聊天的常驻通知还在。
 *
 * 判定规则（宁可漏拦，不可错拦）：
 *  - 有「接听/拒绝/加入」按钮或含「来电」→ 别人打来的 → 绝不干预
 *  - 出现过「响铃中/Ringing」→ 一对一拨出通话 → 这条通话整个生命周期绝不干预
 *    （个人通话拨出后几秒内就会从「正在呼叫…」变成「响铃中…」；
 *     群组通话一直显示「正在呼叫…」——见实机截图）
 *  - 含「语音聊天/Voice chat」→ 本人在语音聊天中 → 挂断
 *  - 含「群组通话/Group call」类字样 → 群组通话 → 挂断
 *  - 「正在呼叫…/Calling…」持续 8 秒仍未变成「响铃中」→ 按群组通话处理 → 挂断
 *
 * 挂断方式：优先按通知上的「挂断」action；没有则打开通话界面，
 * 由无障碍服务在短时间窗口内点击界面上的挂断按钮（GuardState）。
 */
class CallNotificationListener : NotificationListenerService() {

    companion object {
        private const val TAG = "VoiceChatGuardNL"
        private const val WHATSAPP_PACKAGE = "com.whatsapp"

        /** 两次挂断动作之间的最小间隔 */
        private const val ACTION_DEBOUNCE_MS = 5000L

        /** 「正在呼叫…」复查延迟：个人通话在此之前会变成「响铃中…」 */
        private const val CALLING_RECHECK_MS = 8000L

        /** 打开通话界面后，允许无障碍服务点挂断的时间窗口 */
        private const val UI_FALLBACK_WINDOW_MS = 10_000L

        // 全部小写比较（正文取自通知的 text/subText/bigText，不含标题——
        // 标题是联系人/群组名，群组名里常含「群」字，不能用来判定）
        private val INCOMING_WORDS = listOf("来电", "incoming")
        private val RINGING_WORDS = listOf("响铃", "ringing")
        private val CALLING_WORDS = listOf("正在呼叫", "calling")
        private val VOICE_CHAT_WORDS = listOf("语音聊天", "voice chat")
        private val GROUP_CALL_WORDS = listOf(
            "群组通话", "群组语音", "群组视频",
            "group call", "group voice", "group video"
        )

        // 通知按钮：含这些词的按钮可以按（挂断类）
        private val HANGUP_ACTION_WORDS = listOf(
            "挂断", "结束", "退出", "离开", "hang up", "end call", "leave"
        )

        // 通知按钮：含这些词的按钮绝不按，出现即视为别人打来/邀请
        private val NEVER_PRESS_WORDS = listOf(
            "接听", "answer", "拒绝", "decline", "加入", "join", "回复", "reply"
        )
    }

    private val handler = Handler(Looper.getMainLooper())

    /** 已判定为一对一拨出通话的通知 key，整个生命周期不再干预 */
    private val personalKeys = mutableSetOf<String>()
    private val pendingChecks = mutableMapOf<String, Runnable>()
    private var lastActionAt = 0L

    override fun onListenerConnected() {
        // 权限刚开启/服务重启时，把已存在的通话通知也过一遍
        try {
            activeNotifications?.forEach { handle(it) }
        } catch (e: SecurityException) {
            Log.w(TAG, "读取现有通知失败", e)
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        handle(sbn)
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        personalKeys.remove(sbn.key)
        pendingChecks.remove(sbn.key)?.let { handler.removeCallbacks(it) }
    }

    private fun handle(sbn: StatusBarNotification) {
        if (sbn.packageName != WHATSAPP_PACKAGE) return
        // 通话/语音聊天都是常驻通知；普通消息通知直接跳过
        if (!sbn.isOngoing) return

        val n = sbn.notification
        val body = bodyOf(n)

        // 别人打来的（来电/接听/拒绝/加入按钮）→ 绝不干预
        val actionTitles = n.actions?.mapNotNull { it.title?.toString()?.lowercase() }
            ?: emptyList()
        if (actionTitles.any { t -> NEVER_PRESS_WORDS.any { t.contains(it) } }) return
        if (INCOMING_WORDS.any { body.contains(it) }) return

        // 「响铃中」→ 一对一拨出通话，标记后整个生命周期不再干预
        if (RINGING_WORDS.any { body.contains(it) }) {
            personalKeys.add(sbn.key)
            pendingChecks.remove(sbn.key)?.let { handler.removeCallbacks(it) }
            return
        }
        if (sbn.key in personalKeys) return
        if (isSnoozed()) return

        when {
            VOICE_CHAT_WORDS.any { body.contains(it) } ->
                hangUp(sbn, getString(R.string.notif_title))

            GROUP_CALL_WORDS.any { body.contains(it) } ->
                hangUp(sbn, getString(R.string.notif_title_call))

            CALLING_WORDS.any { body.contains(it) } && sbn.key !in pendingChecks -> {
                val key = sbn.key
                val check = Runnable {
                    pendingChecks.remove(key)
                    val cur = try {
                        activeNotifications?.firstOrNull { it.key == key }
                    } catch (e: SecurityException) {
                        null
                    } ?: return@Runnable
                    val curBody = bodyOf(cur.notification)
                    if (cur.isOngoing && key !in personalKeys && !isSnoozed() &&
                        CALLING_WORDS.any { curBody.contains(it) } &&
                        RINGING_WORDS.none { curBody.contains(it) } &&
                        INCOMING_WORDS.none { curBody.contains(it) }
                    ) {
                        hangUp(cur, getString(R.string.notif_title_call))
                    }
                }
                pendingChecks[key] = check
                handler.postDelayed(check, CALLING_RECHECK_MS)
            }
        }
    }

    private fun hangUp(sbn: StatusBarNotification, interceptTitle: String) {
        val now = SystemClock.elapsedRealtime()
        if (now - lastActionAt < ACTION_DEBOUNCE_MS) return

        val n = sbn.notification
        val hangupAction = n.actions?.firstOrNull { a ->
            val t = a.title?.toString()?.lowercase()?.trim() ?: return@firstOrNull false
            HANGUP_ACTION_WORDS.any { t.contains(it) } &&
                NEVER_PRESS_WORDS.none { t.contains(it) }
        }

        try {
            if (hangupAction != null) {
                hangupAction.actionIntent?.send() ?: return
                lastActionAt = now
                Log.i(TAG, "已通过通知按钮挂断：${hangupAction.title}")
            } else {
                // 通知上没有挂断按钮：打开通话界面，由无障碍服务点挂断
                val contentIntent = n.contentIntent ?: return
                GuardState.hangupUntilElapsed = now + UI_FALLBACK_WINDOW_MS
                contentIntent.send()
                lastActionAt = now
                Log.i(TAG, "已打开通话界面，等待无障碍服务挂断")
            }
            GuardNotifications.showIntercepted(this, interceptTitle)
        } catch (e: PendingIntent.CanceledException) {
            Log.w(TAG, "通知 PendingIntent 已失效", e)
        }
    }

    /** 通知正文（不含标题），小写 */
    private fun bodyOf(n: Notification): String {
        val e = n.extras
        return listOfNotNull(
            e.getCharSequence(Notification.EXTRA_TEXT),
            e.getCharSequence(Notification.EXTRA_SUB_TEXT),
            e.getCharSequence(Notification.EXTRA_BIG_TEXT)
        ).joinToString(" ").lowercase()
    }

    private fun isSnoozed(): Boolean {
        val until = getSharedPreferences(VoiceChatGuardService.PREFS, Context.MODE_PRIVATE)
            .getLong(VoiceChatGuardService.KEY_SNOOZE_UNTIL, 0L)
        return System.currentTimeMillis() < until
    }
}
