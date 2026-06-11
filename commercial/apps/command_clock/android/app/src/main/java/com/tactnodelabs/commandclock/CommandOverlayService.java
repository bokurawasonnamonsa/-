package com.tactnodelabs.commandclock;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.Settings;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.WindowManager;
import android.widget.TextView;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

public class CommandOverlayService extends Service {
    public static final String ACTION_SHOW = "com.tactnodelabs.commandclock.action.SHOW_OVERLAY";
    public static final String ACTION_HIDE = "com.tactnodelabs.commandclock.action.HIDE_OVERLAY";
    public static final String ACTION_UPDATE_TEXT = "com.tactnodelabs.commandclock.action.UPDATE_TEXT";
    public static final String EXTRA_TEXT = "text";

    private static final String CHANNEL_ID = "command_clock_overlay";
    private static final int NOTIFICATION_ID = 4101;
    private static final String PREFS = "command_clock";
    private static final String KEY_LABEL = "label";
    private static final String KEY_INSTRUCTION_EPOCH = "instruction_epoch";
    private static final String KEY_MY_SECONDS = "my_seconds";
    private static final String KEY_LONGEST_SECONDS = "longest_seconds";
    private static final String KEY_BUFFER_SECONDS = "buffer_seconds";
    private static final String KEY_FLOW_SECONDS = "flow_seconds";
    private static final String KEY_OVERLAY = "overlay_enabled";
    private static final String KEY_LANGUAGE = "language";

    private final Handler handler = new Handler(Looper.getMainLooper());
    private WindowManager windowManager;
    private WindowManager.LayoutParams overlayParams;
    private TextView overlayView;
    private String latestText = "UTC --:--:--\nWaiting\n--:--";
    private boolean overlayEnabled = true;

    private final Runnable overlayTick = new Runnable() {
        @Override
        public void run() {
            if (overlayEnabled) {
                latestText = buildClockText();
                ensureOverlay();
                updateOverlayText();
                handler.postDelayed(this, 1000);
            }
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        createNotificationChannel();
        startForeground(NOTIFICATION_ID, buildNotification());
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : null;
        if (ACTION_HIDE.equals(action)) {
            overlayEnabled = false;
            saveOverlayState(false);
            handler.removeCallbacks(overlayTick);
            removeOverlay();
            stopForeground(true);
            stopSelf();
        } else if (ACTION_SHOW.equals(action)) {
            overlayEnabled = true;
            saveOverlayState(true);
            ensureOverlay();
            startOverlayTick();
            updateNotification();
        } else {
            if (ACTION_UPDATE_TEXT.equals(action)) {
                String text = intent.getStringExtra(EXTRA_TEXT);
                if (text != null && !text.trim().isEmpty()) {
                    latestText = text.trim();
                }
            }
            if (overlayEnabled) {
                ensureOverlay();
                startOverlayTick();
            }
            updateOverlayText();
        }
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacks(overlayTick);
        removeOverlay();
        super.onDestroy();
    }

    private void ensureOverlay() {
        if (!Settings.canDrawOverlays(this) || overlayView != null) {
            return;
        }
        overlayView = new TextView(this);
        overlayView.setTextColor(Color.rgb(255, 218, 106));
        overlayView.setTextSize(15);
        overlayView.setGravity(Gravity.CENTER);
        overlayView.setPadding(dp(18), dp(10), dp(18), dp(10));
        overlayView.setBackgroundColor(Color.argb(222, 8, 10, 14));
        overlayView.setSingleLine(false);
        overlayView.setMaxLines(3);
        overlayView.setLineSpacing(0, 1.05f);
        overlayView.setMinWidth(dp(190));
        overlayView.setMinHeight(dp(68));
        overlayView.setOnTouchListener(new DragTouchListener());

        int type = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;
        overlayParams = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                type,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.TRANSLUCENT
        );
        overlayParams.gravity = Gravity.TOP | Gravity.START;
        overlayParams.x = dp(16);
        overlayParams.y = dp(210);
        try {
            windowManager.addView(overlayView, overlayParams);
        } catch (RuntimeException e) {
            overlayView = null;
            overlayEnabled = false;
            saveOverlayState(false);
            stopForeground(true);
            stopSelf();
        }
    }

    private void updateOverlayText() {
        if (overlayView != null) {
            overlayView.setText(latestText);
        }
    }

    private void removeOverlay() {
        if (overlayView != null) {
            windowManager.removeView(overlayView);
            overlayView = null;
        }
    }

    private Notification buildNotification() {
        Intent launchIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this,
                0,
                launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        return builder
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("Command Clock")
                .setContentText(overlayEnabled ? "Floating countdown is visible" : "Floating countdown is hidden")
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Hide", serviceAction(ACTION_HIDE, 1))
                .addAction(android.R.drawable.ic_menu_view, "Show", serviceAction(ACTION_SHOW, 2))
                .build();
    }

