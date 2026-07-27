import React from "react";
import { Composition } from "remotion";
import {
  HookScene,
  hookSceneSchema,
  hookDefaultProps,
} from "./compositions/HookScene";
import {
  MarkerListScene,
  markerListSchema,
  markerListDefaultProps,
} from "./compositions/MarkerListScene";
import {
  MoneyCounterScene,
  moneyCounterSchema,
  moneyCounterDefaultProps,
} from "./compositions/MoneyCounterScene";
import {
  CTAScene,
  ctaSchema,
  ctaDefaultProps,
} from "./compositions/CTAScene";

const FPS = 30;
const WIDTH = 1080;
const HEIGHT = 1920;

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="HookScene"
        component={HookScene}
        durationInFrames={90} // 3 сек
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        schema={hookSceneSchema}
        defaultProps={hookDefaultProps}
      />
      <Composition
        id="MarkerListScene"
        component={MarkerListScene}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        schema={markerListSchema}
        defaultProps={markerListDefaultProps}
        calculateMetadata={({ props }) => ({
          // заголовок 1 сек + время на каждый пункт + 1 сек хвоста
          durationInFrames: 30 + props.items.length * props.framesPerItem + 30,
        })}
      />
      <Composition
        id="MoneyCounterScene"
        component={MoneyCounterScene}
        durationInFrames={150} // 5 сек
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        schema={moneyCounterSchema}
        defaultProps={moneyCounterDefaultProps}
      />
      <Composition
        id="CTAScene"
        component={CTAScene}
        durationInFrames={120} // 4 сек
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        schema={ctaSchema}
        defaultProps={ctaDefaultProps}
      />
    </>
  );
};
