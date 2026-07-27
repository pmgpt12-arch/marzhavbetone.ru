import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  Easing,
} from "remotion";
import { z } from "zod";
import { theme } from "../theme";
import { AmberGlow, StormBackground } from "../components/AmberGlow";
import { GrainOverlay } from "../components/GrainOverlay";
import { SubtitleBar } from "../components/SubtitleBar";

export const moneyCounterSchema = z.object({
  /** Заголовок сверху */
  label: z.string(),
  /** Целевая сумма в рублях */
  targetAmount: z.number(),
  /** Длительность нарастания счётчика, секунды */
  countDurationSec: z.number().default(3),
  /** Субтитр внизу */
  subtitle: z.string().default(""),
  /** Валюта-подпись */
  suffix: z.string().default("₽"),
});

export type MoneyCounterSceneProps = z.infer<typeof moneyCounterSchema>;

export const moneyCounterDefaultProps: MoneyCounterSceneProps = {
  label: "Столько генподрядчик зарабатывает на вас",
  targetAmount: 47_000_000,
  countDurationSec: 3,
  subtitle: "И это только на перепродаже субподряда",
  suffix: "₽",
};

const formatRub = (n: number): string =>
  Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");

/** Анимированный счётчик денег 0 → N с форматированием рублей */
export const MoneyCounterScene: React.FC<MoneyCounterSceneProps> = ({
  label,
  targetAmount,
  countDurationSec,
  subtitle,
  suffix,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const countFrames = countDurationSec * fps;

  const progress = interpolate(frame, [10, 10 + countFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const value = progress * targetAmount;

  // «Удар» масштаба в конце счёта
  const endScale = interpolate(
    frame,
    [10 + countFrames, 10 + countFrames + 8, 10 + countFrames + 16],
    [1, 1.08, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const labelOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.bg }}>
      <StormBackground lightningFrames={[Math.round(10 + countFrames + 6)]} />
      <AmberGlow intensity={0.4 + progress * 0.6} top={20} />
      <GrainOverlay />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: "0 60px",
          gap: 40,
        }}
      >
        <div
          style={{
            opacity: labelOpacity,
            fontFamily: theme.fonts.display,
            fontSize: 56,
            fontWeight: 700,
            color: theme.colors.text,
            textAlign: "center",
            maxWidth: 900,
            textShadow: theme.shadows.textHeavy,
          }}
        >
          {label}
        </div>
        <div
          style={{
            transform: `scale(${endScale})`,
            fontFamily: theme.fonts.mono,
            fontSize: 130,
            fontWeight: 800,
            color: theme.colors.amber,
            textShadow: theme.shadows.amberGlow,
            letterSpacing: 2,
          }}
        >
          {formatRub(value)} {suffix}
        </div>
      </AbsoluteFill>
      <SubtitleBar text={subtitle} from={10 + Math.round(countFrames)} />
    </AbsoluteFill>
  );
};
