import socket
import select


class UdpProxy(object):
    def __init__(self, net_local_front_addr, net_local_back_addr,
            net_target_addr, socket_timeout=0, verbose=False):
        super(UdpProxy, self).__init__()
        self.sock_front = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_front.bind(net_local_front_addr)
        self.sock_back = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_back.bind(net_local_back_addr)
        self.net_target_addr = net_target_addr
        self.socket_timeout = socket_timeout
        self.verbose = verbose

    def run(self):
        net_target_front_addr = None
        if self.verbose:
            print("proxy start")
        while True:
            rd_list, _, _ = select.select([self.sock_front, self.sock_back],
                    [], [], self.socket_timeout)
            if self.sock_front in rd_list:
                buf, net_target_front_addr = self.sock_front.recvfrom(65536)
                if self.verbose:
                    print("F recv %dbytes from %s" % (len(buf), str(net_target_front_addr)))
                    print("B send %dbytes to   %s" % (len(buf), str(self.net_target_addr)))
                self.sock_back.sendto(buf, self.net_target_addr)
            if self.sock_back in rd_list and net_target_front_addr is not None:
                buf, addr = self.sock_back.recvfrom(65536)
                if self.verbose:
                    print("B recv %dbytes from %s" % (len(buf), str(addr)))
                    print("F send %dbytes to   %s" % (len(buf), str(net_target_front_addr)))
                self.sock_front.sendto(buf, net_target_front_addr)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Udp proxy: \
external_access --> front_port --> back_port --> target_addr')
    parser.add_argument('front_port', type=int, help='front-end port')
    parser.add_argument('back_port', type=int, help='back-end port')
    parser.add_argument('target_ip', type=str, help='target ip address')
    parser.add_argument('target_port', type=int, help='target port')
    parser.add_argument('--front_ip', type=str, default='0.0.0.0',
            help='front-end ip address')
    parser.add_argument('--back_ip', type=str, default='0.0.0.0',
            help='back-end ip address')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='Prints the number of bytes received')
    args = parser.parse_args()

    net_local_front_addr = (args.front_ip, args.front_port)
    net_local_back_addr  = (args.back_ip, args.back_port)
    net_target_addr      = (args.target_ip, args.target_port)
    socket_timeout       = 1
    proxy = UdpProxy(net_local_front_addr, net_local_back_addr, net_target_addr,
            socket_timeout=socket_timeout, verbose=args.verbose)
    proxy.run()