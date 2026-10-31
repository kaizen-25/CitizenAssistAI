# Design: CitizenAssist

The locked system. Every Hallmark run reads this first and pages share it. Change it on purpose; the file is the rule.
SPEC §10 outranks this file, and this file outranks the Hallmark theme it adapts.

## System
- Direction: civic paper, chosen by the team on 2026-10-31. It should feel like a trustworthy official document.
- Genre: editorial
- Shape: app screens, with the landing page as the one marketing screen
- Theme: Editorial, adapted
- Axes: light/serif/warm, posture: restrained

## Adaptations from Editorial
- Noto Serif and Noto Serif Devanagari set the heads, replacing the theme's condensed sans, which has no Hindi glyphs.
- Noto Sans and Noto Sans Devanagari set reading text and controls.
- Navy replaces the theme's green as the action colour (SPEC §10), and marigold is the one signature accent.
- Green, amber and red exist only as scheme status, always with an icon and a text label.
- Fonts are self-hosted in `frontend/public/fonts/` so they load with Wi-Fi off.

## Tokens
`frontend/src/tokens.css` is the source of truth. Colours and fonts live in Tailwind's `@theme`, so `bg-paper`, `text-ink` and `border-rule` work. The default Tailwind palette is switched off on purpose.

| Role | Tokens |
| --- | --- |
| Surfaces | `paper`, `paper-2`, `paper-3` |
| Text and rules | `ink`, `ink-2`, `muted`, `rule`, `rule-2`, `ink-rule` |
| Action | `accent`, `accent-hover`, `accent-ink`, `focus` |
| Signature | `accent-2`, `accent-2-tint` |
| Status | `eligible`, `unknown`, `ineligible`, each with a `-tint` |

## Surfaces
- Warm uncoated paper. A 2px ink rule opens a table or ledger, and 1px hairlines part the rows.
- Depth is a paper step, `paper-2` for a well and `paper-3` for a sheet. Only the landing slip casts a shadow.
- Radius is 3px on controls and chips. The seals are the only circles.
- Excerpts from official sources sit in a `paper-2` well in the serif, so their words read apart from ours.

## Signature
The document plan is a route of marigold seals joined by one stem. It appears on the landing slip, the plan page and the packet.

## Screens
- Results: the three counts lead as a ledger, with the actions and the Ask panel beside the rows.
- Scheme: each rule is a row, with its outcome on the left and the explanation and excerpt on the right.

## Controls
- Primary: `.btn .btn-primary`, navy fill, 48px high.
- Secondary: `.btn`, transparent with a 1px ink border, same size.
- Choice sets: `.cell` inside a hairline, chosen state is navy with light text.

## Motion
- State only: colour eases over `--dur-micro`, no scroll reveals, nothing loops.

## Copy
- Sentence case, short and imperative. No eyebrows and no tracked capitals.
- Never an invented number. Metrics come only from `scripts/run_evaluation.py`.

## Linting
`node .claude/skills/hallmark/scripts/sloplint.mjs frontend/src/index.css --scope app --genre editorial --url http://localhost:5173/ --url http://localhost:5173/assess --render`

The render tier needs `puppeteer-core`. Keep it outside the project and point `HALLMARK_PUPPETEER` at its folder, with `CHROME_PATH` set to Chrome.
