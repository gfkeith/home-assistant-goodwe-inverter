"""Simple test script to check inverter UDP protocol communication"""

import asyncio
import goodwe
from goodwe.const import GOODWE_UDP_PORT, GOODWE_TCP_PORT
from goodwe.exceptions import InverterError
import logging
import sys


logging.basicConfig(
    format="%(asctime)-15s %(funcName)s(%(lineno)d) - %(levelname)s: %(message)s",
    stream=sys.stderr,
    level=getattr(logging, "DEBUG", None),
)

# Set the appropriate IP address
IP_ADDRESS = ""

FAMILY = None  # One of ET, ES, DT or None to detect inverter family automatically
COMM_ADDR = None  # Usually 0xf7 for ET/ES or 0x7f for DT, or None for default value
TIMEOUT = 2
RETRIES = 10


async def connect_inverter():
    """Try UDP first (port 8899), fall back to TCP (port 502) like the HA integration does."""
    port = GOODWE_UDP_PORT
    try:
        return await goodwe.connect(host=IP_ADDRESS, port=port, family=FAMILY, timeout=TIMEOUT, retries=RETRIES)
    except InverterError as udp_err:
        print(f"UDP port {port} failed ({udp_err}), trying TCP port {GOODWE_TCP_PORT}...", file=sys.stderr)
        port = GOODWE_TCP_PORT
        return await goodwe.connect(host=IP_ADDRESS, port=port, family=FAMILY, timeout=TIMEOUT, retries=RETRIES)


inverter = asyncio.run(connect_inverter())
print(
    f"Identified inverter:\n"
    f"\tModel:    {inverter.model_name}\n"
    f"\tSerialNr: {inverter.serial_number}\n"
    f"\tFirmware: {inverter.firmware}"
)

response = asyncio.run(inverter.read_runtime_data())

print("\nSensors values:")
for sensor in inverter.sensors():
    if sensor.id_ in response:
        print(
            f"\t{sensor.id_:30}:\t{sensor.name} = {response[sensor.id_]} {sensor.unit}"
        )
