# spice2x Arcade

Control [spice2x](https://spice2x.github.io/) arcade machines directly from Home Assistant — no
SSH or shell scripts required. Insert IC cards and enter PINs, take screenshots, mirror the live
screen, send touch input (SDVX / IIDX), and drive the full spice API.

## Prerequisites

- A PC running **spice2x** with the API enabled (launched with the API flag; the same setup used by
  the **spice companion** app). For IIDX TDJ mode, also launch with `-iidxpoke`.
- The machine must be reachable from Home Assistant on your network.
- You'll need the host **IP/hostname**, **API port** (default `57300`), and the **API password**
  (the same values you use in the spice companion app; the default password is usually `changeme`).
- Screen mirroring requires spice2x's screen-capture support (graphics hook) to be active.

## Setup

1. Add the integration via **Settings → Devices & Services → Add Integration → spice2x Arcade**.
2. Enter the host, port, password, and a friendly name. Each machine becomes its own device.
3. Open the device's **Configure** (options) to add your **cards** (name + card number + PIN) and to
   tune the PIN delay and screen-mirror quality.

## Using it

- A **Card side** selector (Player 1 / Player 2) picks which side inserts and screenshots target.
- Each configured card gets an **Insert &lt;name&gt;** button.
- A **Screenshot** button and a **Screen** camera are created per machine.
- Add the bundled **spice2x Screen** Lovelace card for a live, tappable screen mirror.
- Services (`spice.insert_card`, `spice.insert_double`, `spice.keypad_write`, `spice.touch`,
  `spice.control`, and more) expose the full API for automations.

Credits to the spice2x team for the spice API and companion app.
