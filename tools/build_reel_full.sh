#!/usr/bin/env bash
# Полная сборка ролика: планы → панорама → надписи → голос → готовый mp4.
#
# Имена переменных латиницей: оболочка кириллицу в идентификаторах не
# принимает, в отличие от питоновских инструментов рядом.
#
# Зачем отдельный скрипт. Шагов четыре, и последний — сведение звука —
# делался руками в сессии. Такой шаг воспроизводится по памяти, а память
# у следующего захода своя: параметры звука уже один раз уехали.
#
# ЗВУК ЗАДАЁТСЯ ЯВНО, И ЭТО НЕ ПРИДИРКА. Фильтр loudnorm сам поднимает
# частоту дискретизации (замер 16.08.2026: на выходе оказалось 96 кГц моно
# при исходных 24 кГц от модели). Instagram ждёт 48 кГц; несовпадение он
# чинит перекодированием на своей стороне, то есть теряя качество там, где
# терять нечего. Отсюда -ar 48000 -ac 2 явными аргументами.
#
# +faststart переносит индекс в начало файла: без него загрузка ждёт
# дочитывания всего mp4.
#
#     tools/build_reel_full.sh 01-uderzhanie 01-uderzhanie-5-millionov out/
set -euo pipefail

if [ $# -lt 3 ]; then
    echo "нужно: <имя-планов> <имя-сценария> <каталог-выдачи>" >&2
    echo "пример: $0 01-uderzhanie 01-uderzhanie-5-millionov out/" >&2
    exit 2
fi

SHOTS="$1"
SCRIPT="$2"
OUTDIR="$3"
NEIGHBOUR="${AI_BUSINESS_OS:-../ai-business-os}"

mkdir -p "$OUTDIR"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "1/4 видеоряд"
python3 tools/build_footage.py "content/reels/shots/${SHOTS}.yaml" \
    --out "$WORK/footage.mp4"

echo "2/4 надписи"
python3 tools/build_reel.py "content/reels/${SCRIPT}.md" \
    --footage "$WORK/footage.mp4" --out "$WORK/немой.mp4"

echo "3/4 голос"
# Голос кэшируется рядом с выдачей. Синтез платный, а пересборка ролика
# нужна на каждой правке кадров — без кэша каждая правка картинки заново
# оплачивает неизменившийся текст. Кэш сбрасывается удалением файла.
CACHE="$OUTDIR/voice"
mkdir -p "$CACHE"
if [ -f "$CACHE/${SHOTS}.wav" ]; then
    echo "  взят из кэша: $CACHE/${SHOTS}.wav"
    VOICE="$CACHE/${SHOTS}.wav"
else
    if [ ! -f "$NEIGHBOUR/tools/generate_voiceover.py" ]; then
        echo "нет $NEIGHBOUR/tools/generate_voiceover.py — задайте AI_BUSINESS_OS" >&2
        exit 2
    fi
    python3 "$NEIGHBOUR/tools/generate_voiceover.py" \
        "content/reels/voice/${SHOTS}.yaml" --out "$WORK/vo"

    # Расшифровка сверяется с написанным на стороне генератора; здесь
    # проверяем, что сверка вообще прошла, — молчаливое false тут дороже
    # лишней строки.
    if ! grep -q 'verbatim: true' "$WORK/vo/report.yaml"; then
        echo "ВНИМАНИЕ: озвучка разошлась с текстом, смотрите $WORK/vo/report.yaml" >&2
    fi
    cp "$(find "$WORK/vo" -name '*.wav' | head -1)" "$CACHE/${SHOTS}.wav"
    VOICE="$CACHE/${SHOTS}.wav"
fi

echo "4/4 сведение"
# Голос длиннее картинки — не мелочь: видео кончается, звук продолжается,
# и площадка обрежет фразу на полуслове. Замер 16.08.2026: у ролика 2
# озвучка вышла 23,4 с против 22 с видео. Хвост достраивается остановкой
# последнего кадра, а расхождение называется вслух — если оно велико,
# лечить надо текст озвучки, а не монтаж.
VDUR="$(ffprobe -v error -select_streams v:0 -show_entries format=duration \
    -of csv=p=0 "$WORK/немой.mp4")"
ADUR="$(ffprobe -v error -select_streams a:0 -show_entries format=duration \
    -of csv=p=0 "$VOICE")"
LONGER="$(python3 -c "print('yes' if float('$ADUR') > float('$VDUR') + 0.15 else 'no')")"

if [ "$LONGER" = "yes" ]; then
    echo "  голос $ADUR с длиннее картинки $VDUR с — хвост достроен стоп-кадром" >&2
    VFILTER="-vf tpad=stop_mode=clone:stop_duration=$(python3 -c "print(round(float('$ADUR')-float('$VDUR')+0.1,2))") -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p"
else
    VFILTER="-c:v copy"
fi

# shellcheck disable=SC2086
ffmpeg -y -v error -i "$WORK/немой.mp4" -i "$VOICE" \
    -filter:a "loudnorm=I=-14:TP=-1.5:LRA=11" \
    -map 0:v:0 -map 1:a:0 \
    $VFILTER -c:a aac -b:a 192k -ar 48000 -ac 2 \
    -movflags +faststart \
    "$OUTDIR/${SHOTS}.mp4"

echo "Готово: $OUTDIR/${SHOTS}.mp4"
ffprobe -v error -show_entries stream=codec_name,width,height,sample_rate,channels \
    -show_entries format=duration -of default=noprint_wrappers=1 \
    "$OUTDIR/${SHOTS}.mp4"
