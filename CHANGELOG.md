# Changelog

## [Unreleased]

## [3.1.3] - 2026-07-26

- Host **Camect Connected** status is now Disconnected / Connected / Synced
  (HTTP API up vs event websocket open)
- Re-register hub event listeners after reconnect so alerts resume
- Install `camect` from the [jimboca/camect-py](https://github.com/jimboca/camect-py)
  fork via `install.sh` (clone + `camect` symlink) until upstream ships
  websocket connected-state APIs
- Do not bump Errors when seeding default custom params; show Notices/Errors
  for empty user/password or no Camect Hosts, and clear when config is complete
- Camera **Online** status (separate from **Enabled**); online/offline events
  no longer overwrite Enabled (#10)
- Treat missing `camera` key from ListCameras as an empty list (avoid false
  hub disconnect on poll)

## [3.1.2] - 2026-07-02

- Add Fox detected-object NLS label (`ANM-12`) for Admin Console display
- Call `updateProfile()` on startup so IoX receives nodedef/editor/NLS updates
- Publish configuration help from `CONFIG.md` via markdown2
- Fix connection notices and ERR driver sync on restart
- Defer discover until typed custom data is loaded
- Ignore local `*.lock` and `*.pid` runtime files in git

## [3.1.1] - 2026-06-28

- Fix restart rehydration of Host/Camera Python objects
- Add configurable Camect port per host (#24)
- Add object name aliases for Amazon truck, USPS truck, etc. (#11)
- Remove stale cameras and orphaned hubs when config changes (#19, #22)
- Show Polyglot notices on connection failures (#21)
- Refresh GV2/GV3 on controller query (#12)
