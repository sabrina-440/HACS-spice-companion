# spice2x Arcade — Home Assistant integration

A HACS-installable Home Assistant integration that talks **natively** to
[spice2x](https://spice2x.github.io/) arcade machines over the spice API. 
Home Assistant connects to your machine(s) directly so you can log in
with a card + PIN, take screenshots, mirror the live screen, and send touch input from your
dashboard, phone, watch, or voice.

## Features

- **Multiple machines** — add each spice2x host in the UI; each becomes its own device.
- **Cards + PINs** — configure cards (name / number / PIN) and insert them with one tap.
- **Pick the side** — a per-machine **Card side** selector (Player 1 / Player 2) chooses where cards
  and screenshots go.
- **Screenshots** — a button per machine (and a `spice.screenshot` service).
- **Screen mirroring** — a **Camera** entity per screen, plus a bundled interactive Lovelace card.
- **Touch input** — tap/click on the live screen (SDVX / IIDX) via the custom card, or the
  `spice.touch` service.
- **Full API** — services for keypad, buttons, lights, coin, control (restart/exit/shutdown/reboot),
  and the IIDX ticker.

## Prerequisites

- A PC running **spice2x** with its **API enabled** (the same setup the spice companion app uses).
  For IIDX TDJ mode, also launch spice2x with `-iidxpoke`.
- The machine reachable from Home Assistant (same LAN, or via VPN — exposing it publicly is not
  recommended).
- The host **IP/hostname**, **API port** (default `57300`), and **API password** (default is often
  `changeme`). These match your spice companion app settings.

## Installation

### HACS (recommended)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**, add
   `https://github.com/sabrina-440/whatever` as an **Integration**.
2. Install **spice2x Arcade** and **restart Home Assistant**.
3. Add it via **Settings → Devices & Services → Add Integration → spice2x Arcade**.

### Manual

Copy `custom_components/spice` into your Home Assistant `config/custom_components/` directory and
restart Home Assistant.

## Configuration

1. **Add Integration → spice2x Arcade**, then enter host, port, password, and a name. The setup step
   tests the connection before creating the device.
2. Open the device and choose **Configure** to:
   - **Add / remove cards** (name, 16-digit card number, PIN).
   - Adjust **settings**: PIN delay (warm-up wait before entering the PIN, default 7s), double-insert
     stagger, and screen-mirror quality/downscale.

## Entities created per machine

| Entity | Purpose |
| --- | --- |
| `select` **Card side** | Choose Player 1 / Player 2 for inserts and screenshots. |
| `button` **Insert &lt;name&gt;** | One per configured card — inserts it on the selected side and enters the PIN. |
| `button` **Screenshot** | Takes a screenshot on the selected side. |
| `camera` **Screen** | Live JPEG mirror of the machine's screen (one per detected screen). |

## Live screen + touch (Lovelace card)

If you add the screen feed as a camera to your dash board touch will **NOT WORK**, you need to add the custom card.

The integration bundles a custom card that shows the live screen and forwards taps/clicks as touch
input. Add it to a dashboard:

```yaml
type: custom:spice-screen-card
entry_id: <your config entry id>   # or: device_id: <your device id>
fps: 10          # optional
quality: 40      # optional
divide: 2        # optional
title: My Cabinet
```

The card is auto-registered as a frontend resource — no manual resource setup needed. To find the
`entry_id`, open the device page in Settings → Devices & Services and copy the id from the URL, or
use `device_id` instead (from the same page).
If it does not show up you can add it as a resource in Settings → Dashboards → ⋮ (top right) → Resources → + Add Resource or try full hard restart of your HA instance.

## Services

All services target a device (your machine):

- `spice.insert_card` — card_number, pin, side, pin_delay
- `spice.insert_double` — card_number/pin + card_number2/pin2, side, pin_delay, stagger
- `spice.keypad_write` — side, values
- `spice.screenshot` — side
- `spice.button_press` — buttons `[[name, value], ...]`
- `spice.lights_write` — lights `[[name, value], ...]`
- `spice.coin_insert` — amount
- `spice.touch` — points `[[id, x, y], ...]` / `spice.touch_reset` — ids `[id, ...]`
- `spice.control` — action: restart / exit / shutdown / reboot
- `spice.iidx_ticker_set` — text

## Credits

All credits to the **spice2x** team for the spice API and the spice companion app, on which the
vendored `spiceapi` library and the mirroring/touch protocol are based.
