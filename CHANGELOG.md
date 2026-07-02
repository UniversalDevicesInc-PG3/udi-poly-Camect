# Changelog

## [Unreleased]

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
