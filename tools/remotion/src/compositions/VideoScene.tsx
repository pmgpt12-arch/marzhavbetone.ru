import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { z } from "zod";
import { theme } from "../theme";
import { AnimatedText } from "../components/AnimatedText";
import { GrainOverlay } from "../components/GrainOverlay";

/**
 * Сцена на живом клипе: снятое видео и короткая надпись поверх.
 *
 * Зачем. Требование владельца 17.08.2026: не меньше 60–70% ролика —
 * настоящие движущиеся сцены, а зум по фотографии видеосценой не
 * считается. Остальные сцены проекта кладут текст на неподвижный кадр;
 * эта — на клип, и только она засчитывается в долю видео.
 *
 * Движения камеры здесь нет намеренно. Оно уже снято внутри клипа, и
 * добавлять сверху наезд значит спорить с тем, что и так движется.
 */
export const videoSceneSchema = z.object({
  /** Файл клипа в public/ */
  video: z.string(),
  /** Короткая надпись: два-четыре слова */
  text: z.string().default(""),
  highlightWords: z.array(z.string()).default([]),
  anchor: z.enum(["top", "bottom", "center"]).default("center"),
  dimAmount: z.number().min(0).max(1).default(0.45),
  durationSec: z.number().default(3),
  /** С какой секунды клипа брать кусок */
  startFrom: z.number().default(0),
});

export type VideoSceneProps = z.infer<typeof videoSceneSchema>;

export const videoSceneDefaultProps: VideoSceneProps = {
  video: "u1-listaet-akt.mp4",
  text: "С каждого акта удержат 3–5%",
  highlightWords: ["3–5%"],
  anchor: "center",
  dimAmount: 0.45,
  durationSec: 2.5,
  startFrom: 0,
};

// Интерфейс площадки перекрывает края кадра
const SAFE_TOP = 340;
const SAFE_BOTTOM = 500;

export const VideoScene: React.FC<VideoSceneProps> = ({
  video,
  text,
  highlightWords,
  anchor,
  dimAmount,
  startFrom,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.bgDeep }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <OffthreadVideo
          src={staticFile(video)}
          startFrom={Math.round(startFrom * 30)}
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>

      {/* Затемнение только со стороны надписи: сплошная плашка убивает
          кадр, ради которого клип и снимали */}
      <AbsoluteFill
        style={{
          background:
            anchor === "bottom"
              ? `linear-gradient(0deg, rgba(22,23,25,${dimAmount + 0.25}) 0%, rgba(22,23,25,0) 60%)`
              : anchor === "top"
                ? `linear-gradient(180deg, rgba(22,23,25,${dimAmount + 0.25}) 0%, rgba(22,23,25,0) 60%)`
                : `radial-gradient(ellipse at center, rgba(22,23,25,${dimAmount}) 0%, rgba(22,23,25,${dimAmount * 0.4}) 70%)`,
        }}
      />
      <GrainOverlay />

      {text ? (
        <AbsoluteFill
          style={{
            padding: `${SAFE_TOP}px 70px ${SAFE_BOTTOM}px`,
            justifyContent:
              anchor === "top" ? "flex-start" : anchor === "bottom" ? "flex-end" : "center",
            alignItems: "center",
          }}
        >
          <AnimatedText
            text={text}
            fontSize={84}
            align="center"
            highlightWords={highlightWords}
          />
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
