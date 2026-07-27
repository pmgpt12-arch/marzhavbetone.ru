import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { z } from "zod";
import { theme } from "../theme";
import { AnimatedText } from "../components/AnimatedText";
import { AmberGlow, StormBackground } from "../components/AmberGlow";
import { GrainOverlay } from "../components/GrainOverlay";
import { SubtitleBar } from "../components/SubtitleBar";

export const hookSceneSchema = z.object({
  /** Провокационный текст-хук */
  hookText: z.string(),
  /** Слова для янтарной подсветки */
  highlightWords: z.array(z.string()).default([]),
  /** Субтитр внизу */
  subtitle: z.string().default(""),
  /** Кадры вспышек молний */
  lightningFrames: z.array(z.number()).default([30, 62]),
  /** Насколько затемнять фон 0..1 */
  dimAmount: z.number().min(0).max(1).default(0.55),
});

export type HookSceneProps = z.infer<typeof hookSceneSchema>;

export const hookDefaultProps: HookSceneProps = {
  hookText: "Ваш генподрядчик уже всё решил за вас",
  highlightWords: ["генподрядчик"],
  subtitle: "5 маркеров, что стройка идёт к банкротству",
  lightningFrames: [30, 62],
  dimAmount: 0.55,
};

/** Первые ~3 секунды: крупный хук, грозовое небо, затемнение, молнии */
export const HookScene: React.FC<HookSceneProps> = ({
  hookText,
  highlightWords,
  subtitle,
  lightningFrames,
  dimAmount,
}) => {
  const frame = useCurrentFrame();
  // Фоновое затемнение нарастает первые 20 кадров
  const dim = interpolate(frame, [0, 20], [0, dimAmount], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.bg }}>
      <StormBackground lightningFrames={lightningFrames} />
      <div style={{ position: "absolute", inset: 0, background: `rgba(0,0,0,${dim})` }} />
      <AmberGlow intensity={0.9} top={14} />
      <GrainOverlay />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: "0 70px",
        }}
      >
        <AnimatedText
          text={hookText}
          highlightWords={highlightWords}
          fontSize={92}
          stagger={5}
        />
      </AbsoluteFill>
      <SubtitleBar text={subtitle} from={18} />
    </AbsoluteFill>
  );
};
