package com.tactnodelabs.commandclock;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
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
import android.widget.Switch;
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
    private static final String KEY_SHOW_UTC = "show_utc";
    private static final String KEY_SHOW_PHASE = "show_phase";
    private static final String KEY_SHOW_COUNTDOWN = "show_countdown";
    private static final String KEY_SHOW_ARRIVAL = "show_arrival";
    private static final int REQUEST_POST_NOTIFICATIONS = 4101;
    private static final int REQUEST_OVERLAY_PERMISSION = 4102;

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
    private TextView shareHeader;
    private TextView shareCodeView;
    private TextView status;
    private TextView labelInputLabel;
    private TextView mySecondsLabel;
    private TextView longestSecondsLabel;
    private TextView bufferSecondsLabel;
    private TextView flowSecondsLabel;
    private TextView arrivalPreviewLabel;
    private TextView overlaySettingsLabel;
    private TextView showUtcLabel;
    private TextView showPhaseLabel;
    private TextView showCountdownLabel;
    private TextView showArrivalLabel;
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
    private Switch showUtcSwitch;
    private Switch showPhaseSwitch;
    private Switch showCountdownSwitch;
    private Switch showArrivalSwitch;

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

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_OVERLAY_PERMISSION) {
            handler.postDelayed(this::refreshPermissionState, 500);
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

        LinearLayout languageBox = new LinearLayout(this);
        languageBox.setOrientation(LinearLayout.VERTICAL);
        languageBox.setBackground(border(0xFF161B22, 0xFF58A6FF, 2));
        languageBox.setPadding(dp(12), dp(10), dp(12), dp(10));

        languageLabel = text("", 13, 0xFFF2F5F8, true);
        languageLabel.setPadding(0, 0, 0, dp(5));
        languageBox.addView(languageLabel, new LinearLayout.LayoutParams(-1, -2));

        languageSpinner = new Spinner(this);
        languageSpinner.setBackground(border(0xFF1C2A3A, 0xFF58A6FF, 2));
        ArrayAdapter<String> adapter = new ArrayAdapter<String>(this, android.R.layout.simple_spinner_item, LANG_NAMES) {
            @Override
            public View getView(int position, View convertView, ViewGroup parent) {
                TextView view = (TextView) super.getView(position, convertView, parent);
                view.setTextColor(0xFF58A6FF);
                view.setTextSize(19);
                view.setTypeface(null, Typeface.BOLD);
                view.setPadding(dp(14), dp(12), dp(14), dp(12));
                return view;
            }

            @Override
            public View getDropDownView(int position, View convertView, ViewGroup parent) {
                TextView view = (TextView) super.getDropDownView(position, convertView, parent);
                view.setTextColor(0xFF111820);
                view.setTextSize(17);
                view.setPadding(dp(14), dp(12), dp(14), dp(12));
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
        languageBox.addView(languageSpinner, new LinearLayout.LayoutParams(-1, -2));
        root.addView(languageBox, new LinearLayout.LayoutParams(-1, -2));

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
                setStatus(msg(
                        "Preset filled. Tap Issue instruction when values are ready.",
                        "プリセットを入力しました。設定値が揃ったら「指示開始」を押してください。",
                        "프리셋을 입력했습니다. 값이 준비되면 \"지시 시작\"을 누르세요.",
                        "已填入预设。数值就绪后点按“发出指示”。",
                        "กรอกพรีเซ็ตแล้ว แตะ \"เริ่มคำสั่ง\" เมื่อพร้อม",
                        "Prasetel diisi. Ketuk Terbitkan instruksi saat nilai siap.",
                        "Preajuste rellenado. Toca Emitir instrucción cuando los valores estén listos.",
                        "Predefinição preenchida. Toque em Emitir instrução quando os valores estiverem prontos.",
                        "Préréglage rempli. Appuyez sur Lancer l'instruction quand les valeurs sont prêtes.",
                        "Voreinstellung eingetragen. Tippen Sie auf Anweisung starten, wenn die Werte bereit sind."));
            });
            presetRow.addView(button, new LinearLayout.LayoutParams(0, -2, 1));
        }
        root.addView(presetRow, new LinearLayout.LayoutParams(-1, -2));

        arrivalPreviewLabel = text("", 14, 0xFFA7B0BC, true);
        arrivalPreviewLabel.setGravity(Gravity.CENTER);
        arrivalPreviewLabel.setPadding(0, dp(10), 0, dp(4));
        root.addView(arrivalPreviewLabel, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout actionRow = row();
        issueButton = new Button(this);
        issueButton.setOnClickListener(v -> issueInstruction());
        actionRow.addView(issueButton, new LinearLayout.LayoutParams(0, -2, 1));
        clearButton = new Button(this);
        clearButton.setOnClickListener(v -> clearOperation());
        actionRow.addView(clearButton, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(actionRow, new LinearLayout.LayoutParams(-1, -2));

        shareHeader = text("", 18, 0xFFF2F5F8, true);
        shareHeader.setGravity(Gravity.CENTER);
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

        overlaySettingsLabel = text("", 16, 0xFFF2F5F8, true);
        overlaySettingsLabel.setGravity(Gravity.CENTER);
        overlaySettingsLabel.setPadding(0, dp(16), 0, dp(4));
        root.addView(overlaySettingsLabel, new LinearLayout.LayoutParams(-1, -2));

        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        showUtcSwitch = new Switch(this);
        showUtcSwitch.setChecked(prefs.getBoolean(KEY_SHOW_UTC, true));
        showUtcLabel = overlaySettingRow(root, showUtcSwitch);

        showPhaseSwitch = new Switch(this);
        showPhaseSwitch.setChecked(prefs.getBoolean(KEY_SHOW_PHASE, true));
        showPhaseLabel = overlaySettingRow(root, showPhaseSwitch);

        showCountdownSwitch = new Switch(this);
        showCountdownSwitch.setChecked(prefs.getBoolean(KEY_SHOW_COUNTDOWN, true));
        showCountdownLabel = overlaySettingRow(root, showCountdownSwitch);

        showArrivalSwitch = new Switch(this);
        showArrivalSwitch.setChecked(prefs.getBoolean(KEY_SHOW_ARRIVAL, true));
        showArrivalLabel = overlaySettingRow(root, showArrivalSwitch);

        showUtcSwitch.setOnCheckedChangeListener((button, checked) -> updateOverlayDisplaySetting(KEY_SHOW_UTC, checked));
        showPhaseSwitch.setOnCheckedChangeListener((button, checked) -> updateOverlayDisplaySetting(KEY_SHOW_PHASE, checked));
        showCountdownSwitch.setOnCheckedChangeListener((button, checked) -> updateOverlayDisplaySetting(KEY_SHOW_COUNTDOWN, checked));
        showArrivalSwitch.setOnCheckedChangeListener((button, checked) -> updateOverlayDisplaySetting(KEY_SHOW_ARRIVAL, checked));

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

    private TextView overlaySettingRow(LinearLayout root, Switch settingSwitch) {
        LinearLayout line = new LinearLayout(this);
        line.setOrientation(LinearLayout.HORIZONTAL);
        line.setGravity(Gravity.CENTER_VERTICAL);
        line.setPadding(dp(10), dp(6), dp(10), dp(6));
        line.setBackground(border(0xFF0D1117, 0xFF30363D, 1));

        TextView label = text("", 14, 0xFFE6EDF3, true);
        line.addView(label, new LinearLayout.LayoutParams(0, -2, 1));

        tintSwitch(settingSwitch);
        line.addView(settingSwitch, new LinearLayout.LayoutParams(-2, -2));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.setMargins(0, dp(6), 0, 0);
        root.addView(line, params);
        return label;
    }

    private void tintSwitch(Switch settingSwitch) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            int[][] states = new int[][]{
                    new int[]{android.R.attr.state_checked},
                    new int[]{-android.R.attr.state_checked}
            };
            settingSwitch.setThumbTintList(new ColorStateList(states, new int[]{0xFF58A6FF, 0xFF8B949E}));
            settingSwitch.setTrackTintList(new ColorStateList(states, new int[]{0x6658A6FF, 0x3330363D}));
        }
    }

    private void updateOverlayDisplaySetting(String key, boolean checked) {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(key, checked).apply();
        if (overlayEnabled) {
            startOverlayService(CommandOverlayService.ACTION_SHOW, null);
            updateClock();
        }
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
            setStatus(msg(
                    "Use seconds from 0 to 7200. Longest time must be greater than 0.",
                    "秒数は0〜7200で入力してください。最長設定値は1秒以上が必要です。",
                    "0~7200초로 입력하세요. 최장 시간은 0보다 커야 합니다.",
                    "请使用 0 到 7200 秒。最长设置必须大于 0。",
                    "ใช้วินาที 0-7200 เวลานานสุดต้องมากกว่า 0",
                    "Gunakan detik 0-7200. Waktu terpanjang harus lebih dari 0.",
                    "Usa segundos de 0 a 7200. El tiempo más largo debe ser mayor que 0.",
                    "Use segundos de 0 a 7200. O tempo mais longo deve ser maior que 0.",
                    "Utilisez des secondes de 0 à 7200. Le temps le plus long doit être supérieur à 0.",
                    "Verwenden Sie Sekunden von 0 bis 7200. Die längste Zeit muss größer als 0 sein."));
            return;
        }
        if (my > longest) {
            setStatus(msg(
                    "My time cannot be longer than the longest time.",
                    "自分の設定値は、最長設定値より長くできません。",
                    "내 시간은 최장 시간보다 길 수 없습니다.",
                    "我的时间不能长于最长时间。",
                    "เวลาของฉันต้องไม่ยาวกว่าเวลานานสุด",
                    "Waktu saya tidak boleh lebih lama dari waktu terpanjang.",
                    "Mi tiempo no puede ser mayor que el tiempo más largo.",
                    "Meu tempo não pode ser maior que o tempo mais longo.",
                    "Mon temps ne peut pas être plus long que le temps le plus long.",
                    "Meine Zeit darf nicht länger als die längste Zeit sein."));
            return;
        }

        activeLabel = label;
        mySeconds = my;
        longestSeconds = longest;
        bufferSeconds = buffer;
        flowSeconds = flow;
        instructionEpochSeconds = Instant.now().getEpochSecond();
        saveState();
        setStatus(msg(
                "Instruction issued. Press the game Start button when this countdown reaches zero.",
                "指示を開始しました。このカウントが0になったら、ゲーム側のスタートを押してください。",
                "지시를 시작했습니다. 카운트가 0이 되면 게임의 Start를 누르세요.",
                "指示已发出。倒计时为零时请按下游戏中的开始。",
                "เริ่มคำสั่งแล้ว กด Start ในเกมเมื่อนับถอยหลังถึง 0",
                "Instruksi diterbitkan. Tekan Start game saat hitungan mencapai nol.",
                "Instrucción emitida. Pulsa Start del juego cuando la cuenta llegue a cero.",
                "Instrução emitida. Pressione Start do jogo quando a contagem chegar a zero.",
                "Instruction lancée. Appuyez sur Start du jeu quand le compte atteint zéro.",
                "Anweisung gestartet. Drücken Sie Spiel-Start, wenn der Countdown null erreicht."));
        updateClock();
    }

    private void clearOperation() {
        instructionEpochSeconds = 0L;
        activeLabel = defaultLabel();
        saveState();
        labelInput.setText(activeLabel);
        shareCodeView.setText("");
        setStatus(msg("Cleared.", "クリアしました。", "초기화했습니다.", "已清除。", "ล้างแล้ว", "Dihapus.", "Borrado.", "Limpo.", "Effacé.", "Zurückgesetzt."));
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
        updateArrivalPreview(now);

        if (instructionEpochSeconds <= 0) {
            countdownTitle.setText(msg("Waiting for instruction", "指示待機中", "지시 대기 중", "等待指示", "รอคำสั่ง", "Menunggu instruksi", "Esperando instrucción", "Aguardando instrução", "En attente d'instruction", "Warte auf Anweisung"));
            countdown.setText("--:--");
            targetSummary.setText(msg(
                    "Set your values, then tap Issue instruction.",
                    "設定値を入力してから「指示開始」を押してください。",
                    "값을 입력한 뒤 \"지시 시작\"을 누르세요.",
                    "设置数值后点按“发出指示”。",
                    "ตั้งค่าแล้วแตะ \"เริ่มคำสั่ง\"",
                    "Atur nilai, lalu ketuk Terbitkan instruksi.",
                    "Configura los valores y toca Emitir instrucción.",
                    "Defina os valores e toque em Emitir instrução.",
                    "Définissez les valeurs, puis appuyez sur Lancer l'instruction.",
                    "Werte eingeben, dann Anweisung starten."));
            updateOverlay("UTC " + utc + "\n" + countdownTitle.getText() + "\n--:--");
            return;
        }

        long nowEpoch = now.getEpochSecond();
        boolean waitingForStart = nowEpoch < pressStartEpochSeconds();
        long targetEpoch = waitingForStart ? pressStartEpochSeconds() : arrivalEpochSeconds();
        long remaining = Math.max(0, targetEpoch - nowEpoch);
        String value = formatDuration(remaining);
        countdownTitle.setText(waitingForStart
                ? msg("Press game Start in", "ゲーム側STARTまで", "게임 START까지", "距按下游戏开始", "กด START ในเกมใน", "Tekan Start game dalam", "Pulsar Start del juego en", "Pressionar Start do jogo em", "Appuyer sur Start du jeu dans", "Spiel-Start in")
                : msg("Arrival in", "同時到着まで", "동시 도착까지", "距同时到达", "ถึงพร้อมกันใน", "Tiba bersamaan dalam", "Llegada simultánea en", "Chegada simultânea em", "Arrivée simultanée dans", "Gleichzeitige Ankunft in"));
        countdown.setText(value);
        targetSummary.setText(syncSummary());
        updateOverlay("UTC " + utc + "\n" + countdownTitle.getText() + ": " + activeLabel + "\n" + value);
        if (waitingForStart && remaining == 0) {
            setStatus(msg(
                    "Press the game Start button now.",
                    "今、ゲーム側のスタートを押してください。",
                    "지금 게임의 Start를 누르세요.",
                    "请现在按下游戏中的开始。",
                    "กด Start ในเกมตอนนี้",
                    "Tekan tombol Start game sekarang.",
                    "Pulsa el botón Start del juego ahora.",
                    "Pressione o botão Start do jogo agora.",
                    "Appuyez sur le bouton Start du jeu maintenant.",
                    "Drücken Sie jetzt die Spiel-Start-Taste."));
        } else if (!waitingForStart && remaining == 0) {
            setStatus(msg("Arrival time reached.", "到着時刻です。", "도착 시각입니다.", "已到达时刻。", "ถึงเวลาแล้ว", "Waktu tiba tercapai.", "Hora de llegada alcanzada.", "Hora de chegada atingida.", "Heure d'arrivée atteinte.", "Ankunftszeit erreicht."));
        }
    }

    private long pressStartEpochSeconds() {
        return instructionEpochSeconds + bufferSeconds + (longestSeconds - mySeconds);
    }

    private long arrivalEpochSeconds() {
        return instructionEpochSeconds + bufferSeconds + longestSeconds + flowSeconds;
    }

    private void updateArrivalPreview(Instant now) {
        long base = instructionEpochSeconds > 0 ? instructionEpochSeconds : now.getEpochSecond();
        int longest = inputDurationOrCurrent(longestSecondsInput, longestSeconds);
        int buffer = inputDurationOrCurrent(bufferSecondsInput, bufferSeconds);
        int flow = inputDurationOrCurrent(flowSecondsInput, flowSeconds);
        long arrivalEpoch = base + buffer + longest + flow;
        String arrival = DateTimeFormatter.ofPattern("HH:mm:ss")
                .withZone(ZoneOffset.UTC)
                .format(Instant.ofEpochSecond(arrivalEpoch));
        arrivalPreviewLabel.setText(arrivalLabel() + " " + arrival);
    }

    private int inputDurationOrCurrent(EditText input, int currentValue) {
        if (input == null) {
            return currentValue;
        }
        int parsed = parseDuration(input.getText().toString().trim(), currentValue);
        return parsed < 0 ? currentValue : parsed;
    }

    private String arrivalLabel() {
        return msg("Arrival", "到着", "도착", "到达", "ถึง", "Tiba", "Llegada", "Chegada", "Arrivée", "Ankunft");
    }

    private String syncSummary() {
        String press = DateTimeFormatter.ofPattern("HH:mm:ss 'UTC'")
                .withZone(ZoneOffset.UTC)
                .format(Instant.ofEpochSecond(pressStartEpochSeconds()));
        String arrive = DateTimeFormatter.ofPattern("HH:mm:ss 'UTC'")
                .withZone(ZoneOffset.UTC)
                .format(Instant.ofEpochSecond(arrivalEpochSeconds()));
        return msg("Press: ", "押下: ", "누름: ", "按下: ", "กด: ", "Tekan: ", "Pulsar: ", "Pressionar: ", "Appui: ", "Drücken: ") + press
                + " / " + msg("Arrival: ", "到着: ", "도착: ", "到达: ", "ถึง: ", "Tiba: ", "Llegada: ", "Chegada: ", "Arrivée: ", "Ankunft: ") + arrive
                + "\n" + msg("Buffer ", "猶予 ", "여유 ", "缓冲 ", "พัก ", "Penyangga ", "Margen ", "Folga ", "Tampon ", "Puffer ") + formatDuration(bufferSeconds)
                + " / " + msg("Flow ", "流れ ", "진행 ", "流动 ", "ไหล ", "Alur ", "Flujo ", "Fluxo ", "Flux ", "Fluss ") + formatDuration(flowSeconds)
                + " / " + msg("My ", "自分 ", "내 ", "我的 ", "ฉัน ", "Saya ", "Mi ", "Meu ", "Mon ", "Mein ") + formatDuration(mySeconds)
                + " / " + msg("Longest ", "最長 ", "최장 ", "最长 ", "นานสุด ", "Terpanjang ", "Más largo ", "Mais longo ", "Plus long ", "Längste ") + formatDuration(longestSeconds);
    }

    private void generateShareCode() {
        if (instructionEpochSeconds <= 0) {
            setStatus(msg("Issue an instruction first.", "先に指示を開始してください。", "먼저 지시를 시작하세요.", "请先发出指示。", "เริ่มคำสั่งก่อน", "Terbitkan instruksi terlebih dahulu.", "Emite una instrucción primero.", "Emita uma instrução primeiro.", "Lancez d'abord une instruction.", "Starten Sie zuerst eine Anweisung."));
            return;
        }
        String label = Base64.encodeToString(activeLabel.getBytes(StandardCharsets.UTF_8), Base64.URL_SAFE | Base64.NO_WRAP);
        String code = "CC2|" + instructionEpochSeconds + "|" + longestSeconds + "|" + bufferSeconds + "|" + flowSeconds + "|" + label;
        shareCodeView.setText(code);
        setStatus(msg(
                "Share this code. Others import it, then set their own time.",
                "このコードを共有してください。受け取った人は取り込み後、自分の設定値を入力します。",
                "이 코드를 공유하세요. 다른 사람은 가져온 뒤 자신의 시간을 설정합니다.",
                "分享此代码。其他人导入后设置自己的时间。",
                "แชร์รหัสนี้ ผู้อื่นนำเข้าแล้วตั้งเวลาของตนเอง",
                "Bagikan kode ini. Orang lain mengimpornya lalu mengatur waktu mereka sendiri.",
                "Comparte este código. Otros lo importan y luego configuran su propio tiempo.",
                "Compartilhe este código. Outros importam e depois definem o próprio tempo.",
                "Partagez ce code. Les autres l'importent puis définissent leur propre temps.",
                "Teilen Sie diesen Code. Andere importieren ihn und legen dann ihre eigene Zeit fest."));
    }

    private void importShareCode() {
        String code = importCodeInput.getText().toString().trim();
        String[] parts = code.split("\\|");
        if (parts.length != 6 || !"CC2".equals(parts[0])) {
            setStatus(msg("Invalid share code.", "共有コードが正しくありません。", "공유 코드가 올바르지 않습니다.", "共享代码无效。", "รหัสแชร์ไม่ถูกต้อง", "Kode berbagi tidak valid.", "Código compartido no válido.", "Código compartilhado inválido.", "Code de partage invalide.", "Freigabecode ungültig."));
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
            setStatus(msg(
                    "Imported. Set your own time if needed.",
                    "取り込みました。必要なら自分の設定値を入力してください。",
                    "가져왔습니다. 필요하면 자신의 시간을 설정하세요.",
                    "已导入。如需要请设置您的时间。",
                    "นำเข้าแล้ว ตั้งเวลาของคุณหากจำเป็น",
                    "Diimpor. Atur waktu Anda sendiri jika perlu.",
                    "Importado. Configura tu propio tiempo si es necesario.",
                    "Importado. Defina seu próprio tempo se necessário.",
                    "Importé. Définissez votre propre temps si nécessaire.",
                    "Importiert. Legen Sie bei Bedarf Ihre eigene Zeit fest."));
            updateClock();
        } catch (RuntimeException e) {
            setStatus(msg("Invalid share code.", "共有コードが正しくありません。", "공유 코드가 올바르지 않습니다.", "共享代码无效。", "รหัสแชร์ไม่ถูกต้อง", "Kode berbagi tidak valid.", "Código compartido no válido.", "Código compartilhado inválido.", "Code de partage invalide.", "Freigabecode ungültig."));
        }
    }

    private void toggleOverlay() {
        if (!Settings.canDrawOverlays(this)) {
            setStatus(msg(
                    "Tap \"Allow floating display\" below to enable this feature.",
                    "下の「重ねて表示を許可」をタップして機能を有効にしてください。",
                    "아래 \"다른 앱 위에 표시 허용\"을 눌러 이 기능을 활성화하세요.",
                    "请点按下方的“允许悬浮显示”以启用此功能。",
                    "แตะ \"อนุญาตการแสดงทับ\" ด้านล่างเพื่อเปิดใช้งาน",
                    "Ketuk \"Izinkan tampilan mengambang\" di bawah untuk mengaktifkan fitur ini.",
                    "Toca \"Permitir visualización flotante\" abajo para activar esta función.",
                    "Toque em \"Permitir exibição flutuante\" abaixo para ativar este recurso.",
                    "Appuyez sur \"Autoriser l'affichage flottant\" ci-dessous pour activer cette fonction.",
                    "Tippen Sie unten auf \"Schwebende Anzeige erlauben\", um diese Funktion zu aktivieren."));
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
        launchOverlayPermissionSettings();
    }

    private void launchOverlayPermissionSettings() {
        Intent intent = new Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName())
        );
        startActivityForResult(intent, REQUEST_OVERLAY_PERMISSION);
    }

    private boolean prevCanDraw = false;

    private void refreshPermissionState() {
        boolean canDraw = Settings.canDrawOverlays(this);
        boolean justGranted = canDraw && !prevCanDraw;
        prevCanDraw = canDraw;

        if (!canDraw && overlayEnabled) {
            overlayEnabled = false;
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_OVERLAY, false).apply();
        }
        if (permissionButton != null) {
            permissionButton.setVisibility(canDraw ? View.GONE : View.VISIBLE);
        }
        if (overlayButton != null) {
            overlayButton.setEnabled(canDraw);
            overlayButton.setAlpha(canDraw ? 1.0f : 0.4f);
            overlayButton.setText(overlayEnabled
                    ? msg("Floating countdown: ON", "フローティング: ON", "플로팅: ON", "浮动显示: 开", "ลอย: เปิด", "Mengambang: ON", "Flotante: ON", "Flutuante: ON", "Flottant: ON", "Schwebend: AN")
                    : msg("Floating countdown: OFF", "フローティング: OFF", "플로팅: OFF", "浮动显示: 关", "ลอย: ปิด", "Mengambang: OFF", "Flotante: OFF", "Flutuante: OFF", "Flottant: OFF", "Schwebend: AUS"));
        }
        if (justGranted && !overlayEnabled) {
            // Auto-enable the overlay the first time permission is granted
            overlayEnabled = true;
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_OVERLAY, true).apply();
            if (overlayButton != null) {
                overlayButton.setText(msg("Floating countdown: ON", "フローティング: ON", "플로팅: ON", "浮动显示: 开", "ลอย: เปิด", "Mengambang: ON", "Flotante: ON", "Flutuante: ON", "Flottant: ON", "Schwebend: AN"));
            }
        }
        if (canDraw && overlayEnabled) {
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
        languageLabel.setText(msg("Language", "言語", "언어", "语言", "ภาษา", "Bahasa", "Idioma", "Idioma", "Langue", "Sprache"));
        labelInputLabel.setText(msg("Operation name", "作戦名", "작전 이름", "任务名称", "ชื่อปฏิบัติการ", "Nama operasi", "Nombre de operación", "Nome da operação", "Nom de l'opération", "Einsatzname"));
        mySecondsLabel.setText(msg("My setting time (mm:ss)", "自分の設定値（mm:ss）", "내 설정 시간 (mm:ss)", "我的设置时间 (mm:ss)", "เวลาตั้งค่าของฉัน (mm:ss)", "Waktu pengaturan saya (mm:ss)", "Mi tiempo de ajuste (mm:ss)", "Meu tempo de ajuste (mm:ss)", "Mon temps de réglage (mm:ss)", "Meine Einstellzeit (mm:ss)"));
        longestSecondsLabel.setText(msg("Longest member setting (mm:ss)", "最長設定値（mm:ss）", "최장 멤버 설정 (mm:ss)", "最长成员设置 (mm:ss)", "สมาชิกที่นานที่สุด (mm:ss)", "Pengaturan anggota terpanjang (mm:ss)", "Ajuste del miembro más largo (mm:ss)", "Ajuste do membro mais longo (mm:ss)", "Réglage du membre le plus long (mm:ss)", "Längste Mitglieder-Einstellung (mm:ss)"));
        bufferSecondsLabel.setText(msg("Buffer after instruction (mm:ss)", "指示後の猶予時間（mm:ss）", "지시 후 여유 시간 (mm:ss)", "指示后缓冲时间 (mm:ss)", "เวลาพักหลังคำสั่ง (mm:ss)", "Waktu penyangga setelah instruksi (mm:ss)", "Tiempo de margen tras la instrucción (mm:ss)", "Tempo de folga após instrução (mm:ss)", "Temps tampon après instruction (mm:ss)", "Puffer nach Anweisung (mm:ss)"));
        flowSecondsLabel.setText(msg("Flowing/rally time (mm:ss)", "流れている時間（mm:ss）", "진행/집결 시간 (mm:ss)", "流动/集结时间 (mm:ss)", "เวลาไหล/รวมตัว (mm:ss)", "Waktu alur/rally (mm:ss)", "Tiempo de flujo/reunión (mm:ss)", "Tempo de fluxo/reunião (mm:ss)", "Temps de flux/rassemblement (mm:ss)", "Fluss-/Sammelzeit (mm:ss)"));
        labelInput.setHint(msg("Operation name", "作戦名", "작전 이름", "任务名称", "ชื่อปฏิบัติการ", "Nama operasi", "Nombre de operación", "Nome da operação", "Nom de l'opération", "Einsatzname"));
        mySecondsInput.setHint(msg("Example 01:30", "例 01:30", "예 01:30", "例 01:30", "ตัวอย่าง 01:30", "Contoh 01:30", "Ejemplo 01:30", "Exemplo 01:30", "Exemple 01:30", "Beispiel 01:30"));
        longestSecondsInput.setHint(msg("Example 02:00", "例 02:00", "예 02:00", "例 02:00", "ตัวอย่าง 02:00", "Contoh 02:00", "Ejemplo 02:00", "Exemplo 02:00", "Exemple 02:00", "Beispiel 02:00"));
        bufferSecondsInput.setHint(msg("Example 00:15", "例 00:15", "예 00:15", "例 00:15", "ตัวอย่าง 00:15", "Contoh 00:15", "Ejemplo 00:15", "Exemplo 00:15", "Exemple 00:15", "Beispiel 00:15"));
        flowSecondsInput.setHint(msg("Example 05:00", "例 05:00", "예 05:00", "例 05:00", "ตัวอย่าง 05:00", "Contoh 05:00", "Ejemplo 05:00", "Exemplo 05:00", "Exemple 05:00", "Beispiel 05:00"));
        issueButton.setText(msg("Issue instruction", "指示開始", "지시 시작", "发出指示", "เริ่มคำสั่ง", "Terbitkan instruksi", "Emitir instrucción", "Emitir instrução", "Lancer l'instruction", "Anweisung starten"));
        clearButton.setText(msg("Clear", "クリア", "초기화", "清除", "ล้าง", "Hapus", "Borrar", "Limpar", "Effacer", "Zurücksetzen"));
        shareHeader.setText(msg("Share code (optional)", "共有コード（任意）", "공유 코드 (선택)", "共享代码（可选）", "รหัสแชร์ (ไม่บังคับ)", "Kode berbagi (opsional)", "Código compartido (opcional)", "Código compartilhado (opcional)", "Code de partage (optionnel)", "Freigabecode (optional)"));
        shareButton.setText(msg("Create share code", "共有コード作成", "공유 코드 생성", "创建共享代码", "สร้างรหัสแชร์", "Buat kode berbagi", "Crear código compartido", "Criar código compartilhado", "Créer un code de partage", "Freigabecode erstellen"));
        importCodeInput.setHint(msg("Paste share code", "共有コードを貼り付け", "공유 코드 붙여넣기", "粘贴共享代码", "วางรหัสแชร์", "Tempel kode berbagi", "Pegar código compartido", "Colar código compartilhado", "Coller le code de partage", "Freigabecode einfügen"));
        importButton.setText(msg("Import shared instruction", "共有指示を取り込む", "공유 지시 가져오기", "导入共享指示", "นำเข้าคำสั่งที่แชร์", "Impor instruksi bersama", "Importar instrucción compartida", "Importar instrução compartilhada", "Importer l'instruction partagée", "Geteilte Anweisung importieren"));
        overlayButton.setText(overlayEnabled
                ? msg("Floating countdown: ON", "フローティング: ON", "플로팅: ON", "浮动显示: 开", "ลอย: เปิด", "Mengambang: ON", "Flotante: ON", "Flutuante: ON", "Flottant: ON", "Schwebend: AN")
                : msg("Floating countdown: OFF", "フローティング: OFF", "플로팅: OFF", "浮动显示: 关", "ลอย: ปิด", "Mengambang: OFF", "Flotante: OFF", "Flutuante: OFF", "Flottant: OFF", "Schwebend: AUS"));
        permissionButton.setText(msg("Allow floating display", "重ねて表示を許可", "다른 앱 위에 표시 허용", "允许悬浮显示", "อนุญาตการแสดงทับ", "Izinkan tampilan mengambang", "Permitir visualización flotante", "Permitir exibição flutuante", "Autoriser l'affichage flottant", "Schwebende Anzeige erlauben"));
        overlaySettingsLabel.setText(msg("Floating display settings", "フローティング表示設定", "플로팅 표시 설정", "浮动显示设置", "ตั้งค่าการแสดงลอย", "Pengaturan tampilan mengambang", "Ajustes de visualización flotante", "Configurações de exibição flutuante", "Paramètres d'affichage flottant", "Einstellungen fuer schwebende Anzeige"));
        showUtcLabel.setText(msg("UTC time", "UTC時刻", "UTC 시간", "UTC 时间", "เวลา UTC", "Waktu UTC", "Hora UTC", "Hora UTC", "Heure UTC", "UTC-Zeit"));
        showPhaseLabel.setText(msg("Phase", "フェーズ", "단계", "阶段", "ช่วง", "Fase", "Fase", "Fase", "Phase", "Phase"));
        showCountdownLabel.setText(msg("Countdown", "カウントダウン", "카운트다운", "倒计时", "นับถอยหลัง", "Hitung mundur", "Cuenta atrás", "Contagem regressiva", "Compte à rebours", "Countdown"));
        showArrivalLabel.setText(arrivalLabel());
        if (!shareCodeView.getText().toString().startsWith("CC2|")) {
            shareCodeView.setText(msg(
                    "Issue an instruction, then create a code. Others can import it and use their own time.",
                    "指示開始後にコードを作成できます。受け取った人は取り込み、自分の設定値で使えます。",
                    "지시를 시작한 뒤 코드를 만드세요. 다른 사람은 가져와서 자신의 시간으로 사용할 수 있습니다.",
                    "发出指示后创建代码。其他人可导入并使用自己的时间。",
                    "เริ่มคำสั่งแล้วสร้างรหัส ผู้อื่นนำเข้าและใช้เวลาของตนเองได้",
                    "Terbitkan instruksi, lalu buat kode. Orang lain dapat mengimpor dan memakai waktu mereka sendiri.",
                    "Emite una instrucción y crea un código. Otros pueden importarlo y usar su propio tiempo.",
                    "Emita uma instrução e crie um código. Outros podem importar e usar o próprio tempo.",
                    "Lancez une instruction, puis créez un code. Les autres peuvent l'importer avec leur propre temps.",
                    "Starten Sie eine Anweisung und erstellen Sie einen Code. Andere können ihn importieren und ihre eigene Zeit nutzen."));
        }
        refreshPermissionState();
    }

    private String defaultLabel() {
        return msg("Next operation", "次の作戦", "다음 작전", "下一次任务", "ปฏิบัติการถัดไป", "Operasi berikutnya", "Próxima operación", "Próxima operação", "Prochaine opération", "Nächster Einsatz");
    }

    private void setLanguage(String nextLanguage) {
        language = nextLanguage;
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_LANGUAGE, language).apply();
        applyLanguage();
        updateClock();
    }

    private String msg(String en, String ja, String ko, String zh,
                       String th, String id, String es, String pt,
                       String fr, String de) {
        switch (language) {
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
