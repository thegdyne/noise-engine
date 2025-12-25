# Quick HOWTO: Generate Packs from Images

**Full reference:** `GENERATOR_PACK_SESSION.md`

---

## Workflow

1. **New Claude chat**
2. **Upload `GENERATOR_PACK_SESSION.md`** + your image
3. **"Generate a pack inspired by this image"**
4. **Review proposal** — ask for changes if needed
5. **"Looks good, generate it"** — get `.tar.gz` archive

## Install

```bash
cd ~/repos/noise-engine
tar -xzf {pack_id}.tar.gz -C packs/
cp packs/{pack_id}/{pack_id}.json ~/noise-engine-presets/
# Restart Noise Engine, select pack from dropdown
```

## Tips

- Be specific: "dark and rhythmic" / "bright and evolving"
- Ask for role balance: 1-2 each of bed/accent/foreground/motion
- If params feel generic, ask for more thematic P1-P5 controls

## Validate (Optional)

```bash
python tools/forge_validate.py packs/{pack_id}/ --verbose
python tools/forge_audio_validate.py packs/{pack_id}/ --render
```

---

See `GENERATOR_PACK_SESSION.md` for schemas, synthesis methods, and troubleshooting.
