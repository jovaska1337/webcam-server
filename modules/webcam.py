import asyncio

from collections import deque
from linuxpy.video.device import BufferType, Device

class FrameStream:
    def __init__(self, webcam):
        self.webcam = webcam
        self.frames = deque([], 64)
        self.semphr = asyncio.Semaphore(0)
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *info):
        await self.close()

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self.semphr.acquire()
        if len(self.frames) < 1: 
            await self.webcam.__remove(self)
            raise StopAsyncIteration
        else:
            return self.frames.popleft()

    def _Webcam__feed(self, frame):
        self.frames.append(frame)
        self.semphr.release()
        return self

    async def close(self):
        await self.webcam.__remove(self)
        self.__close()
        return self

    def __close(self):
        self.frames.clear()
        self.semphr.release()

    def _Webcam__close(self):
        self.__close()

class FrameSnapshot:
    def __init__(self, webcam):
        self.webcam = webcam
        self.frame  = None
        self.event  = asyncio.Event() 

    async def __aenter__(self):
        return self

    async def __aexit__(self, *info):
        await self.close()

    async def get(self):
        await self.event.wait()
        return self.frame

    def _Webcam__feed(self, frame):
        self.frame = frame
        self.event.set()

    async def close(self):
        self.__close()
        await self.webcam.__remove(self)
        return self

    def __close(self):
        self.event.set()

    def _Webcam__close(self):
        self.__close()

class FrameFormatter:
    def __init__(self):
        self.width   = None
        self.height  = None
        self.pixfmt  = None
        self.bufsize = None

    def setup_format(self, fmt):
        self.width   = fmt.width
        self.height  = fmt.height
        self.pixfmt  = fmt.pixel_format
        self.bufsize = fmt.size

    def process_frame(self, frame):
        # user implements to receive what they want
        # from the stream / snapshot functions
        raise NotImplementedError("Virtual method")

class Webcam:
    def __init__(self, dev, fmt, ondemand = True):
        self.device     = Device.from_id(dev)
        self.fmt        = fmt
        self.reader     = None
        self.task       = None
        self.task_wait  = asyncio.Event()
        self.task_begin = asyncio.Event()
        self.task_lock  = asyncio.Lock()
        self.sinks      = []
        self.sinks_lock = asyncio.Lock()
        self.ondemand   = ondemand

    async def __aenter__(self):
        if not self.ondemand:
            await self.__begin(True)
        return self

    async def __aexit__(self, *info):
        await self.close()

    async def close(self):
        await self.__end(True)
        await self.__close()

    async def close_sinks(self):
        async with self.sinks_lock:
            for sink in self.sinks:
                sink.__close()
            self.sinks.clear()

    async def __close(self):
        self.device.close()
        await self.close_sinks()

    async def stream(self):
        stream = FrameStream(self)
        async with self.sinks_lock:
            self.sinks.append(stream)
        await self.__begin()
        return stream

    async def snapshot(self):
        snapshot = FrameSnapshot(self)
        try:
            async with self.sinks_lock:
                self.sinks.append(snapshot)
            await self.__begin()
            frame = await snapshot.get()
        finally:
            await snapshot.close()
        return frame

    async def __task(self):
        try:
            self.task_wait.set()
            await self.task_begin.wait()
            with self.device as cam:
                fmt = cam.get_format(BufferType.VIDEO_CAPTURE)
                self.fmt.setup_format(fmt)
                async for frame in cam:
                    async with self.sinks_lock:
                        if len(self.sinks) > 0:
                            tmp = self.fmt.process_frame(frame)
                            for sink in self.sinks:
                                    sink.__feed(tmp)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.__close()
            raise e

    async def __begin(self, force = False):
        spawned = False
        async with self.task_lock:
            if self.task == None:
                if force or (self.ondemand and len(self.sinks) > 0):
                    self.task_wait.clear()
                    self.task = asyncio.create_task(self.__task())
                    await self.task_wait.wait()
                    spawned = True
        if spawned:
            self.task_begin.set()
        return self

    async def __end(self, force = False):
        async with self.task_lock:
            if self.task != None:
                if force or (self.ondemand and (len(self.sinks) < 1)):
                    await self.task_wait.wait()
                    self.task_begin.set()
                    self.task.cancel()
                    await self.task
                    self.task_begin.clear()
                    try:
                        self.task.exception()
                    finally:
                        self.task = None
        return self

    async def __remove(self, stream):
        async with self.sinks_lock:
            if stream in self.sinks:
                self.sinks.remove(stream)
        await self.__end()
    
    async def _FrameStream__remove(self, stream):
        await self.__remove(stream)
    
    async def _FrameSnapshot__remove(self, stream):
        await self.__remove(stream)
