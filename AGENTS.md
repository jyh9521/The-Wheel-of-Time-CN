# Localization engineering instructions

Read docs/LOCALIZATION_STANDARD.md, BUILDING.md, TRANSLATING.md, TECHNICAL.md
and LICENSING.md before architecture changes.

- Treat this as a reusable localization framework. Locale data belongs in locales/.
- Keep Unreal/WoT engine constraints in profiles/ or documented adapter modules.
- Source game files are read-only inputs. Reject unknown fingerprints.
- Preserve research history and distinguish runtime evidence from inference.
- Do not commit original game assets or proprietary fonts.
- Run synthetic tests and optional owned-game integration before pushing.
- Supported QA scope starts at 1366x768; prioritize 1080p, 1440p and 4K.
- No mass translation, executable patch, DLL injection, or map/logic changes
  without a separately selected task.
