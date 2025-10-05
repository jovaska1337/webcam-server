## Simple webcam streaming server

This is a simple server for creating an MJPEG stream from a webcam through V4L.
It is intended to be used with OctoPrint to provide webcam footage of a 3D printer.

Currently, only the YUYV format is supported as that's what my webcam uses.

The server supports streaming through `/stream.mjpg` and taking snapshots through `/snapshot.jpeg`.
Everything is implemented on top of asyncio and the server is implemented using Quart to make the
whole program asynchronous.

The webcam can run in "continuous" or "on demand" mode. In "continuous" mode, the webcam IO task is
kept running all the time and frames are discarded when there are no sinks. In "on demand" mode,
the webcam IO task is started when there's at least one sink (active request) and stopped when
there are no sinks. Starting and stopping the IO task takes ~1 second or so.

The server can listen on a TCP/IP socket or UNIX socket, check `webcam.conf` for configuration
options.
