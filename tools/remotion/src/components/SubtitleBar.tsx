import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { theme } from "../theme";

export interface SubtitleBarProps {
  text: string;
  /** Кадр появления */
  from?: number;
}

/** Полоса субтитров снизу: тёмная плашка + янтарная линия сверху */
export const SubtitleBar: React.FC<SubtitleBarProps> = ({ text, from = 0 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [from, from + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [from, from + 10], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (!text) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        // 480 px снизу перекрывает интерфейс Instagram: подпись, имя автора,
        // кнопки. Текст ниже этой границы зритель не увидит.
        bottom: 480,
        opacity,
        transform: `translateY(${translateY}px)`,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "rgba(7,8,10,0.82)",
          borderTop: `3px solid ${theme.colors.amber}`,
          borderRadius: theme.radii.md,
          padding: "22px 36px",
          maxWidth: 900,
          boxShadow: theme.shadows.card,
          backdropFilter: "blur(6px)",
        }}
      >
        <div
          style={{
            fontFamily: theme.fonts.display,
            fontSize: 44,
            fontWeight: 600,
            lineHeight: 1.3,
            color: theme.colors.text,
            textAlign: "center",
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
};
