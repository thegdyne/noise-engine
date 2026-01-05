# Cross-Platform Testing

Goal: Ensure Noise Engine runs on Windows and Linux, not just macOS.

## Tasks
- [ ] Recruit Windows tester (Discord?)
- [ ] Recruit Linux tester (Discord?)
- [ ] Document platform-specific setup (SC paths, Python env)
- [ ] Test PyQt5 rendering on Windows
- [ ] Test PyQt5 rendering on Linux (X11/Wayland)
- [ ] Verify OSC communication cross-platform
- [ ] Check file paths (presets dir, pack loading)
- [ ] Create Windows install guide
- [ ] Create Linux install guide

## Known Risks
- SuperCollider paths differ per OS
- Audio device APIs vary (CoreAudio vs WASAPI vs ALSA/Jack)
- Font rendering may differ
- Keyboard shortcuts (Cmd vs Ctrl)
