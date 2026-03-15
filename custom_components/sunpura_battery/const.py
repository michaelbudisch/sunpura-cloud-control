"""Constants for the Sunpura Battery Control integration."""

# This is the internal name of the integration, it should also match the directory
# name for the integration.
DOMAIN = "sunpura_battery"
BASE_URL = "https://monitor.ai-ec.cloud:8443"

CONF_POLL_INTERVAL_SECONDS = "poll_interval_seconds"
DEFAULT_POLL_INTERVAL_SECONDS = 5
MIN_POLL_INTERVAL_SECONDS = 1
MAX_POLL_INTERVAL_SECONDS = 60
