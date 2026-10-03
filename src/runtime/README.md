# Runtime layer

No hook, injected DLL or engine binary patch currently exists or is required for the verified BMP PoC.
Resource adapters live in tools/font and tools/pack. Add runtime code only after a separately
verified resource limitation and explicit task selection; preserve this separation.
