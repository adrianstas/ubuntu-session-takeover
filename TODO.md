# TODO

## To verify on the host

- [ ] **GDM greeter at 100% remote scale** (commit 29dbf65). Deploy
      `dist/runtime-multimon-20261111b`, log out, connect over RDP and check
      that the login screen is shown 1:1 instead of the 150% default. The
      greeter broker log should report `"scale_percent": 100`
      (`journalctl -b | grep native-adaptive-resolution`, unit
      `ubuntu-native-greeter.service`).

## Open

- [ ] Windows mstsc "Use all my monitors" on real monitors: CI covers only the
      FreeRDP X11 client on two RandR monitors. First manual test (2026-11-11)
      worked: two monitors, correct geometry and resolution.
- [ ] A foreign `RecordVirtual` screen cast (for example a local Miracast sink)
      during a lease must stay behind the physical barrier; there is no
      integration test for it yet.
- [ ] With a fractional remote scale that a virtual monitor does not support,
      extra monitors fall back to a row to the right of the viewport instead of
      the client positions.
