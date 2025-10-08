# Ecowitt MQTT Bridge (Custom Integration)
A lightweight **Home Assistant integration** that listens to **Ecowitt flat MQTT uploads**
(e.g. from GW1100, GW2000, GW3000) and publishes **MQTT Discovery sensors** automatically.
Subscribe to **Ecowitt flat MQTT uploads** (e.g. GW3000) and publish **Home Assistant MQTT Discovery** sensors with correct units (HA system units by default, optional overrides).

## ✨ Features

- Parses Ecowitt flat MQTT payloads (`ecowitt/#`)
- Auto-creates Home Assistant sensors via MQTT Discovery
- Adapts units to your HA system settings (metric/imperial)
- Optional unit overrides in the config
- No external dependencies — uses HA’s MQTT integration

---
##Prerequisites

- latest firmware on your Ecowitt Gateway
- Log into your Gateway
- Go to -> Weather Services -> Scroll down to "Customized"
- Settings:
  -   Customized: Enabled
  -   Protocol Type: MQTT
  -   Host: ENTER YOUR HOME ASSISTANT IP ADRESS here, e.g. 192.168.0.40
  -   Port: ENTER YOUR MQTT PORT the default is **1883**
  -   Publish Topic: ecwoitt/<NUMBER> <- there might already be a value here, just leave that in! You might need this entry for the configuration! So copy that to your clipboard
  -   Transport: MQTT over TCP
  -   Upload Interval: choose your own. Less than 30s is usually useless, the default is 60s and should be sufficient
  -   Client Name: use default value or as you prefer
  -   Username: NOTE: you shouldn't need a username. if it doesn't publish the topics, enter your mqtt user here
  -   Password: see above, but enter the mqtt users password
  -   Click Save

## Installation (HACS)
1. In HACS → **Integrations → ⋮ → Custom repositories**  --- or check for availability (in that case don't add the custom repository)

   - Add: `https://github.com/dropqube/ecowitt_mqtt_bridge`
   - Category: **Integration**
2. Install **Ecowitt MQTT Bridge**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration → Ecowitt MQTT Bridge**.
5. Configure:
   - **In topic**: `ecowitt/#` (or your exact topic like `ecowitt/048308785133`)
   - Optional unit overrides (leave blank to follow HA).

---

## ⚙️ Configuration

| Option | Description | Default |
|--------|--------------|----------|
| `in_topic` | MQTT topic to listen on (e.g. `ecowitt/#`) | `ecowitt/#` |
| `discovery_prefix` | MQTT discovery prefix | `homeassistant` |
| `state_prefix` | MQTT state prefix | `ecowitt_ha` |
| `unit_temperature` | Override (C / F) | follow HA |
| `unit_wind` | Override (m/s / km/h / mph) | follow HA |
| `unit_rain` | Override (mm / in) | follow HA |
| `unit_pressure` | Override (hPa / inHg) | follow HA |

---

## Notes
- Ensure your Gateway publishes to your MQTT broker (Ecowitt → MQTT upload).
**- If you tested other bridges/add-ons before, consider clearing retained discovery topics to avoid duplicates.**
- Pressure conversion assumes flat uploads use **inHg**; LAN responses (future mode) use **hPa**.
- Works with GW1100/GW2000/GW3000 MQTT uploads.
- Uses HA’s built-in MQTT client (no external dependencies).
- Units auto-convert to HA settings or user overrides.

## Issues / Feedback
Please open issues or feature requests in this repository.

---

## 🪄 Example

After adding, you’ll see entities like:

sensor.ecowitt_gateway_785133_outdoor_temperature
sensor.ecowitt_gateway_785133_wind_speed
sensor.ecowitt_gateway_785133_uv_index
---

## 🧾 License


MIT License © 2025 dropqube

