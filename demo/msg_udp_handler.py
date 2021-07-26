import socket
import struct
import select
import msg_pb2


FRAME_HEAD_FORMAT = 'IIII'
FRAME_HEAD_BYTES  = 4*4
MSG_CMD_FORMAT    = 'H'
MSG_CMD_BYTES     = 2


def MSG_GET_CMD_RESPONS(cmd):
    return cmd | 0x8000


def printFrameHead(frame_head):
    print(f"frame_len: {frame_head['frame_len']}, "
          f"frame_idx: {frame_head['frame_idx']}, "
          f"frame_total: {frame_head['frame_total']}, "
          f"msg_id: {frame_head['msg_id']}")


def parseMsgFrameHead(buf, idx_start=0):
    idx_end = idx_start + 16
    values = struct.unpack(FRAME_HEAD_FORMAT, buf[idx_start:idx_end])
    frame_head = {
        'frame_len'  : values[0],
        'frame_idx'  : values[1],
        'frame_total': values[2],
        'msg_id'     : values[3]
    }
    return frame_head, idx_end


class MsgUdpHandler(object):
    def __init__(self,
            net_local_addr,
            net_target_addr,
            socket_timeout=0,
            frame_max_bytes=65000,
            payload_max_bytes=1024*1024*16):
        super(MsgUdpHandler, self).__init__()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(net_local_addr)
        self.sock = sock
        self.is_specific_target = net_target_addr != None
        self.net_target_addr = net_target_addr
        self.socket_timeout = socket_timeout
        self.frame_max_bytes = frame_max_bytes
        self.frame_payload_max_bytes = frame_max_bytes - FRAME_HEAD_BYTES
        self.payload_max_bytes = payload_max_bytes
        self.msg_id = 0

    def sendData(self, data):
        self.sock.sendto(data, self.net_target_addr)

    def sendMsg(self, cmd, proto_obj=None):
        # 负载序列化
        payload = b'' if proto_obj is None else proto_obj.SerializeToString()
        payload = struct.pack(MSG_CMD_FORMAT, cmd) + payload
        # 计算帧数
        frame_total = self.calcMsgFrameNum(len(payload))
        # 分段发送消息
        total_bytes     = len(payload)  # 负载总字节数
        send_bytes      = 0             # 已发送负载的字节数
        for i in range(frame_total):
            # 负载剩余的字节数
            remain_bytes = total_bytes - send_bytes
            # 当前帧可发送负载的字节数
            frame_payload_bytes = min(remain_bytes, self.frame_payload_max_bytes)
            # 发送一帧数据
            frame_head = struct.pack('IIII',
                    FRAME_HEAD_BYTES+frame_payload_bytes,  # 当前帧长度
                    i+1,          # 帧序号
                    frame_total,  # 帧总数
                    self.msg_id,  # 消息ID
                    )
            frame = frame_head + payload[send_bytes:send_bytes+frame_payload_bytes]
            self.sendData(frame)
            send_bytes += frame_payload_bytes
        self.msg_id += 1

    def sendRspMsg(self, cmd, proto_obj):
        cmd = MSG_GET_CMD_RESPONS(cmd)
        self.sendMsg(cmd, proto_obj)

    def sendSetPropMsg(self, proto_obj):
        self.sendMsg(msg_pb2.MSG_CMD_SET_PROPERTY, proto_obj)

    def sendGetPropMsg(self, prop_id, **args):
        req = msg_pb2.ReqGetProp()
        req.prop_id = prop_id
        for k in args:
            v = args[k]
            if isinstance(v, dict):
                proto_v = getattr(req, k)
                for _k in v:
                    setattr(proto_v, _k, v[_k])
            else:
                setattr(proto_v, k, v)
        self.sendMsg(msg_pb2.MSG_CMD_GET_PROPERTY, req)

    def recvMsg(self, timeout=None):
        timeout = self.socket_timeout if timeout is None else timeout
        last_frame_head = None
        payload = b''
        is_first = True

        while True:
            # print("INFO: waitting to recv...")
            rd_list, _, _ = select.select([self.sock], [], [], timeout)
            if self.sock not in rd_list:
                # print(f"WARN: recv timeout({timeout}s)")
                return None
            buf, addr_client = self.sock.recvfrom(65536)
            if not self.is_specific_target:
                self.net_target_addr = addr_client
            # print(f"INFO: recv bytes: {len(buf)}")
            # 这里省去 buf 的检查
            frame_head, idx_start = parseMsgFrameHead(buf)
            # printFrameHead(frame_head)

            if is_first:
                is_first = False
                if frame_head['frame_idx'] != 1:
                    print("ERROR: first frame idx not 1")
                    return
                if frame_head['frame_total'] == 0:
                    print("ERROR: frame_total wes 0")
                    return
            else:
                if frame_head['msg_id'] != last_frame_head['msg_id'] or \
                    frame_head['frame_total'] != last_frame_head['frame_total'] or \
                    frame_head['frame_idx'] != last_frame_head['frame_idx'] + 1:
                    print("ERROR: frame head wes mismatch last frame head."
                        f"msg_id({frame_head['msg_id']}, {last_frame_head['msg_id']}) "
                        f"frame_total({frame_head['frame_total']}, {last_frame_head['frame_total']}) "
                        f"frame_idx({frame_head['frame_idx']}, {last_frame_head['frame_idx']})")
                    return
            last_frame_head = frame_head
            payload += buf[idx_start:]
            if len(payload) > self.payload_max_bytes:
                print(f"ERROR: payload({len(payload)}bytes) too long.")
            # 判断消息接收完毕
            if frame_head['frame_idx'] == frame_head['frame_total']:
                break
        msg = {
            'last_frame_head': last_frame_head,
            'payload': payload
        }
        return msg

    def calcMsgFrameNum(self, payload_bytes):
        frame_full_num = payload_bytes // self.frame_payload_max_bytes
        frame_remain_bytes = payload_bytes % self.frame_payload_max_bytes
        frame_total = frame_full_num if frame_remain_bytes == 0 else \
                frame_full_num + 1
        return frame_total

    def clearSocketRecvBuf(self, timeout=0):
        while True:
            rd_list, _, _ = select.select([self.sock], [], [], timeout)
            if self.sock not in rd_list:
                return None
            self.sock.recvfrom(65536)