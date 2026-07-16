"""Constants for the spice2x Arcade integration."""

from __future__ import annotations

DOMAIN = "spice"

# config entry data
CONF_HOST = "host"
CONF_PORT = "port"
CONF_PASSWORD = "password"
CONF_NAME = "name"

DEFAULT_PORT = 57300
DEFAULT_NAME = "spice2x Arcade"

# options: configured cards
CONF_CARDS = "cards"
CONF_CARD_NAME = "name"
CONF_CARD_NUMBER = "card_number"
CONF_CARD_PIN = "pin"

# options: behaviour tuning
CONF_PIN_DELAY = "pin_delay"
CONF_DOUBLE_STAGGER = "double_stagger"
CONF_SCREEN_QUALITY = "screen_quality"
CONF_SCREEN_DIVIDE = "screen_divide"

DEFAULT_PIN_DELAY = 7  # seconds; device warm-up before PIN entry
DEFAULT_DOUBLE_STAGGER = 1  # seconds between the two PIN writes
DEFAULT_SCREEN_QUALITY = 40  # JPEG quality 0-100 for the screen mirror
DEFAULT_SCREEN_DIVIDE = 2  # downscale factor for the screen mirror
DEFAULT_SCAN_INTERVAL = 15 # seconds for polling connectivity

# player sides
SIDE_P1 = 0
SIDE_P2 = 1
SIDES = [SIDE_P1, SIDE_P2]

SIDE_LABELS = {SIDE_P1: "Player 1", SIDE_P2: "Player 2"}

# keypad value that triggers a screenshot on the host
SCREENSHOT_KEYPAD_VALUE = "9"

# service names
SERVICE_INSERT_CARD = "insert_card"
SERVICE_INSERT_DOUBLE = "insert_double"
SERVICE_KEYPAD_WRITE = "keypad_write"
SERVICE_SCREENSHOT = "screenshot"
SERVICE_BUTTON_PRESS = "button_press"
SERVICE_LIGHTS_WRITE = "lights_write"
SERVICE_COIN_INSERT = "coin_insert"
SERVICE_TOUCH = "touch"
SERVICE_TOUCH_RESET = "touch_reset"
SERVICE_CONTROL = "control"
SERVICE_IIDX_TICKER = "iidx_ticker_set"

# control actions exposed by the control service
CONTROL_ACTIONS = ["restart", "exit", "shutdown", "reboot"]

# service field names
ATTR_CARD_NUMBER = "card_number"
ATTR_PIN = "pin"
ATTR_CARD_NUMBER2 = "card_number2"
ATTR_PIN2 = "pin2"
ATTR_SIDE = "side"
ATTR_PIN_DELAY = "pin_delay"
ATTR_STAGGER = "stagger"
ATTR_VALUES = "values"
ATTR_BUTTONS = "buttons"
ATTR_LIGHTS = "lights"
ATTR_AMOUNT = "amount"
ATTR_POINTS = "points"
ATTR_IDS = "ids"
ATTR_ACTION = "action"
ATTR_TEXT = "text"

# frontend
FRONTEND_CARD_FILENAME = "spice-screen-card.js"
FRONTEND_CARD_URL = f"/{DOMAIN}/{FRONTEND_CARD_FILENAME}"

# websocket command
WS_TYPE_TOUCH = f"{DOMAIN}/touch"
