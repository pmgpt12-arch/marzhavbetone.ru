/**
 * Бренд-токены: тёмная драматичная палитра, янтарные акценты, кинематографичность.
 * Все сцены и компоненты должны брать значения отсюда (или из props с fallback сюда).
 */
export const theme = {
  colors: {
    /** Тёмный основной фон */
    bg: "#242629",
    /** Более тёмный низ для градиентов */
    bgDeep: "#161719",
    /** Янтарный акцент (каски, деньги, предупреждение) */
    amber: "#ff5a00",
    /** Янтарный яркий (для свечения / бликов) */
    amberBright: "#ff8340",
    /** Приглушённый белый для основного текста */
    text: "#f8f6f0",
    /** Вторичный текст */
    textDim: "#a9a49a",
    /** Цвет опасности / банкротства */
    danger: "#d4553a",
    /** Тонкие линии / рамки */
    stroke: "rgba(248,246,240,0.14)",
  },
  fonts: {
    /** Системный стек с fallback — внешние шрифты не требуются */
    display:
      'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
  },
  radii: {
    sm: 8,
    md: 16,
    lg: 28,
    pill: 999,
  },
  shadows: {
    amberGlow: "0 0 24px rgba(255,90,0,0.55), 0 0 80px rgba(255,90,0,0.25)",
    textHeavy: "0 4px 30px rgba(0,0,0,0.8)",
    card: "0 20px 60px rgba(0,0,0,0.6)",
  },
  gradients: {
    /** Грозовое небо: вертикальный тёмный градиент с холодной синевой */
    stormSky:
      "linear-gradient(180deg, #2b2d31 0%, #242629 45%, #161719 100%)",
    /** Янтарный блик сверху по центру (как прожектор / молния за облаками) */
    amberSpot:
      "radial-gradient(ellipse 90% 45% at 50% 0%, rgba(255,90,0,0.22) 0%, rgba(255,90,0,0.05) 45%, transparent 70%)",
    /** Затемнение по краям (виньетка) */
    vignette:
      "radial-gradient(ellipse 80% 70% at 50% 50%, transparent 55%, rgba(0,0,0,0.75) 100%)",
  },
} as const;

export type Theme = typeof theme;