    private PendingIntent serviceAction(String action, int requestCode) {
        Intent intent = new Intent(this, CommandOverlayService.class);
        intent.setAction(action);
        return PendingIntent.getService(
                this,
                requestCode,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
    }

    private void updateNotification() {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        manager.notify(NOTIFICATION_ID, buildNotification());
    }

    private void startOverlayTick() {
        handler.removeCallbacks(overlayTick);
        latestText = buildClockText();
        updateOverlayText();
        handler.postDelayed(overlayTick, 1000);
    }

    private String buildClockText() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        long instructionEpoch = prefs.getLong(KEY_INSTRUCTION_EPOCH, 0L);
        int my = prefs.getInt(KEY_MY_SECONDS, 60);
        int longest = prefs.getInt(KEY_LONGEST_SECONDS, 60);
        int buffer = prefs.getInt(KEY_BUFFER_SECONDS, 15);
        int flow = prefs.getInt(KEY_FLOW_SECONDS, 300);
        String label = prefs.getString(KEY_LABEL, "");
        String lang = prefs.getString(KEY_LANGUAGE, "en");
        Instant now = Instant.now();
        String utc = "UTC " + DateTimeFormatter.ofPattern("HH:mm:ss")
                .withZone(ZoneOffset.UTC)
                .format(now);
        if (instructionEpoch <= 0) {
            return utc + "\n" + loc(lang,
                    "Waiting…", "待機中…", "대기 중…", "等待中…",
                    "รอคำสั่ง…", "Menunggu…", "Esperando…",
                    "Aguardando…", "En attente…", "Warten…") + "\n--:--";
        }
        long pressEpoch = instructionEpoch + buffer + Math.max(0, longest - my);
        long arrivalEpoch = instructionEpoch + buffer + longest + flow;
        long nowEpoch = now.getEpochSecond();
        boolean waitingForStart = nowEpoch < pressEpoch;
        long targetEpoch = waitingForStart ? pressEpoch : arrivalEpoch;
        long remaining = Math.max(0, targetEpoch - nowEpoch);
        String phase = waitingForStart
                ? loc(lang, "Start: ", "開始: ", "시작: ", "开始: ", "เริ่ม: ", "Mulai: ", "Inicio: ", "Início: ", "Début: ", "Start: ")
                : loc(lang, "Arrive: ", "到着: ", "도착: ", "到达: ", "ถึง: ", "Tiba: ", "Llegar: ", "Chegar: ", "Arrivée: ", "Ankunft: ");
        String labelPart = label.isEmpty() ? "" : " " + label;
        return utc + "\n" + phase + labelPart + "\n" + formatDuration(remaining);
    }

    private String loc(String lang, String en, String ja, String ko, String zh,
                       String th, String id, String es, String pt, String fr, String de) {
        switch (lang) {
            case "ja": return ja;
            case "ko": return ko;
            case "zh": return zh;
            case "th": return th;
            case "id": return id;
            case "es": return es;
            case "pt": return pt;
            case "fr": return fr;
            case "de": return de;
            default:   return en;
        }
    }

    private String formatDuration(long secondsRemaining) {
        long hours = secondsRemaining / 3600;
        long minutes = (secondsRemaining % 3600) / 60;
        long seconds = secondsRemaining % 60;
        if (hours > 0) {
            return String.format(Locale.US, "%02d:%02d:%02d", hours, minutes, seconds);
        }
        return String.format(Locale.US, "%02d:%02d", minutes, seconds);
    }

    private void saveOverlayState(boolean enabled) {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_OVERLAY, enabled).apply();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Command Clock",
                NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription("Keeps the floating countdown available.");
        NotificationManager manager = (NotificationManager) getSystemService(NotificationManager.class);
        manager.createNotificationChannel(channel);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private class DragTouchListener implements android.view.View.OnTouchListener {
        private int startX;
        private int startY;
        private float touchStartX;
        private float touchStartY;

        @Override
        public boolean onTouch(android.view.View view, MotionEvent event) {
            if (overlayParams == null) {
                return false;
            }
            switch (event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                    startX = overlayParams.x;
                    startY = overlayParams.y;
                    touchStartX = event.getRawX();
                    touchStartY = event.getRawY();
                    return true;
                case MotionEvent.ACTION_MOVE:
                    overlayParams.x = startX + Math.round(event.getRawX() - touchStartX);
                    overlayParams.y = startY + Math.round(event.getRawY() - touchStartY);
                    windowManager.updateViewLayout(overlayView, overlayParams);
                    return true;
                default:
                    return true;
            }
        }
    }
}
