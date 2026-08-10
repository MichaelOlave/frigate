# MichaelOlave Frigate fork

This fork adds configurable ONVIF preset patrols to Frigate's native PTZ controls. It is
maintained for the two Tapo TCB72 cameras documented in the `LiveNetwork` repository.

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

Manual PTZ movement pauses a running patrol. Runtime start and stop do not change whether
the patrol is enabled at startup.

The UI persists the following schema in Frigate's normal `config.yml`:

```yaml
cameras:
  camera_name:
    onvif:
      patrol:
        enabled: true
        steps:
          - preset: left-window
            dwell: 10
          - preset: back-door
            dwell: 15
```

At least two steps are required when `enabled` is true. Presets are stored by the camera;
the ordered route and dwell times are stored by Frigate.
