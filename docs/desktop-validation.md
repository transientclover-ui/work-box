# Desktop validation

The automated suite covers storage, adapters, process lifecycle and a Qt offscreen shell smoke test. A real Qt Wayland window was also launched on the current KDE session, populated with temporary data, captured, and closed. That is a startup/layout check, not full desktop certification.

Before claiming full desktop support in a stable release, manually perform this matrix on **KDE Plasma Wayland** and **Omarchy/Hyprland Wayland**:

- Launch with the desktop's existing Qt integration, without changing its configuration.
- Verify system font, palette, accent, icons and native folder/file dialogs.
- Change system appearance while the window is open; test Light and Dark, then System.
- Test keyboard-only navigation, large fonts, fractional scaling, long paths and a small display.
- Drop files and folders from Dolphin and the user's Hyprland file manager. Verify no source file moves or duplicates.
- Create in an existing directory, attempt duplicate creation, reopen, and inspect references.
- Open associated folders with the default file manager; check missing-path feedback.
- Authenticate Codex externally, run a small authorized task in a throwaway project, inspect output and results.
- HALT during execution, close during execution, terminate only the GUI, and reopen the Box.
- Disconnect external storage and simulate disk-full errors. Never use valuable user files for fault tests.

Hyprland interaction, live system-theme changes, physical drag/drop, native dialogs and real paid worker tasks have not yet been manually validated in this session. Bundled Qt plugin compatibility is a packaging concern to resolve before a distribution release.
