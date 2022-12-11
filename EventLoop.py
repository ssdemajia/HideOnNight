# coding=utf-8
import traceback
from collections import defaultdict
import logging
import select
import const
import time


class PollResult(object):
    def __init__(self):
        self.fd = -1
        self.pollType = const.PollType.POLL_NULL


class SelectLoop(object):
    def __init__(self):
        self.readList = set()
        self.writeList = set()
        self.errorList = set()

    def addPollEvent(self, fd, pollType):
        if pollType & const.PollType.POLL_READ:
            self.readList.add(fd)
        if pollType & const.PollType.POLL_WRITE:
            self.writeList.add(fd)
        if pollType & const.PollType.POLL_ERROR:
            self.errorList.add(fd)

    def deletePollEvent(self, fd):
        if fd in self.readList:
            self.readList.remove(fd)
        if fd in self.writeList:
            self.writeList.remove(fd)
        if fd in self.errorList:
            self.errorList.remove(fd)

    def modifyPollEvent(self, fd, pollType):
        self.deletePollEvent(fd)
        self.addPollEvent(fd, pollType)

    def poll(self, timeout):
        if len(self.readList) == 0 and len(self.writeList) == 0 and len(self.errorList) == 0:
            return []
        readList, writeLists, errorList = select.select(self.readList, self.writeList, self.errorList, timeout)
        result = defaultdict(PollResult)
        for fdList, pollType in ((readList, const.PollType.POLL_READ),
                                (writeLists, const.PollType.POLL_WRITE),
                                (errorList, const.PollType.POLL_ERROR)):
            for fd in fdList:
                result[fd].fd = fd
                result[fd].pollType |= pollType
        return result.values()

    def close(self):
        return

class Timer(object):
    def __init__(self, tickTime, callback):
        self.tickTime = tickTime
        self.callback = callback
        self.lastTickTime = 0

    def __call__(self, *args, **kwargs):
        self.lastTickTime = time.time()
        self.callback()

    def canTick(self):
        now = time.time()
        return now - self.lastTickTime >= self.tickTime


class EventLoop(object):
    def __init__(self):
        self._impl = SelectLoop()

        self._fdCallbacks = {}
        self._timerCallbacks = []
        self._isStop = False

    def add(self, socket, pollType, callback):
        fd = socket.fileno()
        self._fdCallbacks[fd] = (socket, callback)
        self._impl.addPollEvent(fd, pollType)

    def remove(self, socket):
        fd = socket.fileno()
        del self._fdCallbacks[fd]
        self._impl.deletePollEvent(fd)

    def addTimer(self, timer):
        # Timer(tickTime, callback)
        self._timerCallbacks.append(timer)

    def removeTimer(self, timer):
        self._timerCallbacks.remove(timer)

    def modify(self, socket, pollType):
        self._impl.modifyPollEvent(socket.fileno(), pollType)

    def stop(self):
        self._isStop = True

    def run(self):
        print('eventloop start')
        while not self._isStop:
            events = []
            try:
                events = self._impl.poll(const.TIME_TICK)
            except Exception as e:
                traceback.print_exc()
                continue

            for event in events:
                fd = event.fd
                socket, callback = self._fdCallbacks.get(fd)
                if callback:
                    callback.handleEvent(socket, fd, event)

            for callback in self._timerCallbacks:
                if callback.canTick():
                    callback()

    def close(self):
        self._impl.close()
