import sys
import signal
import asyncio
import configparser

from pathlib import Path
from hypercorn.config import Config
from hypercorn.asyncio import serve

# append local module directory to path
sys.path.append(str(Path(__file__).parent / "modules"))

from server import server, close_sinks

DEFAULT_CONFIG = {
    "Server" : {
        "Bind" : "127.0.0.1",
        "Port" : "10101"
    },
    "Camera" : {
        "DeviceId" : "0",
        "OnDemand" : "yes"
    }
}

shutdown_event = asyncio.Event()

async def terminate():
    shutdown_event.set()
    await close_sinks()

async def main():

    app_config = configparser.ConfigParser()
    app_config.read_dict(DEFAULT_CONFIG)
    app_config.read(str(Path(__file__).parent / "webcam.conf"))
    
    server.config["deviceid"] = app_config.getint("Camera", "DeviceId")
    server.config["ondemand"] = app_config.getboolean("Camera", "OnDemand")
   
    hc_config = Config()
    host = app_config.get("Server", "Bind")
    if (len(host) > 1) and (host[0] == "/"):
        hc_config.bind = [ f"unix:{host}" ]
    else:
        port = app_config.getint("Server", "Port")
        hc_config.bind = [ f"{host}:{port}" ]

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.ensure_future(terminate()))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(terminate()))
    await serve(server, hc_config, shutdown_trigger=shutdown_event.wait)

if __name__ == "__main__":
    asyncio.run(main())
