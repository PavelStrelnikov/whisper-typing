# WhisperTyping

Голосовой ввод текста в любое приложение Windows.
Нажал кнопку — говоришь — текст появляется в активном окне.

**Языки:** русский, английский, иврит (автоопределение)

---

## Быстрый старт

### Вариант 1: Папка с установкой (рекомендуется)

**Требования:** Python 3.10+ ([python.org](https://python.org))

1. Скопируй папку `whisper-typing` на компьютер
2. Запусти `install.bat` — он создаст виртуальное окружение и установит все зависимости
3. Запусти `run.bat`

### Вариант 2: Готовый .exe

Если есть собранная версия:
1. Скопируй папку `WhisperTyping` на компьютер
2. Запусти `WhisperTyping.exe`

---

## Использование

1. После запуска появится маленькое плавающее окно
2. **Ctrl+Shift+Space** (по умолчанию) — зажми и говори
3. Отпусти — текст вставится в активное окно (Notepad, браузер, Word, чат и т.д.)
4. Иконка в системном трее — меню с настройками

### Триггеры

| Тип | Примеры |
|-----|---------|
| Клавиатура | Ctrl+Shift+Space, F9, F10, любая комбинация |
| Мышь | Средняя кнопка, боковые кнопки (X1, X2) |

### Режимы

- **Push-to-talk** — зажми кнопку, говори, отпусти
- **Toggle** — нажми для начала записи, нажми ещё раз для остановки

---

## Настройки (шестерёнка в окне)

| Параметр | Описание |
|----------|----------|
| **STT Provider** | `local` — на своём GPU/CPU, `cloud` — через OpenAI API |
| **Model Size** | tiny/base/small/medium/large-v3 (больше = точнее, но медленнее) |
| **Language** | auto / ru / en / he |
| **Trigger Key** | Горячая клавиша (кнопка "Record" для записи комбинации) |
| **Mouse Button** | Кнопка мыши для триггера |
| **Trigger Mode** | Push-to-talk / Toggle |
| **OpenAI API Key** | Ключ для облачного режима (не нужен для local) |

---

## Режимы распознавания

### Local (faster-whisper)

- Работает оффлайн, бесплатно
- С NVIDIA GPU (CUDA) — быстро (large-v3 за ~1-2 сек)
- Без GPU — медленно, но работает (рекомендуется модель tiny или base)
- Модель скачивается автоматически при первом запуске

### Cloud (OpenAI API)

- Требует интернет и API ключ
- Очень быстро и точно
- Платно (по тарифам OpenAI, ~$0.006/мин)

---

## Установка для разработки

```bash
# Клонировать
git clone <repo-url>
cd whisper-typing

# Виртуальное окружение
python -m venv .venv
.venv\Scripts\activate

# Зависимости
pip install -r requirements.txt

# CUDA (опционально, для NVIDIA GPU)
pip install -r requirements-cuda.txt

# Запуск
python main.py
```

---

## Сборка .exe

```bash
# В активированном venv:
pip install pyinstaller
pyinstaller whisper_typing.spec --noconfirm

# Или просто запусти:
build.bat
```

Результат: `dist/WhisperTyping/WhisperTyping.exe`

> Папку `dist/WhisperTyping/` целиком можно копировать на другой компьютер.
> Для CUDA нужно чтобы на целевом компьютере был установлен драйвер NVIDIA.

---

## Структура файлов

```
whisper-typing/
├── main.py                 # Точка входа
├── whisper_typing.pyw      # Запуск без консоли
├── install.bat             # Автоустановка
├── run.bat                 # Запуск (без консоли)
├── run_console.bat         # Запуск с отладкой
├── build.bat               # Сборка .exe
├── config/
│   ├── settings.py         # Настройки приложения
│   └── constants.py        # Константы
├── core/
│   ├── audio_recorder.py   # Запись с микрофона
│   ├── stt_local.py        # Локальное распознавание
│   ├── stt_cloud.py        # Облачное распознавание
│   ├── text_injector.py    # Вставка текста в окна
│   ├── hotkey_manager.py   # Горячие клавиши и мышь
│   └── history.py          # История транскрипций
└── ui/
    ├── app.py              # Главный контроллер
    ├── floating_window.py  # Плавающее окно
    ├── settings_window.py  # Окно настроек
    ├── history_window.py   # Окно истории
    └── tray_icon.py        # Системный трей
```

---

## Логи

Логи пишутся в `%APPDATA%\WhisperTyping\whisper-typing.log`

Настройки: `%APPDATA%\WhisperTyping\settings.json`

История: `%APPDATA%\WhisperTyping\history.json`

---

## Известные нюансы

- Для глобальных хоткеев библиотека `keyboard` может требовать права администратора в некоторых приложениях
- Модели faster-whisper при первом запуске скачиваются (~1-3 ГБ для large-v3)
- Настройки и история хранятся в `%APPDATA%\WhisperTyping\` — при переносе на другой компьютер они создадутся заново
