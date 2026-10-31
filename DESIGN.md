# Design: CitizenAssist

The locked system. Every Hallmark run reads this first and pages share it. Change it on purpose; the file is the rule.
SPEC §10 outranks this file, and this file outranks the Hallmark theme it adapts.

## System
- Genre: modern-minimal
- Shape of the first page: app screens
- Theme: Wayfind, adapted. Picked by hand: the dealt themes could not meet "light background, navy primary".
- Axes: light/grotesk-sans/cool, posture: committed

## Adaptations from Wayfind
- Noto Sans, Noto Sans Devanagari and Noto Sans Gurmukhi replace Chivo Mono, which has no Hindi or Punjabi glyphs.
- Navy replaces cobalt as the accent.
- Green, amber and red exist only as scheme status, always with an icon and a text label.
- Fonts are self-hosted in `frontend/public/fonts/` so they load with Wi-Fi off.

## Tokens
`frontend/src/tokens.css` is the source of truth. Colours and fonts live in Tailwind's `@theme`, so `bg-paper`, `text-ink` and `border-rule` work. The default Tailwind palette is switched off on purpose.

| Role | Tokens |
| --- | --- |
| Surfaces | `paper`, `paper-2`, `paper-3` |
| Text and rules | `ink`, `ink-2`, `muted`, `rule`, `ink-rule` |
| Action | `accent`, `accent-hover`, `accent-ink`, `focus` |
| Figures on ink | `accent-2` |
| Status | `eligible`, `unknown`, `ineligible`, each with a `-tint` |

## Surfaces
- 2px ink borders, radius 0 everywhere. Depth comes from borders, not shadows.
- The plate: a square bordered field holding one instruction and its figure. Use it for the unlock plan steps.
- Status as full-width rows; the unlock plan as joined steps.

## Controls
- Primary: `.btn .btn-primary`, navy fill, square, 48px high.
- Secondary: `.btn`, transparent with a 2px ink border, same size.
- Choice sets: `.cell` inside a 2px border, chosen state is ink with paper text.

## Motion
- Character: severe. Colour changes in `steps(1)`, no scroll reveals, nothing loops.

## Copy
- Sentence case, short and imperative. No eyebrows and no tracked capitals.
- Never an invented number. Metrics come only from `scripts/run_evaluation.py`.

## Linting
`node .claude/skills/hallmark/scripts/sloplint.mjs frontend/src/index.css --scope app --genre modern-minimal --url http://localhost:5173/<route> --render`

The render tier needs `puppeteer-core`; without it only the static checks run.
