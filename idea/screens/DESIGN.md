---
name: Nocturne Focus
colors:
  surface: '#0e141c'
  surface-dim: '#0e141c'
  surface-bright: '#333a43'
  surface-container-lowest: '#080f17'
  surface-container-low: '#161c25'
  surface-container: '#1a2029'
  surface-container-high: '#242a33'
  surface-container-highest: '#2f353f'
  on-surface: '#dde3ef'
  on-surface-variant: '#ccc7ad'
  inverse-surface: '#dde3ef'
  inverse-on-surface: '#2b313a'
  outline: '#95917a'
  outline-variant: '#4a4734'
  surface-tint: '#d8c926'
  primary: '#ffffff'
  on-primary: '#363100'
  primary-container: '#f5e644'
  on-primary-container: '#6e6600'
  inverse-primary: '#686000'
  secondary: '#c3c6d1'
  on-secondary: '#2c3039'
  secondary-container: '#434750'
  on-secondary-container: '#b2b5bf'
  tertiary: '#ffffff'
  on-tertiary: '#2e3135'
  tertiary-container: '#e1e2e8'
  on-tertiary-container: '#626469'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#f5e644'
  primary-fixed-dim: '#d8c926'
  on-primary-fixed: '#1f1c00'
  on-primary-fixed-variant: '#4e4800'
  secondary-fixed: '#dfe2ed'
  secondary-fixed-dim: '#c3c6d1'
  on-secondary-fixed: '#181c23'
  on-secondary-fixed-variant: '#434750'
  tertiary-fixed: '#e1e2e8'
  tertiary-fixed-dim: '#c5c6cc'
  on-tertiary-fixed: '#191c20'
  on-tertiary-fixed-variant: '#44474c'
  background: '#0e141c'
  on-background: '#dde3ef'
  surface-variant: '#2f353f'
typography:
  display-timer:
    fontFamily: Archivo Narrow
    fontSize: 112px
    fontWeight: '700'
    lineHeight: 104px
    letterSpacing: -0.04em
  display-timer-mobile:
    fontFamily: Archivo Narrow
    fontSize: 64px
    fontWeight: '700'
    lineHeight: 64px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Noto Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
  headline-md:
    fontFamily: Noto Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  title-sm:
    fontFamily: Archivo Narrow
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: 0.08em
  body-lg:
    fontFamily: Noto Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Noto Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  label-numeric:
    fontFamily: Archivo Narrow
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Noto Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 3rem
  margin-mobile: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

> 2026-10-31: 웹판은 이날부터 [토스판 밝은 규칙](토스판/DESIGN.md)의 색·모양을 씁니다. 이 검정 바탕 규칙과 검정 시안(1A~1F 등)은 기록으로 둡니다.

## Brand & Style

This design system embodies the solitary focus of deep nighttime work. Designed for knowledge workers, developers, and writers seeking uninterrupted flow, the emotional profile transitions between total stillness, quiet precision, and the vivid clarity of a moonlit workspace. 

The aesthetic marries **Tactile Brutalist Minimalism** with **Atmospheric Luminescence**. Interface structures are austere, geometric, and sharp—relying on uncompromising pure blacks and technical framing marks. In contrast, dynamic states introduce a soft, luminous moonlight radiance. The UI steps out of the user's conscious attention, serving as an ambient terminal for deep human concentration.

## Colors

The palette operates in extreme tonal restraint:
- **Canvas (`#000000`)**: An absolute void baseline that minimizes eye fatigue and screen glare during late-night sessions.
- **Surface Elevation (`#0F1216` to `#23272F`)**: Linear-gradient or solid flat dark navy panels that stage interactive tools without creating harsh contrast against pure black.
- **Moonlight Accent (`#FFEF4D`)**: High-chroma moonlight yellow reserved strictly for active focal states, time passage metrics, primary calls-to-action, and the active session progress glow.
- **Text & Foreground**: Primary information is set in high-contrast crisp silver-white (`#EEF0F3`), while secondary descriptors and telemetry use muted slate (`#949AA6`).
- **Dividers & Structural Framing (`#7C828D`)**: Subdued structural guides used for hairline container boundaries and reticle crosshairs.

