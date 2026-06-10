package com.tactnodelabs.commandclock;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final String PREFS = "command_clock";
    private static final String KEY_LABEL = "label";
    private static final String KEY_INSTRUCTION_EPOCH = "instruction_epoch";
    private static final String KEY_MY_SECONDS = "my_seconds";
    private static final String KEY_LONGEST_SECONDS = "longest_seconds";
    private static final String KEY_BUFFER_SECONDS = "buffer_seconds";
    private static final String KEY_FLOW_SECONDS = "flow_seconds";
    private static final String KEY_LANGUAGE = "language";
    private static final String KEY_OVERLAY = "overlay_enabled";
    private static final int REQUEST_POST_NOTIFICATIONS = 4101;

    private static final String[] LANG_CODES = {"en", "ja", "ko", "zh", "th", "id", "es", "pt", "fr", "de"};
    private static final String[] LANG_NAMES = {
            "English", "日本語", "한국어", "中文", "ไทย", "Bahasa Indonesia",
            "Español", "Português", "Français", "Deutsch"
    };

    private final Handler handler = new Handler(Looper.getMainLooper());
    private Spinner languageSpinner;
    private TextView languageLabel;
    private TextView utcTime;
    private TextView targetSummary;
    private TextView countdownTitle;
    private TextView countdown;
    private TextView shareCodeView;
    private TextView status;
    private TextView labelInputLabel;
    private TextView mySecondsLabel;
    private TextView longestSecondsLabel;
    private TextView bufferSecondsLabel;
    private TextView flowSecondsLabel;
    private EditText labelInput;
    private EditText mySecondsInput;
    private EditText longestSecondsInput;
    private EditText bufferSecondsInput;
    private EditText flowSecondsInput;
    private EditText importCodeInput;
    private Button issueButton;
    private Button clearButton;
    private Button shareButton;
    private Button importButton;
    private Button overlayButton;
    private Button permissionButton;

    private long instructionEpochSeconds;
    private int mySeconds = 60;
    private int longestSeconds = 60;
    private int bufferSeconds = 15;
    private int flowSeconds = 300;
    private String activeLabel;
    private String language = "en";
    private boolean overlayEnabled;
    private boolean bindingLanguage;

    private final Runnable tick = new Runnable() {
        @Override
        public void run() {
            updateClock();
            handler.postDelayed(this, 1000);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        loadState();
        requestNotificationPermissionIfNeeded();
        setContentView(buildLayout());
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.post(tick);
        refreshPermissionState();
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (!overlayEnabled) {
            handler.removeCallbacks(tick);
        }
    }

    private View buildLayout() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(0xFF0D1117);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(dp(22), dp(28), dp(22), dp(24));
        scroll.addView(root);

        TextView title = text("Command Clock", 28, 0xFFF2F5F8, true);
        title.setGravity(Gravity.CENTER);
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));

        languageLabel = text("", 13, 0xFFF2F5F8, true);
        languageLabel.setPadding(0, 0, 0, dp(5));
        root.addView(languageLabel, new LinearLayout.LayoutParams(-1, -2));

        languageSpinner = new Spinner(this);
        languageSpinner.setBackground(border(0xFF1B2430, 0xFF58A6FF, 2));
        ArrayAdapter<String> adapter = new ArrayAdapter<String>(this, android.R.layout.simple_spinner_item, LANG_NAMES) {
            @Override
            public View getView(int position, View convertView, ViewGroup parent) {
                TextView view = (TextView) super.getView(position, convertView, parent);
                view.setTextColor(0xFFF2F5F8);
                view.setTextSize(17);
                view.setPadding(dp(14), dp(10), dp(14), dp(10));
                return view;
            }

            @Override
            public View getDropDownView(int position, View convertView, ViewGroup parent) {
                TextView view = (TextView) super.getDropDownView(position, convertView, parent);
                view.setTextColor(0xFF111820);
                view.setTextSize(16);
                view.setPadding(dp(14), dp(10), dp(14), dp(10));
                return view;
            }
        };
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        languageSpinner.setAdapter(adapter);
        bindingLanguage = true;
        languageSpinner.setSelection(languageIndex(language));
        bindingLanguage = false;
        languageSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (!bindingLanguage) {
                    setLanguage(LANG_CODES[position]);
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        root.addView(languageSpinner, new LinearLayout.LayoutParams(-1, -2));

        utcTime = text("", 20, 0xFF58A6FF, false);
        utcTime.setGravity(Gravity.CENTER);
        utcTime.setPadding(0, dp(18), 0, 0);
        root.addView(utcTime, new LinearLayout.LayoutParams(-1, -2));

        targetSummary = text("", 13, 0xFFA7B0BC, false);
        targetSummary.setGravity(Gravity.CENTER);
        targetSummary.setPadding(0, dp(6), 0, 0);
        root.addView(targetSummary, new LinearLayout.LayoutParams(-1, -2));

        countdownTitle = text("", 16, 0xFFF2F5F8, true);
        countdownTitle.setGravity(Gravity.CENTER);
        countdownTitle.setPadding(0, dp(18), 0, dp(2));
        root.addView(countdownTitle, new LinearLayout.LayoutParams(-1, -2));

        countdown = text("", 42, 0xFF3DDC97, true);
        countdown.setGravity(Gravity.CENTER);
        root.addView(countdown, new LinearLayout.LayoutParams(-1, -2));

        labelInputLabel = fieldLabel();
        root.addView(labelInputLabel, new LinearLayout.LayoutParams(-1, -2));
        labelInput = input();
        labelInput.setText(activeLabel);
        root.addView(labelInput, new LinearLayout.LayoutParams(-1, -2));

        mySecondsLabel = fieldLabel();
        root.addView(mySecondsLabel, new LinearLayout.LayoutParams(-1, -2));
        mySecondsInput = input();
        mySecondsInput.setText(formatDuration(mySeconds));
        root.addView(mySecondsInput, new LinearLayout.LayoutParams(-1, -2));

        longestSecondsLabel = fieldLabel();
        root.addView(longestSecondsLabel, new LinearLayout.LayoutParams(-1, -2));
        longestSecondsInput = input();
        longestSecondsInput.setText(formatDuration(longestSeconds));
        root.addView(longestSecondsInput, new LinearLayout.LayoutParams(-1, -2));

        bufferSecondsLabel = fieldLabel();
        root.addView(bufferSecondsLabel, new LinearLayout.LayoutParams(-1, -2));
        bufferSecondsInput = input();
        bufferSecondsInput.setText(formatDuration(bufferSeconds));
        root.addView(bufferSecondsInput, new LinearLayout.LayoutParams(-1, -2));

        flowSecondsLabel = fieldLabel();
        root.addView(flowSecondsLabel, new LinearLayout.LayoutParams(-1, -2));
        flowSecondsInput = input();
        flowSecondsInput.setText(formatDuration(flowSeconds));
        root.addView(flowSecondsInput, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout presetRow = row();
        int[] presets = {30, 60, 180, 300};
        String[] presetLabels = {"30s", "60s", "3m", "5m"};
        for (int i = 0; i < presets.length; i++) {
            int value = presets[i];
            Button button = new Button(this);
            button.setText(presetLabels[i]);
            button.setOnClickListener(v -> {
                    mySecondsInput.setText(formatDuration(value));
                setStatus(msg("Preset filled. Tap Issue instruction when values are ready.",
                        "プリセットを入力しました。設定値が揃ったら「指示開始」を押してください。"));
            });
            presetRow.addView(button, new LinearLayout.LayoutParams(0, -2, 1));
        }
        root.addView(presetRow, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout actionRow = row();
        issueButton = new Button(this);
        issueButton.setOnClickListener(v -> issueInstruction());
        actionRow.addView(issueButton, new LinearLayout.LayoutParams(0, -2, 1));
        clearButton = new Button(this);
        clearButton.setOnClickListener(v -> clearOperation());
        actionRow.addView(clearButton, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(actionRow, new LinearLayout.LayoutParams(-1, -2));

        TextView shareHeader = text("", 18, 0xFFF2F5F8, true);
        shareHeader.setGravity(Gravity.CENTER);
        shareHeader.setText(msg("Share code (optional)", "共有コード（任意）"));
        shareHeader.setPadding(0, dp(18), 0, dp(6));
        root.addView(shareHeader, new LinearLayout.LayoutParams(-1, -2));

        shareCodeView = text("", 13, 0xFFCAD1D9, false);
        shareCodeView.setTextIsSelectable(true);
        shareCodeView.setPadding(dp(10), dp(10), dp(10), dp(10));
        shareCodeView.setBackground(border(0xFF161B22, 0xFF2B3542, 1));
        root.addView(shareCodeView, new LinearLayout.LayoutParams(-1, -2));

        shareButton = new Button(this);
        shareButton.setOnClickListener(v -> generateShareCode());
        root.addView(shareButton, new LinearLayout.LayoutParams(-1, -2));

        importCodeInput = input();
        root.addView(importCodeInput, new LinearLayout.LayoutParams(-1, -2));

        importButton = new Button(this);
        importButton.setOnClickListener(v -> importShareCode());
        root.addView(importButton, new LinearLayout.LayoutParams(-1, -2));

        overlayButton = new Button(this);
        overlayButton.setOnClickListener(v -> toggleOverlay());
        root.addView(overlayButton, new LinearLayout.LayoutParams(-1, -2));

        permissionButton = new Button(this);
        permissionButton.setOnClickListener(v -> openOverlayPermission());
        root.addView(permissionButton, new LinearLayout.LayoutParams(-1, -2));

        status = text("", 13, 0xFFA7B0BC, false);
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, dp(14), 0, 0);
        root.addView(status, new LinearLayout.LayoutParams(-1, -2));

        applyLanguage();
        updateClock();
        return scroll;
    }

    private LinearLayout row() {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER);
        row.setPadding(0, dp(8), 0, 0);
        return row;
    }

    private EditText input() {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setTextColor(0xFFF2F5F8);
        input.setHintTextColor(0xFF8B949E);
        return input;
    }

    private TextView fieldLabel() {
        TextView view = text("", 13, 0xFFA7B0BC, true);
        view.setPadding(0, dp(12), 0, 0);
        return view;
    }

    private TextView text(String value, int size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        if (bold) {
            view.setTypeface(Typeface.DEFAULT_BOLD);
        }
        return view;
    }

    private GradientDrawable border(int fill, int stroke, int widthDp) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setCornerRadius(dp(8));
        drawable.setStroke(dp(widthDp), stroke);
        return drawable;
    }

    private void loadState() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        language = prefs.getString(KEY_LANGUAGE, defaultLanguage());
        overlayEnabled = prefs.getBoolean(KEY_OVERLAY, false);
        activeLabel = prefs.getString(KEY_LABEL, defaultLabel());
        instructionEpochSeconds = prefs.getLong(KEY_INSTRUCTION_EPOCH, 0L);
        mySeconds = prefs.getInt(KEY_MY_SECONDS, 60);
        longestSeconds = prefs.getInt(KEY_LONGEST_SECONDS, 60);
        bufferSeconds = prefs.getInt(KEY_BUFFER_SECONDS, 15);
        flowSeconds = prefs.getInt(KEY_FLOW_SECONDS, 300);
        if (instructionEpochSeconds > 0 && arrivalEpochSeconds() <= Instant.now().getEpochSecond()) {
            instructionEpochSeconds = 0L;
            overlayEnabled = false;
            prefs.edit().remove(KEY_INSTRUCTION_EPOCH).putBoolean(KEY_OVERLAY, false).apply();
        }
    }

    private void issueInstruction() {
        String label = labelInput.getText().toString().trim();
        int my = parseDuration(mySecondsInput.getText().toString().trim(), -1);
        int longest = parseDuration(longestSecondsInput.getText().toString().trim(), -1);
        int buffer = parseDuration(bufferSecondsInput.getText().toString().trim(), -1);
        int flow = parseDuration(flowSecondsInput.getText().toString().trim(), -1);
        if (label.isEmpty()) {
            label = defaultLabel();
        }
        if (my < 0 || longest <= 0 || buffer < 0 || flow < 0 || my > 7200 || longest > 7200 || buffer > 7200 || flow > 7200) {
            setStatus(msg("Use seconds from 0 to 7200. Longest time must be greater than 0.",
                    "秒数は0〜7200で入力してください。最長設定値は1秒以上が必要です。"));
            return;
        }
        if (my > longest) {
            setStatus(msg("My time cannot be longer than the longest time.",
                    "自分の設定値は、最長設定値より長くできません。"));
            return;
        }

        activeLabel = label;
        mySeconds = my;
        longestSeconds = longest;
        bufferSeconds = buffer;
        flowSeconds = flow;
        instructionEpochSeconds = Instant.now().getEpochSecond();
        saveState();
        setStatus(msg("Instruction issued. Press the game Start button when this countdown reaches zero.",
                "指示を開始しました。このカウントが0になったら、ゲーム側のスタートを押してください。"));
        updateClock();
    }

    private void clearOperation() {
        instructionEpochSeconds = 0L;
        activeLabel = defaultLabel();
        saveState();
        labelInput.setText(activeLabel);
        shareCodeView.setText("");
        setStatus(msg("Cleared.", "クリアしました。"));
        updateClock();
    }

    private void saveState() {
        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putString(KEY_LABEL, activeLabel)
                .putLong(KEY_INSTRUCTION_EPOCH, instructionEpochSeconds)
                .putInt(KEY_MY_SECONDS, mySeconds)
                .putInt(KEY_LONGEST_SECONDS, longestSeconds)
                .putInt(KEY_BUFFER_SECONDS, bufferSeconds)
                .putInt(KEY_FLOW_SECONDS, flowSeconds)
                .apply();
    }

    private void updateClock() {
        Instant now = Instant.now();
        String utc = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss 'UTC'")
                .withZone(ZoneOffset.UTC)
                .format(now);
        utcTime.setText(utc);

        if (instructionEpochSeconds <= 0) {
            countdownTitle.setText(msg("Waiting for instruction", "指示待機中"));
            countdown.setText("--:--");
            targetSummary.setText(msg("Set your values, then tap Issue instruction.",
                    "設定値を入力してから「指示開始」を押してください。"));
            updateOverlay("UTC " + utc + "\n" + countdownTitle.getText() + "\n--:--");
            return;
        }

        long nowEpoch = now.getEpochSecond();
        boolean waitingForStart = nowEpoch < pressStartEpochSeconds();
        long targetEpoch = waitingForStart ? pressStartEpochSeconds() : arrivalEpochSeconds();
        long remaining = Math.max(0, targetEpoch - nowEpoch);
        String value = formatDuration(remaining);
        countdownTitle.setText(waitingForStart
                ? msg("Press game Start in", "ゲーム側STARTまで")
                : msg("Arrival in", "同時到着まで"));
        countdown.setText(value);
        targetSummary.setText(syncSummary());
        updateOverlay("UTC " + utc + "\n" + countdownTitle.getText() + ": " + activeLabel + "\n" + value);
        if (waitingForStart && remaining == 0) {
            setStatus(msg("Press the game Start button now.",
                    "今、ゲーム側のスタートを押してください。"));
        } else if (!waitingForStart && remaining == 0) {
            setStatus(msg("Arrival time reached.", "到着時刻です。"));
        }
    }

    private long pressStartEpochSeconds() {
        return instructionEpochSeconds + bufferSeconds + (longestSeconds - mySeconds);
    }

    private long arrivalEpochSeconds() {
        return instructionEpochSeconds + bufferSeconds + longestSeconds + flowSeconds;
    }

    private String syncSummary() {
        String press = DateTimeFormatter.ofPattern("HH:mm:ss 'UTC'")
                .withZone(ZoneOffset.UTC)
                .format(Instant.ofEpochSecond(pressStartEpochSeconds()));
        String arrive = DateTimeFormatter.ofPattern("HH:mm:ss 'UTC'")
                .withZone(ZoneOffset.UTC)
                .format(Instant.ofEpochSecond(arrivalEpochSeconds()));
        return msg("Press: ", "押下: ") + press
                + " / " + msg("Arrival: ", "到着: ") + arrive
                + "\n" + msg("Buffer ", "猶予 ") + formatDuration(bufferSeconds)
                + " / " + msg("Flow ", "流れ ") + formatDuration(flowSeconds)
                + " / " + msg("My ", "自分 ") + formatDuration(mySeconds)
                + " / " + msg("Longest ", "最長 ") + formatDuration(longestSeconds);
    }

    private void generateShareCode() {
        if (instructionEpochSeconds <= 0) {
            setStatus(msg("Issue an instruction first.", "先に指示を開始してください。"));
            return;
        }
        String label = Base64.encodeToString(activeLabel.getBytes(StandardCharsets.UTF_8), Base64.URL_SAFE | Base64.NO_WRAP);
        String code = "CC2|" + instructionEpochSeconds + "|" + longestSeconds + "|" + bufferSeconds + "|" + flowSeconds + "|" + label;
        shareCodeView.setText(code);
        setStatus(msg("Share this code. Others import it, then set their own time.",
                "このコードを共有してください。受け取った人は取り込み後、自分の設定値を入力します。"));
    }

    private void importShareCode() {
        String code = importCodeInput.getText().toString().trim();
        String[] parts = code.split("\\|");
        if (parts.length != 6 || !"CC2".equals(parts[0])) {
            setStatus(msg("Invalid share code.", "共有コードが正しくありません。"));
            return;
        }
        try {
            instructionEpochSeconds = Long.parseLong(parts[1]);
            longestSeconds = Integer.parseInt(parts[2]);
            bufferSeconds = Integer.parseInt(parts[3]);
            flowSeconds = Integer.parseInt(parts[4]);
            activeLabel = new String(Base64.decode(parts[5], Base64.URL_SAFE | Base64.NO_WRAP), StandardCharsets.UTF_8);
            labelInput.setText(activeLabel);
            longestSecondsInput.setText(formatDuration(longestSeconds));
            bufferSecondsInput.setText(formatDuration(bufferSeconds));
            flowSecondsInput.setText(formatDuration(flowSeconds));
            saveState();
            setStatus(msg("Imported. Set your own time if needed.",
                    "取り込みました。必要なら自分の設定値を入力してください。"));
            updateClock();
        } catch (RuntimeException e) {
            setStatus(msg("Invalid share code.", "共有コードが正しくありません。"));
        }
    }

    private void toggleOverlay() {
        if (!Settings.canDrawOverlays(this)) {
            setStatus(msg("Allow floating display first, then tap the button again.",
                    "先に「重ねて表示」を許可してから、もう一度ボタンを押してください。"));
            openOverlayPermission();
            return;
        }
        overlayEnabled = !overlayEnabled;
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_OVERLAY, overlayEnabled).apply();
        startOverlayService(overlayEnabled ? CommandOverlayService.ACTION_SHOW : CommandOverlayService.ACTION_HIDE, null);
        applyLanguage();
        updateClock();
    }

    private void updateOverlay(String text) {
        if (overlayEnabled) {
            startOverlayService(CommandOverlayService.ACTION_UPDATE_TEXT, text);
        }
    }

    private void startOverlayService(String action, String text) {
        Intent intent = new Intent(this, CommandOverlayService.class);
        intent.setAction(action);
        if (text != null) {
            intent.putExtra(CommandOverlayService.EXTRA_TEXT, text);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
    }

    private void openOverlayPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            setStatus(msg(
                    "On Android 13+: tap the three-dot menu in the permission screen and select Allow restricted settings if the toggle is grayed out.",
                    "Android 13以降：許可画面で右上のメニューをタップし「制限付き設定を許可」を選択してください（トグルがグレーの場合）。"
            ));
        }
        Intent intent = new Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName())
        );
        startActivity(intent);
    }

    private void refreshPermissionState() {
        if (!Settings.canDrawOverlays(this) && overlayEnabled) {
            overlayEnabled = false;
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_OVERLAY, false).apply();
        }
        if (permissionButton != null) {
            permissionButton.setVisibility(Settings.canDrawOverlays(this) ? View.GONE : View.VISIBLE);
        }
        if (overlayButton != null) {
            overlayButton.setText(overlayEnabled
                    ? msg("Floating countdown: ON", "フローティング: ON")
                    : msg("Floating countdown: OFF", "フローティング: OFF"));
        }
        if (overlayEnabled && Settings.canDrawOverlays(this)) {
            startOverlayService(CommandOverlayService.ACTION_SHOW, null);
        }
    }

    private void requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQUEST_POST_NOTIFICATIONS);
        }
    }

    private void applyLanguage() {
        languageLabel.setText(msg("Language", "言語"));
        labelInputLabel.setText(msg("Operation name", "作戦名"));
        mySecondsLabel.setText(msg("My setting time (mm:ss)", "自分の設定値（mm:ss）"));
        longestSecondsLabel.setText(msg("Longest member setting (mm:ss)", "最長設定値（mm:ss）"));
        bufferSecondsLabel.setText(msg("Buffer after instruction (mm:ss)", "指示後の猶予時間（mm:ss）"));
        flowSecondsLabel.setText(msg("Flowing/rally time (mm:ss)", "流れている時間（mm:ss）"));
        labelInput.setHint(msg("Operation name", "作戦名"));
        mySecondsInput.setHint(msg("Example 01:30", "例 01:30"));
        longestSecondsInput.setHint(msg("Example 02:00", "例 02:00"));
        bufferSecondsInput.setHint(msg("Example 00:15", "例 00:15"));
        flowSecondsInput.setHint(msg("Example 05:00", "例 05:00"));
        issueButton.setText(msg("Issue instruction", "指示開始"));
        clearButton.setText(msg("Clear", "クリア"));
        shareButton.setText(msg("Create share code", "共有コード作成"));
        importCodeInput.setHint(msg("Paste share code", "共有コードを貼り付け"));
        importButton.setText(msg("Import shared instruction", "共有指示を取り込む"));
        overlayButton.setText(overlayEnabled
                ? msg("Floating countdown: ON", "フローティング: ON")
                : msg("Floating countdown: OFF", "フローティング: OFF"));
        permissionButton.setText(msg("Allow floating display", "重ねて表示を許可"));
        if (shareCodeView.getText().length() == 0) {
            shareCodeView.setText(msg("Issue an instruction, then create a code. Others can import it and use their own time.",
                    "指示開始後にコードを作成できます。受け取った人は取り込み、自分の設定値で使えます。"));
        }
        refreshPermissionState();
    }

    private String defaultLabel() {
        return msg("Next operation", "次の作戦");
    }

    private void setLanguage(String nextLanguage) {
        language = nextLanguage;
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_LANGUAGE, language).apply();
        applyLanguage();
        updateClock();
    }

    private String msg(String en, String ja) {
        return "ja".equals(language) ? ja : en;
    }

    private int parseDuration(String value, int fallback) {
        String normalized = value.trim().toLowerCase(Locale.US);
        if (normalized.isEmpty()) {
            return fallback;
        }
        try {
            if (normalized.endsWith("m")) {
                return Integer.parseInt(normalized.substring(0, normalized.length() - 1).trim()) * 60;
            }
            if (normalized.endsWith("s")) {
                return Integer.parseInt(normalized.substring(0, normalized.length() - 1).trim());
            }
            if (normalized.contains(":")) {
                String[] parts = normalized.split(":");
                if (parts.length == 2) {
                    int minutes = Integer.parseInt(parts[0].trim());
                    int seconds = Integer.parseInt(parts[1].trim());
                    if (seconds < 0 || seconds > 59) {
                        return fallback;
                    }
                    return minutes * 60 + seconds;
                }
                if (parts.length == 3) {
                    int hours = Integer.parseInt(parts[0].trim());
                    int minutes = Integer.parseInt(parts[1].trim());
                    int seconds = Integer.parseInt(parts[2].trim());
                    if (minutes < 0 || minutes > 59 || seconds < 0 || seconds > 59) {
                        return fallback;
                    }
                    return hours * 3600 + minutes * 60 + seconds;
                }
                return fallback;
            }
            return Integer.parseInt(normalized);
        } catch (NumberFormatException e) {
            return fallback;
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

    private int languageIndex(String code) {
        for (int i = 0; i < LANG_CODES.length; i++) {
            if (LANG_CODES[i].equals(code)) {
                return i;
            }
        }
        return 0;
    }

    private String defaultLanguage() {
        String deviceLanguage = Locale.getDefault().getLanguage();
        for (String code : LANG_CODES) {
            if (code.equals(deviceLanguage)) {
                return code;
            }
        }
        return "en";
    }

    private void setStatus(String message) {
        if (status != null) {
            status.setText(message);
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
