import React from "react";
import { spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { theme } from "../theme";

export interface AnimatedTextProps {
  /** Текст; слова появляются по очереди */
  text: string;
  /** Задержка старта (кадры) */
  delay?: number;
  /** Шаг между словами (кадры) */
  stagger?: number;
  fontSize?: number;
  color?: string;
  /** Слова, которые нужно подсветить янтарным */
  highlightWords?: string[];
  fontWeight?: number;
  align?: React.CSSProperties["textAlign"];
  lineHeight?: number;
  maxWidth?: number;
}

/** Spring-появление текста по словам: подъём + прозрачность + лёгкий scale */
export const AnimatedText: React.FC<AnimatedTextProps> = ({
  text,
  delay = 0,
  stagger = 4,
  fontSize = 72,
  color = theme.colors.text,
  highlightWords = [],
  fontWeight = 800,
  align = "center",
  lineHeight = 1.15,
  maxWidth = 920,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(/\s+/).filter(Boolean);

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent:
          align === "center" ? "center" : align === "right" ? "flex-end" : "flex-start",
        maxWidth,
        textAlign: align,
        fontFamily: theme.fonts.display,
        fontSize,
        fontWeight,
        lineHeight,
        textShadow: theme.shadows.textHeavy,
        columnGap: fontSize * 0.28,
      }}
    >
      {words.map((word, i) => {
        const clean = word.replace(/[.,!?—:;«»]/g, "").toLowerCase();
        const isHi = highlightWords.some((w) => w.toLowerCase() === clean);
        const start = delay + i * stagger;
        const s = spring({
          frame: frame - start,
          fps,
          config: { damping: 14, stiffness: 140, mass: 0.7 },
        });
        const opacity = interpolate(frame, [start, start + 6], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity,
              transform: `translateY(${(1 - s) * 60}px) scale(${0.85 + s * 0.15})`,
              color: isHi ? theme.colors.amber : color,
              textShadow: isHi
                ? `${theme.shadows.amberGlow}, ${theme.shadows.textHeavy}`
                : theme.shadows.textHeavy,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};
