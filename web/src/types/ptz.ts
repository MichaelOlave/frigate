type PtzFeature =
  | "pt"
  | "zoom"
  | "pt-r"
  | "zoom-r"
  | "zoom-a"
  | "pt-r-fov"
  | "pt-r-generic"
  | "focus";

export type CameraPtzInfo = {
  name: string;
  features: PtzFeature[];
  presets: string[];
  patrol: {
    enabled: boolean;
    object_tracking: boolean;
    running: boolean;
    paused_for_tracking: boolean;
    current_preset: string | null;
    last_error: string | null;
    steps: PtzPatrolStep[];
  };
};

export type PtzPatrolStep = {
  preset: string;
  dwell: number;
};
