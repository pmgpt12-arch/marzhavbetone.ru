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
 * Сцена «кадр под тезис»: снятое изображение и утверждение поверх него.
 *
 * Зачем отдельно от остальных. Стандарт V2 требует смеси источников кадра:
 * ролик, собранный только моушн-графикой, читается как шаблонная презентация
 * ровно так же, как ролик из одних обложек читается автонарезкой. Здесь
 * основа — снятый под сцену кадр, а движение даёт не панорама сама по себе,
 * а вход текста и медленный наезд вместе.
 *
 * Наезд намеренно мелкий: заметный превращает разбор в рекламный ролик.
 */
export const photoStatementSchema = z.object({
  /** Файл кадра в public/ */
  image: z.string(),
  /** Утверждение поверх кадра */
  text: z.string(),
  /** Слова, которые подсвечиваются акцентом */
  highlightWords: z.array(z.string()).default([]),
  /** Куда прижать текст: сверху или снизу безопасной зоны */
  anchor: z.enum(["top", "bottom"]).default("top"),
  /** Насколько затемнить кадр под текстом */
  dimAmount: z.number().min(0).max(1).default(0.45),
  /** Направление наезда */
  zoom: z.enum(["in", "out"]).default("in"),
  /** Длительность сцены: у кадра под тезис она своя, а не общая */
  durationSec: z.number().default(5),
  /** Выравнивание надписи. По центру — то, как читают ленту: замер
   *  форматов 17.08.2026 (текст крупно, по центру, 6–8 слов) */
  align: z.enum(["left", "center"]).default("center"),
});

export type PhotoStatementProps = z.infer<typeof photoStatementSchema>;

export const photoStatementDefaultProps: PhotoStatementProps = {
  image: "07-scene2-obyom.png",
  text: "Объём есть в бетоне. В документах его нет",
  highlightWords: ["бетоне"],
  anchor: "top",
  dimAmount: 0.45,
  zoom: "in",
  durationSec: 5,
  align: "center",
};

// Интерфейс Instagram перекрывает края кадра: сверху имя автора, снизу
// описание и кнопки. Написанное там зритель просто не увидит.
const SAFE_TOP = 320;
const SAFE_BOTTOM = 480;

export const PhotoStatementScene: React.FC<PhotoStatementProps> = ({
  image,
  text,
  highlightWords,
  anchor,
  dimAmount,
  zoom,
  align,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
  });
  const scale =
    zoom === "in" ? 1.02 + 0.06 * progress : 1.08 - 0.06 * progress;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.bgDeep }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <Img
          src={staticFile(image)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
          }}
        />
      </AbsoluteFill>

      {/* Затемнение со стороны текста: белая надпись на светлой бумаге
          нечитаема, а сплошная плашка убивает кадр целиком */}
      <AbsoluteFill
        style={{
          background:
            anchor === "top"
              ? `linear-gradient(180deg, rgba(22,23,25,${dimAmount + 0.25}) 0%, rgba(22,23,25,${dimAmount}) 38%, rgba(22,23,25,0) 68%)`
              : `linear-gradient(0deg, rgba(22,23,25,${dimAmount + 0.25}) 0%, rgba(22,23,25,${dimAmount}) 38%, rgba(22,23,25,0) 68%)`,
        }}
      />

      <GrainOverlay />

      <AbsoluteFill
        style={{
          padding: `${SAFE_TOP}px 70px ${SAFE_BOTTOM}px`,
          justifyContent: anchor === "top" ? "flex-start" : "flex-end",
          alignItems: align === "center" ? "center" : "flex-start",
        }}
      >
        <AnimatedText
          text={text}
          fontSize={76}
          highlightWords={highlightWords}
          align={align}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
