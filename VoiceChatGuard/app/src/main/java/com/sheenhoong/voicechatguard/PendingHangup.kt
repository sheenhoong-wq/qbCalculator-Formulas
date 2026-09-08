package com.sheenhoong.voicechatguard

import android.content.Context
import android.os.Handler
import android.os.Looper

/**
 * 「5 秒确认」流程：检测到要拦截时不立即挂断，先弹倒计时提示通知
 * （「不挂断 / 立即挂断」），5 秒无操作则自动执行挂断。
 *
 * 同一时间只有一个待执行动作；无障碍服务和通知监听器共用（同进程）。
 */
object PendingHangup {

    const val DELAY_MS = 5000L

    private val handler = Handler(Looper.getMainLooper())
    private var pending: Runnable? = null

    fun hasPending(): Boolean = pending != null

    /** 弹出倒计时提示，5 秒后执行 [execute]（除非被取消或提前执行） */
    fun schedule(context: Context, promptTitle: String, execute: () -> Unit) {
        cancel(context)
        val wrapped = Runnable {
            pending = null
            GuardNotifications.cancelCountdown(context)
            execute()
        }
        pending = wrapped
        handler.postDelayed(wrapped, DELAY_MS)
        GuardNotifications.showCountdown(context, promptTitle)
    }

    /** 「立即挂断」按钮：马上执行 */
    fun executeNow(context: Context) {
        val r = pending ?: return
        handler.removeCallbacks(r)
        handler.post(r)
    }

    /** 「不挂断」按钮：取消本次动作 */
    fun cancel(context: Context) {
        pending?.let { handler.removeCallbacks(it) }
        pending = null
        GuardNotifications.cancelCountdown(context)
    }
}
