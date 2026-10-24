# Home lower screens — revised composition

Scope: home second/third screens only, via `dist/assets/home-focus.js` and `home-focus.css`. Existing intro source, workbench, robot and last archive page remain unchanged. Native first hero markup is returned from existing home function before lower screens are replaced.

## Assets

Built-in image generation, not external documentary photography:
- `dist/assets/orchard-close-v2.webp`: art-directed autumn branch, soft Taihang-inspired distant mountain, matte fruit. Marked as artistic scene in UI.
- `dist/assets/persimmon-specimen-v2.webp`: genuinely transparent matte persimmon specimen. Color simulated with CSS hue/saturation; independent masked calyx copy reduces stem/leaf recoloring. No inference.

Generation briefs / final prompt set:
1. Photorealistic-natural premium cinematic website background, landscape 3:2. Intimate late-autumn persimmon branch inspired by Taihang rural China; three irregular matte orange-red fruit at 68%/48%, 85%/30%, 52%/63%; dry green-brown calyx, speckled skin, weathered bark, sparse olive leaves. Deep grey-green negative space left 40%, very softly defocused blue-grey mountain and forest. Soft overcast lighting, restrained warm edge, fine grain and shallow focus. No oily/plastic skin, snow, table, frame, UI, lettering, golden sun, illustration or thick fog.
2. Product-mockup botanical specimen asset: single squat naturally irregular orange persimmon on true transparent background, front/slightly above view, generous margin, dry olive-brown four-lobed calyx and short stem. Matte burnt orange porous skin, natural dusty bloom, soft top-left studio light and shadowed bottom-right. Premium macro editorial photography. No wet reflections, plastic toy look, watercolor, floor, cast ground shadow, labels or additional objects.

## Interaction

Orchard: pointer-following subtle camera movement, two hotspots, in-place zoom, inline note, Esc/return restores triggering focus. Touch-specific crop and hotspot positions.

Color specimen: single isolated fruit, continuous range with snap on release, four keyboard-accessible stage buttons, static background/copy, desktop texture magnifier, reduced-motion fallback. Stage is explicit exterior-color simulation, not actual fruit maturation, quality measurement or detection output.

## Validation

- Syntax checked new JS.
- Compared original HTML after stripping only the two new imports: identical.
- Workbench and previous experience source/CSS diffs empty, preserving other routes.
- Desktop: both hotspots, return/Esc, range End, stage button selection, inspected complete screen two/three screenshots.
- Narrow 390px iframe: orchard crop, hotspots and stage selection inspected; one column color layout and button operation verified.
- No new backend or network upload behavior.

Screenshots: `docs/home-orchard-v2.jpg`, `docs/home-season-v2.jpg`.