## Typography

Typography establishes an intentional balance between functional technical instrumentation and calm East Asian legibility. 

- **Numeric & Temporal Data (`Archivo Narrow`)**: Used for the central countdown clock, cycle tallies, and control indicators. Condensed proportions maximize character density while preserving instantaneous recognition across room-scale distances.
- **Hangul & Interface Copy (`Noto Sans`)**: Delivers geometric neutrality, clear stroke hierarchy, and zero distraction when switching between Korean labels and metadata.
- Text transforms: Numerical metrics and mode flags use uppercase or tabular formatting to prevent layout jitter during active session ticks.

## Layout & Spacing

The layout utilizes a centered, focus-driven single-canvas model anchored inside a 12-column layout for desktop and a single-column stack on mobile. 

- **Desktop (1024px+)**: The active timer and session dashboard are constrained within a maximum width of 960px, suspended symmetrically against the `#000000` canvas to remove peripheral distractions.
- **Mobile (<768px)**: Margins compress to `1.25rem`. Auxiliary controls retreat into secondary draw-down states or bottom utility rails, keeping the primary timer visible within vertical thumb reach.
- **Rhythm**: Internal card gaps follow a strict 8px/16px cadence, preserving spacious breathing room around the central clock face while keeping task counters and session intervals compact.

## Elevation & Depth

Rather than conventional drop shadows, depth is manifested through optical luminescence and subtle planar shifts:

- **Surface Tiers**: Base application ground is `#000000`. Overlapping panels and workspaces adopt a vertical linear gradient from `#0F1216` at the top to `#23272F` at the base, bordered by a single hairline outline (`1px solid #7C828D` at 30% to 50% opacity).
- **Moonlight Luminescence**: Focused inputs, active cycle rings, and selected indicators project a restrained ambient bloom: `box-shadow: 0 0 24px -2px rgba(255, 239, 77, 0.28)`.
- **Ghost Reticles**: Depth is defined horizontally and vertically using crosshair intersections and hairline rulers rather than stacked surfaces.

## Shapes

The geometric posture of this design system is strictly non-rounded (`0px` border-radius across all surfaces). Panels, action triggers, toggle switches, and tabs share rigid, perpendicular corners. This architectural severity underscores the disciplined nature of timed work sessions and reinforces an intentional, retro-technical workstation character.

## Components

### Buttons
- **Primary Button**: Solid `#FFEF4D` fill with `#000000` bold typography, zero border-radius. Positioned immediately outside each of the four 90-degree corners sits an offset hairline `+` crosshair (4px arm length, `#FFEF4D` or `#7C828D`).
- **Secondary Button**: Flat transparent background, crisp `1px solid #7C828D` border, `#EEF0F3` text. On hover, the border brightens to `#EEF0F3` with an understated inner stroke illumination.

### Navigation Tabs
- Layout: Horizontal text items separated by a hairline pipe divider (`타이머 | 밤하늘`).
- Inactive: `#949AA6` neutral sans-serif copy.
- Active: `#FFEF4D` text coupled with an unbroken, 2px solid horizontal line situated at the base of the tab container, emanating a soft glow (`box-shadow: 0 2px 8px rgba(255, 239, 77, 0.45)`).

### Cards & Panels
- Background: Linear gradient from `#0F1216` (top) to `#23272F` (bottom).
- Border: `1px solid rgba(124, 130, 141, 0.45)`.
- Corner Accents: Optional subtle L-bracket or crosshair marks applied to card anchor corners to frame active statistics and timer controls.

### Inputs & Selectors
- Background: Flat `#0F1216` with a recessed `1px solid #7C828D` border.
- Active Focus: Border swaps to `#FFEF4D` with no corner rounding, paired with the moonlight yellow outer glow. Caret is colored `#FFEF4D`.

### Checkboxes & Pomodoro Counters
- Checkboxes: 16x16px square boxes with a `1px solid #7C828D` outline. When checked, the box fills solid `#FFEF4D` with a stark black check mark.
- Interval Dots: Session tally dots rendered as small, unfilled 6x6px sharp squares that fill with glowing `#FFEF4D` as intervals complete.