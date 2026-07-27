import React from "react";

/** Плёночное зерно через SVG feTurbulence — кинематографичная текстура */
export const GrainOverlay: React.FC<{ opacity?: number }> = ({ opacity = 0.07 }) => {
  const noise =
    "data:image/svg+xml," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">
        <filter id="n">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>
          <feColorMatrix type="saturate" values="0"/>
        </filter>
        <rect width="100%" height="100%" filter="url(#n)"/>
      </svg>`
    );
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        backgroundImage: `url("${noise}")`,
        backgroundSize: "300px 300px",
        opacity,
        mixBlendMode: "overlay",
      }}
    />
  );
};
