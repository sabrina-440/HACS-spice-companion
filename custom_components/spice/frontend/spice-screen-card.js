/**
 * spice-screen-card
 *
 * A custom Lovelace card for the "spice2x Arcade" integration that shows the
 * live mirrored screen of a machine and forwards taps/clicks to it as touch
 * input (for SDVX / IIDX and other touch games).
 *
 * Configuration:
 *   type: custom:spice-screen-card
 *   entry_id: <config entry id>      # optional, or device_id: <device id>
 *   fps: 10                          # optional, frames per second (default 10)
 *   quality: 40                      # optional JPEG quality override
 *   divide: 2                        # optional downscale override
 *   screen: 0                        # optional screen index
 *   title: My Cabinet                # optional
 *
 * entry_id/device_id can be omitted if exactly one spice2x machine is
 * configured in Home Assistant - the card will find it automatically.
 */

class SpiceScreenCard extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._polling = false;
    this._frameW = 0;
    this._frameH = 0;
    this._divide = 1;
    this._touchIds = new Map(); // pointerId -> arcade touch id
    this._nextId = 100000 + Math.floor(Math.random() * 90000);
    this._objectUrl = null;
    this._built = false;
  }

  setConfig(config) {
    this._config = config || {};
    this._divide = config.divide != null ? Number(config.divide) : 1;
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) {
      this._build();
    }
    if (!this._polling && !this._error) {
      this._polling = true;
      this._loop();
    }
  }

  getCardSize() {
    return 6;
  }

  // devices registered by this integration, keyed by device id
  _spiceDevices() {
    if (!this._hass || !this._hass.devices) return [];
    return Object.values(this._hass.devices).filter((d) =>
      (d.identifiers || []).some(([domain]) => domain === "spice")
    );
  }

  _autoDeviceId() {
    const devices = this._spiceDevices();
    return devices.length === 1 ? devices[0].id : null;
  }

  _entryId() {
    if (this._config.entry_id) return this._config.entry_id;
    const deviceId = this._config.device_id || this._autoDeviceId();
    const device =
      this._hass && this._hass.devices && deviceId
        ? this._hass.devices[deviceId]
        : null;
    if (device && device.config_entries && device.config_entries.length) {
      return device.config_entries[0];
    }
    return null;
  }

  _build() {
    this._built = true;
    this._error = null;
    const card = document.createElement("ha-card");
    if (this._config.title) card.header = this._config.title;

    if (!this._entryId()) {
      const devices = this._spiceDevices();
      this._error =
        devices.length > 1
          ? "Multiple spice2x machines found - set 'device_id' or 'entry_id' to pick one."
          : "No spice2x machine found. Add the spice2x integration, or set 'device_id'/'entry_id'.";
      const msg = document.createElement("div");
      msg.style.cssText = "padding:16px;color:var(--error-color);";
      msg.textContent = this._error;
      card.appendChild(msg);
      this.appendChild(card);
      return;
    }

    const holder = document.createElement("div");
    holder.style.cssText =
      "position:relative;width:100%;line-height:0;background:#000;touch-action:none;";

    const img = document.createElement("img");
    img.style.cssText = "width:100%;height:auto;display:block;user-select:none;";
    img.draggable = false;
    this._img = img;

    holder.appendChild(img);
    card.appendChild(holder);
    this.appendChild(card);

    holder.addEventListener("pointerdown", (e) => this._onDown(e));
    holder.addEventListener("pointermove", (e) => this._onMove(e));
    holder.addEventListener("pointerup", (e) => this._onUp(e));
    holder.addEventListener("pointercancel", (e) => this._onUp(e));
    holder.addEventListener("pointerleave", (e) => this._onUp(e));
  }

  async _loop() {
    const fps = this._config.fps ? Number(this._config.fps) : 10;
    const interval = Math.max(20, Math.floor(1000 / fps));
    while (this.isConnected) {
      const start = Date.now();
      try {
        await this._fetchFrame();
      } catch (err) {
        // machine likely offline; back off a little
        await this._sleep(1000);
      }
      const elapsed = Date.now() - start;
      await this._sleep(Math.max(0, interval - elapsed));
    }
    this._polling = false;
  }

  _sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  async _fetchFrame() {
    const entryId = this._entryId();
    if (!entryId || !this._hass) return;

    const params = new URLSearchParams();
    if (this._config.quality != null) params.set("quality", this._config.quality);
    if (this._config.divide != null) params.set("divide", this._config.divide);
    if (this._config.screen != null) params.set("screen", this._config.screen);
    const q = params.toString();
    const url = `/api/spice/${entryId}/frame${q ? "?" + q : ""}`;

    const resp = await fetch(url, {
      headers: { authorization: `Bearer ${this._hass.auth.data.access_token}` },
    });
    if (!resp.ok) throw new Error(`frame ${resp.status}`);

    this._frameW = Number(resp.headers.get("X-Spice-Width")) || this._frameW;
    this._frameH = Number(resp.headers.get("X-Spice-Height")) || this._frameH;

    const blob = await resp.blob();
    const nextUrl = URL.createObjectURL(blob);
    this._img.src = nextUrl;
    if (this._objectUrl) URL.revokeObjectURL(this._objectUrl);
    this._objectUrl = nextUrl;
  }

  _toArcade(e) {
    // Map a pointer position on the rendered <img> to original-resolution
    // arcade pixel coordinates. The frame dims are post-divide, so multiply
    // by the divide factor to reach the machine's native resolution.
    const rect = this._img.getBoundingClientRect();
    if (!rect.width || !rect.height || !this._frameW || !this._frameH) return null;
    const relX = (e.clientX - rect.left) / rect.width;
    const relY = (e.clientY - rect.top) / rect.height;
    const x = Math.round(relX * this._frameW * this._divide);
    const y = Math.round(relY * this._frameH * this._divide);
    return { x, y };
  }

  async _sendTouch(action, id, x, y) {
    const entryId = this._entryId();
    if (!entryId || !this._hass) return;
    const msg = { type: "spice/touch", entry_id: entryId, action, id };
    if (x != null) msg.x = x;
    if (y != null) msg.y = y;
    try {
      await this._hass.connection.sendMessagePromise(msg);
    } catch (err) {
      // ignore transient touch errors
    }
  }

  _onDown(e) {
    const pos = this._toArcade(e);
    if (!pos) return;
    const id = this._nextId++;
    this._touchIds.set(e.pointerId, id);
    if (e.target.setPointerCapture) e.target.setPointerCapture(e.pointerId);
    this._sendTouch("down", id, pos.x, pos.y);
  }

  _onMove(e) {
    const id = this._touchIds.get(e.pointerId);
    if (id == null) return;
    const pos = this._toArcade(e);
    if (!pos) return;
    this._sendTouch("move", id, pos.x, pos.y);
  }

  _onUp(e) {
    const id = this._touchIds.get(e.pointerId);
    if (id == null) return;
    this._touchIds.delete(e.pointerId);
    this._sendTouch("up", id);
  }

  static getStubConfig() {
    return { fps: 10 };
  }
}

customElements.define("spice-screen-card", SpiceScreenCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "spice-screen-card",
  name: "spice2x Screen",
  description: "Live screen mirror with touch input for a spice2x machine.",
});

