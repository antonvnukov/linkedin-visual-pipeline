import React from "react";
import { Composition } from "remotion";
import { Card, CardProps } from "./Card";

/**
 * One composition, every card format. Size and duration come from props, which
 * scripts/animate.sh writes from the same config JSON the static builder reads.
 * Square (1080x1080) and portrait (1080x1350) are both LinkedIn-native.
 */
const defaults: CardProps = {
  htmlFile: "card.html",
  width: 1080,
  height: 1080,
  durationMs: 5500,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Card"
    component={Card}
    defaultProps={defaults}
    fps={30}
    width={defaults.width}
    height={defaults.height}
    durationInFrames={Math.round((defaults.durationMs / 1000) * 30)}
    calculateMetadata={({ props }) => ({
      width: props.width,
      height: props.height,
      durationInFrames: Math.round((props.durationMs / 1000) * 30),
    })}
  />
);
