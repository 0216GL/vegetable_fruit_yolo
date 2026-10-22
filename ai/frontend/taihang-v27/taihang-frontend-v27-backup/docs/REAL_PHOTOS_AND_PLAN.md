# Real photography and supplied project plan

## Scope

Home lower screens now consume real photography, retaining the continuous color slider and 2.25× image magnifier. No image-generation tools were used for this update. Opening animation, recognition workbench, robot, and archive interaction design are preserved. Photo layout and bindings extend `home-focus` via `real-photos.js`/`.css`.

## Attribution and licenses

All four photographs are Wikimedia Commons originals licensed CC BY-SA 4.0. Source, author, license, and alterations are also available in the home photo credits. Display rescaling, crop, lighten blending and optional hue/saturation simulation are adaptations of the photographic assets, licensed CC BY-SA 4.0. This licensing statement covers photo adaptations, not unrelated application code. WebP conversion retains photographic pixels; no generated image content or illustrated replacement.

- `assets/orchard-real-branch.webp` — Salvador Escriva, Caquis en el árbol, original 4592×3056. https://commons.wikimedia.org/wiki/File:Caquis_en_el_%C3%A1rbol.jpg
- `assets/persimmon-real-yellow.webp` — Rodrigo.Argenton, Caqui chocolate em fundo preto 04, original 2941×1948. https://commons.wikimedia.org/wiki/File:Caqui_chocolate_em_fundo_preto_04.jpg
- `assets/persimmon-real-red.webp` — Rodrigo.Argenton, Caqui rama forte em fundo preto 01, original 4374×2590. https://commons.wikimedia.org/wiki/File:Caqui_rama_forte_em_fundo_preto_01.jpg
- `assets/persimmon-real-angle.webp` — Rodrigo.Argenton, Caqui rama forte em fundo preto 02, original 3912×2505. https://commons.wikimedia.org/wiki/File:Caqui_rama_forte_em_fundo_preto_02.jpg
- License: https://creativecommons.org/licenses/by-sa/4.0/

These are different cultivars/conditions; red and alternate views show the same variety. No claim that these are Taihang fieldwork, team-owned photographs, or ground-truth model grade samples. Slider is color simulation, not real ripening. Original-color toggle removes simulation filters. Magnifier uses exact displayed-image coordinate mapping at 2.25×. Mobile uses an expandable original-photo detail with pan and close/focus return.

## Plan material used

User supplied: 项目计划书-太行智农-定稿(5).docx, October 2026. Read from provided attachment, unchanged. Public site does not expose the full document.

Archive updated selectively:
- Four exterior classes and dataset-specific mean hue statistics from §3.5, explicitly not universal thresholds.
- Dataset records: 443 classification images (353 training /90 validation), 108 detection images (92/16), §3.14. No independent test set yet.
- Plan's recorded validation top-1 88.89% (80/90), detection mAP@0.5 90.87%. Explicitly different tasks, not end-to-end/production accuracy.
- Per-class recall and training parameter comparison figures extracted directly from document `image14.jpg`, `image15.jpg`, converted to `project-recall.webp`, `project-adaptation.webp`. No chart values redrawn.
- YOLO11n detection + YOLO11n-cls classification, reported combined size about 8.27 MB.
- Distinguish documented completed backend development from this presentation site's currently unconnected model.
- Team fieldwork narrative is attributed to plan, while original field samples remain not publicly displayed. Online photographs never presented as team evidence.

## Verification

JS syntax checked. Desktop: orchard hotspot/Esc return, stage selection, range Home, original-color switch, photograph magnifier source/coordinates, archive experimental content/figure. Mobile 390px iframe: stage selection and photo detail open/close verified visually. Original HTML after removing only new CSS/script imports is identical to previous; recognition files and robot source unchanged. Temporary QA iframe removed.
