import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { theme } from "../theme";
import { AnimatedText } from "../components/AnimatedText";
import { GrainOverlay } from "../components/GrainOverlay";

/**
 * Сцена-серия ударов по одному кадру.
 *
 * Зачем она появилась. Владелец 17.08.2026 отклонил три ролика с диагнозом
 * «презентация, сохранённая в mp4»: одна картинка висела пять секунд с
 * медленным наездом и одной фразой поверх. Это и есть слайд, сколько его
 * ни зумируй.
 *
 * Здесь один кадр даёт несколько разных планов. Между ударами стоит
 * жёсткий рез — меняется крупность и точка кадра, а не масштаб на
 * полпроцента, — и на каждом ударе своя короткая фраза, входящая словами.
 * Смена визуального события получается каждые полторы-две с половиной
 * секунды из одного исходника, без второй генерации.
 *
 * Почему это не дешёвый приём ради приёма: крупность выбирается по смыслу
 * удара. «5% с каждого акта» — тугой план на строку с процентами, «деньги
 * ваши» — общий план, где виден весь предмет.
 */
const beatSchema = z.object({
  /** Короткая фраза удара: два-четыре слова, не предложение */
  text: z.string(),
  /** Длительность удара в секундах */
  seconds: z.number(),
  /** Крупность: 1 — весь кадр, 2 — вдвое ближе */
  scale: z.number().min(1).max(3).default(1.15),
  /** Точка кадра по горизонтали и вертикали, 0…1 */
  x: z.number().min(0).max(1).default(0.5),
  y: z.number().min(0).max(1).default(0.5),
  /** Слова, которые подсвечиваются акцентом */
  highlightWords: z.array(z.string()).default([]),
});

export const beatSceneSchema = z.object({
  image: z.string(),
  beats: z.array(beatSchema),
  /** Затемнение под текстом */
  dimAmount: z.number().min(0).max(1).default(0.5),
});

export type BeatSceneProps = z.infer<typeof beatSceneSchema>;

export const beatSceneDefaultProps: BeatSceneProps = {
  image: "r-procenty-dogovor.png",
  beats: [
    { text: "5% с каждого акта", seconds: 2, scale: 1.1, x: 0.5, y: 0.5, highlightWords: ["5%"] },
    { text: "Не платит. Держит", seconds: 2.5, scale: 1.7, x: 0.45, y: 0.55, highlightWords: ["Держит"] },
  ],
  dimAmount: 0.5,
};

// Интерфейс площадки перекрывает края кадра
const SAFE_TOP = 340;
const SAFE_BOTTOM = 500;

export const BeatScene: React.FC<BeatSceneProps> = ({ image, beats, dimAmount }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Какой удар идёт сейчас и сколько кадров он уже длится
  let прошло = 0;
  let текущий = beats[0];
  let началоУдара = 0;
  for (const удар of beats) {
    const длина = Math.round(удар.seconds * fps);
    if (frame < прошло + длина) {
      текущий = удар;
      началоУдара = прошло;
      break;
    }
    прошло += длина;
    текущий = удар;
    началоУдара = прошло - длина;
  }
  const внутри = frame - началоУдара;

  // Внутри удара кадр едет чуть-чуть: без этого рез читается как
  // подвисание. Заметное движение здесь не нужно — работает рез.
  const дрейф = interpolate(внутри, [0, текущий.seconds * fps], [0, 0.04], {
    extrapolateRight: "clamp",
  });
  const масштаб = текущий.scale + дрейф;
  const сдвигX = (0.5 - текущий.x) * 100 * (масштаб - 1);
  const сдвигY = (0.5 - текущий.y) * 100 * (масштаб - 1);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.bgDeep }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <Img
          src={staticFile(image)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${масштаб}) translate(${сдвигX}%, ${сдвигY}%)`,
          }}
        />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(22,23,25,${dimAmount + 0.2}) 0%, rgba(22,23,25,${dimAmount * 0.5}) 45%, rgba(22,23,25,${dimAmount + 0.3}) 100%)`,
        }}
      />
      <GrainOverlay />

      <AbsoluteFill
        style={{
          padding: `${SAFE_TOP}px 70px ${SAFE_BOTTOM}px`,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {/* key перезапускает анимацию входа на каждом ударе: без него
            слова второго удара появились бы уже показанными */}
        <AnimatedText
          key={началоУдара}
          text={текущий.text}
          fontSize={84}
          align="center"
          highlightWords={текущий.highlightWords}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
