# Changelog

## 0.3.2
- Added LAN mapper that enriches MQTT discovery with WH90 / WH69 devices while keeping MQTT as the primary data source
- Published retained discovery payloads with availability topics and availability updates
- Added custom sensor configuration to allow users to describe new MQTT keys without code changes
- Implemented unit override handling (temperature, wind, rain, pressure) in line with Home Assistant 2025 guidelines
- Improved documentation, translations, and error handling for LAN polling and MQTT processing

## 0.3.0
- Initial HACS-ready release
- MQTT flat upload parsing
- MQTT Discovery publishing
- Unit conversion with HA overrides
