import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setPixelFormat("yuv420p");
Config.setCodec("h264");
// Concurrency не фиксируем: на раннере GitHub два ядра, и жёсткая четвёрка
// роняет рендер с «Maximum for --concurrency is 2». Remotion сам возьмёт
// столько потоков, сколько есть на машине.
