# MichaelOlave Frigate fork

This fork adds configurable ONVIF preset patrols to Frigate's native PTZ controls. It is
maintained for the two Tapo TCB72 cameras documented in the `LiveNetwork` repository.

It also adds per-user, per-camera live audio controls for browser playback volume and
WebRTC talk-back microphone gain. Playback ranges from 0–100%; talk-back ranges from
0–200% so quiet microphones can be amplified. These controls affect only the live browser
session and do not change camera firmware gain or recorded audio.

## Upstream boundary

- Current base: upstream tag `v0.17.2`.
- Development branch: `codex/tapo-patrol`.
- Long-lived deployment branch: `tapo-patrol-v0.17`.
- Deployment image: `ghcr.io/michaelolave/frigate:0.17.2-tapo-patrol`.

Do not merge upstream `dev` directly into the deployment branch. For an upgrade, create a
new branch from the chosen upstream release tag, cherry-pick or rebase the patrol commits,
run the image workflow, and update the image tag in `LiveNetwork/cameras/compose.yml` only
after camera tests pass.

## Added behavior

An administrator can open a camera's PTZ controls and select the route button to:

- save the camera's current position as a named ONVIF preset;
- delete presets that are not referenced by a patrol;
- arrange presets into an ordered repeating route;
- set a dwell time from 1 to 3600 seconds for each route step;
- start or stop the saved route; and
- choose whether the route starts automatically with Frigate.
- optionally pause the route to follow a detected object, then resume after the target is
  out of view for the configured autotracking timeout.

Manual PTZ movement pauses a running patrol. Runtime start and stop do not change whether
the patrol is enabled at startup. A running patrol retries its ONVIF connection every five
seconds after a camera disconnect and resumes from the first route step once reconnected.
Object following uses Frigate's object detector rather than raw pixel motion. Cameras that
only advertise ONVIF `TranslationGenericSpace` can opt into a conservative scaled-move
fallback with `onvif.autotracking.generic_relative`; it is disabled by default.

The UI persists the following schema in `/config/ptz_patrol.yml`:

```yaml
cameras:
  camera_name:
    enabled: true
    object_tracking: true
    steps:
      - preset: left-window
        dwell: 10
      - preset: back-door
        dwell: 15
```

At least two steps are required when `enabled` is true. Presets are stored by the camera;
the ordered route and dwell times are stored by Frigate. Keeping this state in its own file
lets deployment tooling replace `config.yml` without erasing routes created in the UI.
