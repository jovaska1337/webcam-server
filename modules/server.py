import time

from quart import Quart, Response
from webcam import Webcam
from imgutil import JPEGFormatter

server = Quart("webcam")
camera = None

async def multipart_stream_generator(stream, boundary):
    try:
        async for frame in stream:
            data = bytearray()
            data += b"--"
            data += boundary 
            data += b"\r\nContent-Type: image/jpeg\r\n\r\n"
            data += frame
            data += b"\r\n"
            yield data
    finally:
        await stream.close()

@server.route("/")
def root():
    html = """
<!DOCTYPE html>
<head>
    <title>Index</title>
</head>
<body>
    <p>This is a small webcam streaming server.</p>
    <ul>
        <li><a href="/stream.mjpg">Webcam stream</a></li>
        <li><a href="/snapshot.jpeg">Webcam snapshot</a></li>
    </ul>
</body>
"""
    return Response(html, mimetype="text/html")

@server.route("/stream.mjpg")
async def stream():
    global camera
    boundary = f"webcam_{str(int(time.time()))}"
    stream = await camera.stream()
    try:
        resp = Response(
            multipart_stream_generator(stream, boundary.encode("ascii")),
            mimetype=f"multipart/x-mixed-replace; boundary={boundary}"
        )
        resp.timeout = None # allow indefinite stream
    except Exception as e:
        stream.close()
        raise e
    return resp

@server.route("/snapshot.jpeg")
async def snapshot():
    global camera
    return Response(
        await camera.snapshot(),
        mimetype="image/jpeg"
    )

@server.after_serving
async def shutdown():
    global camera
    await camera.__aexit__()

async def close_sinks():
    global camera
    await camera.close_sinks()

@server.before_serving
async def startup():
    global camera
    camera = Webcam(
        server.config["deviceid"],
        JPEGFormatter(),
        server.config["ondemand"]
    )
    await camera.__aenter__()
