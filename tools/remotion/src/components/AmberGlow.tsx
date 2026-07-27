import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { theme } from "../theme";

export interface AmberGlowProps {
  /** Интенсивность свечения 0..1 */
  intensity?: number;
  /** Вертикальная позиция центра свечения, % от высоты */
  top?: number;
  /** Пульсация (лёгкое «дыхание» как у прожектора) */
  pulse?: boolean;
}

/** Янтарное свечение-прожектор поверх тёмного фона */
export const AmberGlow: React.FC<AmberGlowProps> = ({
  intensity = 1,
  top = 18,
  pulse = true,
}) => {
  const frame = useCurrentFrame();
  const p = pulse ? 0.85 + 0.15 * Math.sin(frame / 12) : 1;
  const opacity = interpolate(intensity * p, [0, 1], [0, 1]);
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        opacity,
        background: `radial-gradient(ellipse 95% 50% at 50% ${top}%, rgba(232,163,61,0.26) 0%, rgba(232,163,61,0.07) 45%, transparent 72%)`,
        filter: "blur(2px)",
      }}
    />
  );
};

/** Грозовое небо: тёмный градиент + «молнии» вспышками в заданные кадры */
export const StormBackground: React.FC<{ lightningFrames?: number[] }> = ({
  lightningFrames = [],
}) => {
  const frame = useCurrentFrame();
  // Вспышка: быстрый подъём и затухание в окне 6 кадров вокруг кадра молнии
  const flash = lightningFrames.reduce((acc, f) => {
    const d = Math.abs(frame - f);
    return Math.max(acc, d <= 6 ? 1 - d / 6 : 0);
  }, 0);

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <div style={{ position: "absolute", inset: 0, background: theme.gradients.stormSky }} />
      {/* силуэт крана на фоне — чистый SVG */}
      <svg
        style={{ position: "absolute", bottom: 0, left: 0, opacity: 0.35 }}
        width="1080"
        height="700"
        viewBox="0 0 1080 700"
      >
        <g stroke="#1c2028" strokeWidth="10" fill="none">
          <line x1="220" y1="700" x2="220" y2="120" />
          <line x1="120" y1="180" x2="700" y2="180" />
          <line x1="220" y1="120" x2="220" y2="180" />
          <line x1="220" y1="120" x2="700" y2="180" />
          <line x1="120" y1="180" x2="220" y2="120" />
          <line x1="600" y1="180" x2="600" y2="330" />
        </g>
        <rect x="576" y="330" width="48" height="48" fill="#1c2028" />
        <g stroke="#1c2028" strokeWidth="8">
          <line x1="820" y1="700" x2="820" y2="300" />
          <line x1="760" y1="360" x2="1040" y2="360" />
          <line x1="820" y1="300" x2="1040" y2="360" />
        </g>
      </svg>
      {/* вспышка молнии */}
      {flash > 0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `radial-gradient(ellipse 80% 55% at 50% 8%, rgba(255,230,180,${0.5 * flash}) 0%, rgba(200,210,255,${0.18 * flash}) 50%, transparent 75%)`,
          }}
        />
      )}
      <div style={{ position: "absolute", inset: 0, background: theme.gradients.vignette }} />
    </div>
  );
};
