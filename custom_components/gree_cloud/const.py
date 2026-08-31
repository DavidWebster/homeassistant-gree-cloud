"""Constants for the Gree Climate Cloud integration."""

DOMAIN = "gree_cloud"

# Config flow constants
CONF_SERVER = "server"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Update intervals
UPDATE_INTERVAL = 60  # Cloud polling interval in seconds
DISCOVERY_TIMEOUT = 10

# Error thresholds
MAX_ERRORS = 3
MAX_EXPECTED_RESPONSE_TIME_INTERVAL = 180

# Dispatcher signals
DISPATCH_DEVICE_DISCOVERED = f"{DOMAIN}_device_discovered"

# Fan modes (matching official integration)
FAN_MEDIUM_LOW = "medium low"
FAN_MEDIUM_HIGH = "medium high"

# Temperature settings. Half-degree steps are only offered to units that report
# support for it (Props.TEMP_HALF_ENABLED); everything else stays whole-degree.
TARGET_TEMPERATURE_STEP = 1
TARGET_TEMPERATURE_STEP_HALF = 0.5

# Gree HWHP (Hot Water Heat Pump) settings
HWHP_PROP_WATER_TEMP = "WatTmp"  # Current water temperature property key
HWHP_PROP_SET_TEM_INT = "SetTemInt"  # Target temperature (integer part)
HWHP_PROP_SET_TEM_DEC = "SetTemDec"  # Target temperature (decimal part, tenths)
HWHP_TEMP_ENCODING_OFFSET = 100  # Raw temp encoding: actual = raw - offset
HWHP_TEMP_MIN = 40  # Minimum target temperature for hot water (°C)
HWHP_TEMP_MAX = 80  # Maximum target temperature for hot water (°C)
HWHP_PROP_WMOD = "Wmod"  # Water heater mode: 0=heat pump, 2=boost/performance
HWHP_PROP_WSTATE = "Wstate"  # Heating state: 0=keep warm (idle), 1=actively heating
HWHP_PROP_POW_CONSUMP = "powConsump"  # Power consumption (raw device units)
HWHP_WMOD_HEAT_PUMP = 0
HWHP_WMOD_BOOST = 2
HWHP_OPERATION_HEAT_PUMP = "heat_pump"  # Normal heat pump operation
HWHP_OPERATION_BOOST = "performance"  # Boost / turbo operation

# Hot water capacity/availability gauge shown in the EWPE app (the "Hot water
# capacity %" ring). Uses the same +100 raw encoding as temperatures; unlike
# temperature it isn't clamped to 0-100 (a satisfied/overheated tank has been
# observed reporting 120, i.e. 20% - confirmed against the app's own display).
HWHP_PROP_CAPACITY = "Watpercent"

# Two independent on/off schedule windows (labelled "Timer" in the EWPE app).
# Each has an enable flag and a start/end time split into hour + minute props.
HWHP_PROP_SCH1_ENABLE = "Sch1"
HWHP_PROP_WTMR1_START_HR = "Wtmr1StartHr"
HWHP_PROP_WTMR1_START_MIN = "Wtmr1StartMin"
HWHP_PROP_WTMR1_END_HR = "Wtmr1EndHr"
HWHP_PROP_WTMR1_END_MIN = "Wtmr1EndMin"
HWHP_PROP_SCH2_ENABLE = "Sch2"
HWHP_PROP_WTMR2_START_HR = "Wtmr2StartHr"
HWHP_PROP_WTMR2_START_MIN = "Wtmr2StartMin"
HWHP_PROP_WTMR2_END_HR = "Wtmr2EndHr"
HWHP_PROP_WTMR2_END_MIN = "Wtmr2EndMin"

# Two independent Eco mode windows (labelled "Eco" in the EWPE app). Each has
# an enable flag and a start/end time split into hour + minute props, mirroring
# the schedule/"Timer" block above.
HWHP_PROP_ECO1_ENABLE = "ECO1"
HWHP_PROP_ECO1_START_HR = "ECO1StartHr"
HWHP_PROP_ECO1_START_MIN = "ECO1StartMin"
HWHP_PROP_ECO1_END_HR = "ECO1EndHr"
HWHP_PROP_ECO1_END_MIN = "ECO1EndMin"
HWHP_PROP_ECO2_ENABLE = "ECO2"
HWHP_PROP_ECO2_START_HR = "ECO2StartHr"
HWHP_PROP_ECO2_START_MIN = "ECO2StartMin"
HWHP_PROP_ECO2_END_HR = "ECO2EndHr"
HWHP_PROP_ECO2_END_MIN = "ECO2EndMin"

# Energy metering (AC units).
# ElcAll is a cumulative counter in tenths of a kWh; it does not reset daily.
# ElcAllConsumption carries the same value and is not read separately.
PROP_ENERGY_TOTAL = "ElcAll"
ENERGY_SCALE = 0.1

# Compressor frequency in Hz. Reads 0 while the unit is idle and non-zero while
# it is actually running, so it tracks load far more responsively than the
# energy counter, which only moves in whole 0.1 kWh steps.
PROP_COMPRESSOR_FREQ = "CompressorFqy"

# Relative humidity. Already part of the standard Props enum (HUM_SENSOR), so
# it needs no extra request - only an entity to surface it.
PROP_HUMIDITY = "DwatSen"

# Gree Cloud servers
GREE_CLOUD_SERVERS = {
    "Australia": "https://augrih.gree.com",
    "China Mainland": "https://grih.gree.com",
    "East South Asia": "https://hkgrih.gree.com",
    "Europe": "https://eugrih.gree.com",
    "India": "https://ingrih.gree.com",
    "Latin American": 'https://lagrih.gree.com',
    "Middle East": "https://megrih.gree.com",
    "North American": "https://nagrih.gree.com",
    "Russia": "https://rugrih.gree.com",
    "South American": "https://sagrih.gree.com",
}

# Gree MQTT servers (one per region, must match the REST API region)
GREE_MQTT_SERVERS = {
    "Australia": "mqtt-au.gree.com",
    "China Mainland": "mqtt.gree.com",
    "East South Asia": "mqtt-as.gree.com",
    "Europe": "mqtt-eu.gree.com",
    "India": "mqtt-in.gree.com",
    "Latin American": "mqtt-la.gree.com",
    "Middle East": "mqtt-me.gree.com",
    "North American": "mqtt-na.gree.com",
    "Russia": "mqtt-ru.gree.com",
    "South American": "mqtt-sa.gree.com",
}
