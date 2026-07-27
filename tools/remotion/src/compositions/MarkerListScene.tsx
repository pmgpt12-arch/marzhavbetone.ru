import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { theme } from "../theme";
import { AmberGlow } from "../components/AmberGlow";
import { GrainOverlay } from "../components/GrainOverlay";
import { AnimatedText } from "../components/AnimatedText";

export const markerItemSchema = z.object({
  /** Текст маркера */
  text: z.string(),
  /** Эмодзи или короткий символ-иконка (⚠️, 🏗, 💰…) */
  icon: z.string().default("⚠️"),
  /** Мелкая подпись-пояснение */
  caption: z.string().default(""),
});

export const markerListSchema = z.object({
  /** Заголовок списка */
  title: z.string(),
  /** Пункты (обычно 5) */
  items: z.array(markerItemSchema),
  /** Кадров на один пункт (при 30fps: 60 = 2 сек) */
  framesPerItem: z.number().default(60),
});

export type MarkerItem = z.infer<typeof markerItemSchema>;
export type MarkerListSceneProps = z.infer<typeof markerListSchema>;

export const markerListDefaultProps: MarkerListSceneProps = {
  title: "5 маркеров банкротства генподрядчика",
  items: [
    { text: "Смета растёт каждую неделю", icon: "📈", caption: "Допы без вашей подписи" },
    { text: "Субподрядчики меняются как перчатки", icon: "🔁", caption: "Исходники договоров не показывают" },
    { text: "Сроки сдвигаются без актов", icon: "🗓", caption: "Ни одного письменного уведомления" },
    { text: "Просят предоплату «на материалы»", icon: "💰", caption: "Деньги уходят мимо эскроу" },
    { text: "Директор перестал выходить на связь", icon: "📵", caption: "Финальный маркер" },
  ],
  framesPerItem: 60,
};

const MarkerRow: React.FC<{ item: MarkerItem; index: number }> = ({ item, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 150, mass: 0.8 },
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 28,
        opacity,
        transform: `translateX(${(1 - enter) * 120}px)`,
        background: "rgba(13,15,18,0.72)",
        border: `1px solid ${theme.colors.stroke}`,
        borderLeft: `6px solid ${theme.colors.amber}`,
        borderRadius: theme.radii.lg,
        padding: "30px 36px",
        boxShadow: theme.shadows.card,
      }}
    >
      <div
        style={{
          minWidth: 96,
          height: 96,
          borderRadius: theme.radii.md,
          background: "rgba(232,163,61,0.12)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 52,
          boxShadow: theme.shadows.amberGlow,
        }}
      >
        {item.icon}
      </div>
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontFamily: theme.fonts.mono,
            fontSize: 30,
            color: theme.colors.amber,
            letterSpacing: 2,
            marginBottom: 6,
          }}
        >
          МАРКЕР {index + 1}
        </div>
        <div
          style={{
            fontFamily: theme.fonts.display,
            fontSize: 48,
            fontWeight: 700,
            color: theme.colors.text,
            lineHeight: 1.2,
          }}
        >
          {item.text}
        </div>
        {item.caption && (
          <div
            style={{
              fontFamily: theme.fonts.display,
              fontSize: 32,
              color: theme.colors.textDim,
              marginTop: 10,
            }}
          >
            {item.caption}
          </div>
        )}
      </div>
    </div>
  );
};

/** Формат «5 маркеров»: пункты появляются по очереди и накапливаются */
export const MarkerListScene: React.FC<MarkerListSceneProps> = ({
  title,
  items,
  framesPerItem,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.bg }}>
      <div style={{ position: "absolute", inset: 0, background: theme.gradients.stormSky }} />
      <AmberGlow intensity={0.7} top={6} />
      <GrainOverlay />
      <div
        style={{
          position: "absolute",
          inset: 0,
          padding: "110px 70px 160px",
          display: "flex",
          flexDirection: "column",
          gap: 34,
        }}
      >
        <div style={{ marginBottom: 20 }}>
          <AnimatedText text={title} fontSize={60} align="left" highlightWords={["банкротства"]} />
        </div>
        {items.map((item, i) => (
          <Sequence key={i} from={i * framesPerItem} layout="none">
            <MarkerRow item={item} index={i} />
          </Sequence>
        ))}
      </div>
    </AbsoluteFill>
  );
};
