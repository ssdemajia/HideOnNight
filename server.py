# coding=utf-8
from EventLoop import EventLoop
from Ping import PingServer


def main():
    loop = EventLoop()
    # test a ping server
    servers = [PingServer('www.baidu.com', '0.0.0.0', 8899)]

    for server in servers:
        server.addToLoop(loop)

    loop.run()


if __name__ == '__main__':
    main()
