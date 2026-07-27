import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { z } from "zod";
import { theme } from "../theme";
import { AnimatedText } from "../components/AnimatedText";
import { AmberGlow } from "../components/AmberGlow";
import { GrainOverlay } from "../components/GrainOverlay";

export const ctaSchema = z.object({
  /** Основной призыв */
  ctaText: z.string(),
  /** Имя канала / бренда */
  channelName: z.string(),
  /** Дополнительная строка под кнопкой */
  subText: z.string().default(""),
});

export type CTASceneProps = z.infer<typeof ctaSchema>;

export const ctaDefaultProps: CTASceneProps = {
  ctaText: "Подпишись — расскажем, как не потерять деньги на стройке",
  channelName: "@stroy_bez_ila",
  subText: "Разборы смет, судов и банкротств — каждую неделю",
};

/** Финальная сцена: призыв подписаться, пульсирующая янтарная кнопка */
export const CTAScene: React.FC<CTASceneProps> = ({ ctaText, channelName, subText }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const btnIn = spring({
    frame: frame - 14,
    fps,
    config: { damping: 12, stiffness: 160, mass: 0.8 },
  });
  const pulse = 1 + 0.035 * Math.sin(frame / 8);
  const btnOpacity = interpolate(frame, [14, 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.bg }}>
      <div style={{ position: "absolute", inset: 0, background: theme.gradients.stormSky }} />
      <AmberGlow intensity={1} top={30} />
      <GrainOverlay />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          gap: 56,
          padding: "0 70px",
        }}
      >
        <AnimatedText text={ctaText} fontSize={64} highlightWords={["Подпишись"]} />
        <div
          style={{
            opacity: btnOpacity,
            transform: `scale(${btnIn * pulse})`,
            background: `linear-gradient(135deg, ${theme.colors.amber} 0%, ${theme.colors.amberBright} 100%)`,
            color: theme.colors.bg,
            fontFamily: theme.fonts.display,
            fontSize: 54,
            fontWeight: 800,
            padding: "30px 64px",
            borderRadius: theme.radii.pill,
            boxShadow: theme.shadows.amberGlow,
          }}
        >
          Подписаться · {channelName}
        </div>
        {subText && (
          <div
            style={{
              opacity: btnOpacity,
              fontFamily: theme.fonts.display,
              fontSize: 34,
              color: theme.colors.textDim,
              textAlign: "center",
              maxWidth: 800,
            }}
          >
            {subText}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
