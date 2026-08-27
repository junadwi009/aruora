# 02 — ARUORA Visual System

## 1. Visual Personality

ARUORA harus terlihat:

**Clean · Soft · Intelligent · Warm · Premium · Slightly Magical**

Bukan:

- neon AI SaaS
- childish educational app
- corporate university portal
- anime-heavy learning platform
- purple-gradient-everywhere startup

---

# 2. Primary Palette

## Aura Cream
`#F4F0E9`

Fungsi:

- main light background
- landing page surface
- mascot-friendly neutral
- warm alternative to pure white

---

## Midnight Ink
`#19172B`

Fungsi:

- dark surface
- premium sections
- strong headings
- app shell dark mode

---

## Ink
`#282631`

Fungsi:

- primary body text
- icon foreground
- controls

---

## Aura Violet
`#7568F8`

Fungsi:

- primary brand accent
- CTA
- selected state
- focus state
- Aura active state

Jangan gunakan untuk seluruh background secara default.

---

## Aurora Lavender
`#A99DFB`

Fungsi:

- softer highlight
- Aura horn glow
- decorative lighting
- secondary state

---

## Horizon Blue
`#5DA7F7`

Fungsi:

- progress
- information
- listening
- transition state

---

## Aurora Mint
`#68DDD2`

Fungsi:

- success
- improvement
- positive learning movement

---

## Dawn Coral
`#F28B82`

Fungsi:

- human warmth
- warning
- speaking accent
- attention state

Bukan error-critical red.

---

## Cloud Lavender
`#F4F2FA`

Fungsi:

- secondary background
- cards
- subtle section separation

---

## Mist
`#777482`

Fungsi:

- muted copy
- supporting labels
- secondary metadata

---

# 3. Dark Mode Starter

| Token | HEX |
|---|---|
| Background | `#12111D` |
| Surface | `#1C1A2A` |
| Elevated Surface | `#252238` |
| Text | `#F4F1F8` |
| Muted | `#A8A4B2` |
| Border | `#353145` |

Primary violet tetap `#7568F8`, tetapi contrast harus diperiksa pada implementation.

---

# 4. Signature Gradient

## Aurora Signal

```css
linear-gradient(
  120deg,
  #7568F8 0%,
  #5DA7F7 55%,
  #68DDD2 100%
);
```

Gunakan hanya pada:

- achievement
- readiness improvement
- Aura activation
- major milestone
- progress visualization
- selected premium brand moment

Jangan gunakan pada:

- semua tombol
- semua card
- seluruh page background
- seluruh navbar

**Aurora is an event, not a wallpaper.**

---

# 5. Suggested Color Ratio

Light interface:

- 55–65% neutral / cream
- 20–30% ink / neutral dark
- 8–12% violet
- 3–7% blue/mint/coral accents

---

# 6. Typography

## Recommended MVP Family

**Plus Jakarta Sans**

Reasons:

- modern
- highly readable
- friendly without being childish
- suitable for Indonesian origin and global product
- supports UI and display usage

Fallback:

```css
font-family:
  "Plus Jakarta Sans",
  Inter,
  ui-sans-serif,
  system-ui,
  sans-serif;
```

---

# 7. Typography Scale

Suggested starting scale:

| Role | Size | Weight |
|---|---:|---:|
| Display XL | 48–56 | 700 |
| Display | 36–44 | 700 |
| H1 | 30–36 | 700 |
| H2 | 24–28 | 700 |
| H3 | 20–22 | 600–700 |
| Body L | 17–18 | 400 |
| Body | 15–16 | 400 |
| UI Label | 13–14 | 600 |
| Metadata | 11–12 | 500–600 |
| Metric | contextual | 700 |

Avoid excessively light font weights.

---

# 8. Shape Language

## Principle

**Soft geometry, not bubbly geometry.**

Suggested radii:

```text
xs      8px
control 12px
button  14px
card    18px
feature 24px
pill    999px
```

Rules:

- do not make every component pill-shaped
- use large radius only for hero surfaces and modal containers
- progress/readiness modules may use circular geometry

---

# 9. Signature Motifs

## Orbit

Meaning:

- learning system
- matching
- Aura awareness
- progress around a goal

---

## Spark

Symbol:

`✦`

Meaning:

- breakthrough
- insight
- improvement
- Aura presence

Use sparingly.

---

## Path

Meaning:

- journey
- study program
- milestone sequence
- destination

Prefer curved or gently segmented path over generic game-map zigzag.

---

# 10. Iconography

Recommended direction:

- Lucide-style outline icons
- rounded line endings
- 1.75–2px stroke
- simple silhouette
- no cartoon filled icons as default

Use filled icon only for:

- selected state
- milestone
- status
- reward

---

# 11. Illustration Direction

ARUORA illustration:

- soft 3D
- collectible figure aesthetic
- restrained materials
- warm lighting
- clean background
- low visual clutter

Avoid:

- glossy Pixar realism
- anime rendering
- corporate flat-vector people
- hyper-detailed fantasy art

Aura is the main character IP; additional random mascots should not be introduced without a clear need.

---

# 12. Photography Direction

Photography must feel documentary / aspirational.

Good:

- student at airport
- night study
- dorm room
- first day on campus
- train commute abroad
- preparing interview
- passport + laptop
- quiet library
- application preparation

Avoid:

- stock people pointing at whiteboards
- graduation cap cliché
- Big Ben + Tokyo Tower collage
- generic smiling multicultural stock group

Mood:

> **The moment before your life changes.**

---

# 13. Accessibility

Before production:

- validate WCAG contrast for all text/background pairs
- do not rely on color alone for correctness
- success/error requires icon/label in addition to color
- Aura animations must respect reduced-motion preferences
