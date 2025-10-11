# Ecowitt MQTT Bridge (Custom Integration)
# WARNING: THIS IS IN ALPHA STAGE - IT WORKS BUT IT'S NOT MEANT FOR "EASY USE" :WARNING - EXPERIENCED USERS ONLY

# PERSONALLY I RECOMMEND USING THE ADD-ON - I PREFER THE OUTPUT OF DEVICES TO THIS ATTEMPT
# YOU CAN FIND THE ADD-ON VERSION HERE: https://github.com/dropqube/ecowitt_mqtt_addon

A lightweight **Home Assistant integration** that listens to **Ecowitt flat MQTT uploads**
(e.g. from GW1100, GW2000, GW3000) and publishes **MQTT Discovery sensors** automatically.
Subscribe to **Ecowitt flat MQTT uploads** (e.g. GW3000) and publish **Home Assistant MQTT Discovery** sensors with correct units (HA system units by default, optional overrides). The bridge keeps MQTT as the primary data source and augments it with the Ecowitt LAN API for device metadata where available.

## ✨ Features

- Parses Ecowitt flat MQTT payloads (`ecowitt/#`) and publishes retained HA MQTT discovery messages
- Creates dedicated Home Assistant devices for the gateway and known outdoor sensor heads (WH90 / WH69) when available
- Adapts units to your HA system settings (metric/imperial) with optional per-measurement overrides
- Uses the Ecowitt LAN API as a metadata-only fallback for device names, IDs and signal quality
- Allows new MQTT keys to be added via configuration for quick compatibility with new firmware
- No external dependencies — uses HA’s MQTT integration

---
## Prerequisites

- latest firmware on your Ecowitt Gateway
- Log into your Gateway
- Go to -> Weather Services -> Scroll down to "Customized"
- Settings:
  -   Customized: Enabled
  -   Protocol Type: MQTT
  -   Host: ENTER YOUR HOME ASSISTANT IP ADRESS here, e.g. 192.168.0.40
  -   Port: ENTER YOUR MQTT PORT the default is **1883**
  -   Publish Topic: ecowitt/NUMBER <- there might already be a value here, for example ecowitt/0912377902873, just leave that in! You might need this entry for the configuration! So copy that to your clipboard
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
   - Optional LAN access (base URL + refresh interval) for additional device metadata
   - Optional unit overrides (leave blank to follow HA)
   - Optional custom sensor definitions (JSON list)

---

## ⚙️ Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `in_topic` | MQTT topic to listen on (e.g. `ecowitt/#`) | `ecowitt/#` |
| `discovery_prefix` | MQTT discovery prefix | `homeassistant` |
| `state_prefix` | MQTT state prefix | `ecowitt_ha` |
| `use_local_api` | Enable LAN mapper for device metadata fallback | `False` |
| `base_url` | Gateway base URL (e.g. `http://192.168.0.46`) | empty |
| `lan_timeout` | Timeout for LAN calls (seconds) | `5` |
| `map_refresh_sec` | Poll interval for LAN sensor map (seconds) | `600` |
| `unit_temperature` | Override (C / F) | follow HA |
| `unit_wind` | Override (m/s / km/h / mph) | follow HA |
| `unit_rain` | Override (mm / in) | follow HA |
| `unit_pressure` | Override (hPa / inHg) | follow HA |
| `custom_sensors` | JSON array with additional MQTT keys / metadata | empty |

### Custom sensors

Some Ecowitt firmware versions introduce new MQTT keys before the integration is updated. You can add them yourself by
providing JSON in the **Custom sensors** field. Example:

```json
[
  {
    "key": "soilmoisture1",
    "name": "Soil Moisture 1",
    "device": "gateway",
    "convert": "float",
    "unit": "%",
    "precision": 1
  },
  {
    "key": "temp2f",
    "name": "Greenhouse Temperature",
    "convert": "temperature_f",
    "device": "hwid:B708"
  }
]
```

- `device` accepts `gateway`, `outdoor`, or `hwid:XXXX` to pin the entity to a specific sensor head when the LAN API reports it.
- `convert` supports presets such as `float`, `temperature_f`, `temperature_c`, `pressure_inhg`, `wind_mph`, `rain_in`, `text`
  and more.
- `unit` overrides the displayed unit for generic `float`/`text` conversions.
- `precision` controls rounding for `float` converters.

---

## Notes
- Ensure your Gateway publishes to your MQTT broker (Ecowitt → MQTT upload).
- **If you tested other bridges/add-ons before, consider clearing retained discovery topics to avoid duplicates.**
- Pressure conversion assumes flat uploads use **inHg**; LAN responses (fallback) use **hPa**.
- Works with GW1100/GW2000/GW3000 MQTT uploads.
- Uses HA’s built-in MQTT client (no external dependencies).
- Units auto-convert to HA settings or user overrides. Metric / imperial switching follows Home Assistant 2025 guidelines.
- LAN polling failures are logged but do not break MQTT processing. When the LAN API is offline, all entities stay attached to the gateway device.

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






