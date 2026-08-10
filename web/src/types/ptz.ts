type PtzFeature =
  | "pt"
  | "zoom"
  | "pt-r"
  | "zoom-r"
  | "zoom-a"
  | "pt-r-fov"
  | "focus";

export type CameraPtzInfo = {
  name: string;
  features: PtzFeature[];
  presets: string[];
  patrol: {
    enabled: boolean;
    running: boolean;
    current_preset: string | null;
    last_error: string | null;
    steps: PtzPatrolStep[];
  };
};

export type PtzPatrolStep = {
  preset: string;
  dwell: number;
};
