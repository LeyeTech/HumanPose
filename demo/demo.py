#coding: utf-8

import os
import cv2
import time
import fire
import numpy as np
import struct
import threading
import queue
import imagesize
from typing import Union
import os.path as osp
from queue import Queue
from loguru import logger

import msg_pb2
from dev_agent import DevAgent
from msg_udp_handler import MsgUdpHandler, MSG_GET_CMD_RESPONS
from vis import drawBox, drawKps, drawActions2
from fps_helper import FPSHelper


class BaseThread(threading.Thread):
    def __init__(self):
        super(BaseThread, self).__init__()
        self.is_running = False

    def isRunning(self):
        return self.is_running

    def stop(self):
        logger.debug("stop")
        self.is_running = False

    def _run(self):
        pass

    def run(self) -> None:
        self.is_running = True
        self._run()
        self.is_running = False

    def putQueue(self, q, d, timeout=1):
        while self.is_running:
            try:
                q.put(d, timeout=timeout)
                return True
            except queue.Full:
                continue
        return False

    def popQueue(self, q, timeout=1):
        while self.is_running:
            try:
                d = q.get(timeout=timeout)
                return d
            except queue.Empty:
                continue
        return None


class BaseReader(BaseThread):
    def __init__(self, img_queue_size):
        super(BaseReader, self).__init__()
        self.img_queue_size = img_queue_size
        self.img_queue = queue.Queue(img_queue_size)
        self.img_put_idx = 0

    def getImgQueue(self):
        return self.img_queue

    def clearImgQueue(self):
        self.getLastFrame()

    def getFrame(self, is_try=False, timeout=None):
        if not is_try:
            return self.img_queue.get(timeout=timeout)
        if self.img_queue.empty():
            return None
        return self.img_queue.get()

    def getLastFrame(self):
        frame = None
        while not self.img_queue.empty():
            try:
                frame = self.img_queue.get_nowait()
            except queue.Empty:
                pass
        return frame

    def _putFrame(self, frame):
        if self.putQueue(self.img_queue, (self.img_put_idx, frame)):
            self.img_put_idx += 1
            return True
        return False

    def stop(self):
        super(BaseReader, self).stop()
        self.clearImgQueue()



class VideoReader(BaseReader):
    def __init__(self,
            source=0,
            img_queue_size=2,
            cam_size=(640,480),
            cam_fps:int=30,
            cam_use_mjpg=True,
            cam_loop_open:bool=True,
            img_scale=1.0,
            ):
        super(VideoReader, self).__init__(img_queue_size)
        self.source = source
        self.cam_size = cam_size
        self.cam_fps = cam_fps
        self.cam_use_mjpg = cam_use_mjpg
        self.cam_loop_open = cam_loop_open
        self.img_scale = img_scale
        self.source_is_camera = isinstance(source, int) or source.startswith('/dev/')
        assert self.cam_fps > 0
        assert self.img_scale > 0
        self.is_opened = False
        self.cap = self.openSource()

    def openSource(self):
        self.is_opened = False
        cap = cv2.VideoCapture(self.source)
        if self.source_is_camera:
            if not self.cam_loop_open:
                assert cap.isOpened()
            if not cap.isOpened():
                logger.error(f"Open video '{self.source}' faild")
                cap.release()
                return None
        else:
            assert cap.isOpened()
        logger.info(f"Open video '{self.source}' success")
        if self.source_is_camera:
            if self.cam_use_mjpg:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_size[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_size[1])
            cap.set(cv2.CAP_PROP_FPS, self.cam_fps)
        self.is_opened = True
        return cap

    def isOpened(self):
        return self.is_opened

    def _run(self):
        while self.isRunning():
            # 判断输入源是否可用
            if self.cap is None:
                if not self.source_is_camera or not self.cam_loop_open:
                    break
                self.cap = self.openSource()
                if self.cap is None:
                    time.sleep(1)
                    continue
            # 获取一帧
            ts = time.time()
            ret_val, img = self.cap.read()
            if not ret_val:
                if self.source_is_camera:
                    logger.error(f"Read camera{self.source} failed!")
                    self.cap.release()
                    self.cap = None
                    if not self.cam_loop_open:
                        break
                    time.sleep(1)
                    continue
                else:
                    logger.info(f"Read video '{self.source}' finish")
                    break
            # 缩放图片
            if self.img_scale != 1.:
                w = round(img.shape[1] * self.img_scale)
                h = round(img.shape[0] * self.img_scale)
                img = cv2.resize(img, (w, h))
            # 如果输入源是摄像头，图片队列满时，弹出最后一帧
            if self.source_is_camera and self.img_queue.full():
                try:
                    self.img_queue.get_nowait()
                except queue.Empty:
                    pass
            # 存入队列
            if not self._putFrame(img):
                break
            te = time.time()
            # 睡眠
            if not self.source_is_camera:
                time.sleep(max(0, 1./self.cam_fps-(te - ts)))
        self.img_queue.put(None)


class ImgsReader(BaseReader):
    def __init__(self, img_fpaths, img_queue_size=2):
        super(ImgsReader, self).__init__(img_queue_size)
        assert img_fpaths
        self.img_fpaths = img_fpaths
        self.img_idx = 0

    def _run(self):
        while self.isRunning() and self.img_idx < len(self.img_fpaths):
            # 读取图片原始数据
            img_fpath = self.img_fpaths[self.img_idx]
            logger.debug(f"read {img_fpath}")
            self.img_idx += 1
            with open(img_fpath, 'rb') as f:
                img = f.read()
            # 存入队列
            if not self._putFrame(img):
                break
        self.img_queue.put(None)


class ImgSendService(BaseThread):
    def __init__(self, msg_handler:MsgUdpHandler, img_queue:Queue):
        super(ImgSendService, self).__init__()
        self.msg_handler = msg_handler
        self.img_queue   = img_queue

    def _run(self):
        while self.isRunning():
            try:
                img_idx, img = self.img_queue.get(timeout=1)
            except queue.Empty:
                continue
            self.sendImg(img_idx, img)

    def sendImg(self, idx, img):
        if isinstance(img, np.ndarray):
            _, img = cv2.imencode('.jpg', img)
            img = img.tobytes()
        req = msg_pb2.ReqMediaStream()
        req.type = msg_pb2.MEDIA_IMAGE_STREAM
        req.img.idx = idx
        req.img.pix_fmt = 1
        req.img.data = img
        self.msg_handler.sendMsg(msg_pb2.MSG_CMD_MEDIA_SOURCE_STREAM, req)



class StreamRecvService(BaseThread):
    def __init__(self, msg_handler:MsgUdpHandler, img_queue:Queue,
            pose_queue:Queue):
        super(StreamRecvService, self).__init__()
        self.msg_handler = msg_handler
        self.img_queue   = img_queue
        self.pose_queue  = pose_queue

    def _run(self):
        while self.isRunning():
            msg = self.msg_handler.recvMsg(timeout=1)
            if msg is None:
                continue
            self.handleMsg(msg)

    def handleMsg(self, msg):
        cmd = struct.unpack('H', msg['payload'][:2])[0]
        if cmd == msg_pb2.MSG_CMD_STREAM_CAM_IMG:
            self.handleCamImgMsg(msg)
        elif cmd == msg_pb2.MSG_CMD_STREAM_HUMAN_POSE:
            self.handleHumanPoseMsg(msg)
        elif cmd == MSG_GET_CMD_RESPONS(msg_pb2.MSG_CMD_MEDIA_SOURCE_STREAM):
            self.handleRspSourceStreamImg(msg)
        else:
            print("WARN: Unknown cmd: 0x%04x" % cmd)

    def handleCamImgMsg(self, msg):
        req = msg_pb2.ReqCamImgStream()
        req.ParseFromString(msg['payload'][2:])
        img = req.cam_img
        if self.img_queue is None:
            return
        if self.img_queue.full():
            self.img_queue.get_nowait()
        self.img_queue.put((img.idx, img.data))

    def handleHumanPoseMsg(self, msg):
        req = msg_pb2.ReqHumanPoseStream()
        req.ParseFromString(msg['payload'][2:])
        # print(f"img idx: {req.img_idx}")
        boxes = [[b.xmin, b.ymin, b.xmax, b.ymax, b.score] for b in req.boxes]
        pose = {'boxes': boxes}
        if len(req.pose2ds) > 0:
            kps = [[p.x, p.y, p.v] for p in req.pose2ds[0].point]
            # 添加root节点
            kps.append([(kps[6][0]+kps[9][0])//2, (kps[6][1]+kps[9][1])//2,
                    min(kps[6][2], kps[9][2])])
            pose['kps'] = kps
        # 调整kps3d坐标系
        if len(req.pose3ds) > 0:
            # kps3d = [[p.x, p.y, p.z, p.v] for p in req.pose3ds[0].point]
            kps3d = [[-p.x, -p.z, -p.y, p.v] for p in req.pose3ds[0].point]
            pose['kps3d'] = kps3d

        if len(req.hand_dirs) > 0:
            left_dir = [req.hand_dirs[0].left & (1 << x) for x in range(6)]
            right_dir = [req.hand_dirs[0].right & (1 << x) for x in range(6)]
            pose['hand_dir'] = (left_dir, right_dir)

        if self.pose_queue.full():
            self.pose_queue.get_nowait()
        self.pose_queue.put((req.img_idx, pose))

    def handleRspSourceStreamImg(self, msg):
        rsp = msg_pb2.RspMediaStream()
        rsp.ParseFromString(msg['payload'][2:])
        if rsp.status != msg_pb2.MSG_STATUS_OK:
            logger.warning(str(rsp))


class HumanPoseDisplayer(object):
    def __init__(self,
            title:str,
            img_queue:Queue,
            pose_queue:Queue,
            is_show_img:bool,
            cam_img_w:int,
            cam_img_h:int,
            kps_thr:float,
            show_fps:float=None,
            is_draw_fps:bool=True,
            idx_max_diff=3):
        super(HumanPoseDisplayer, self).__init__()
        self.title = title
        self.img_queue = img_queue
        self.pose_queue = pose_queue
        self.is_show_img = is_show_img
        self.cam_img_w = cam_img_w
        self.cam_img_h = cam_img_h
        self.kps_thr = kps_thr
        self.show_fps = show_fps
        self.is_draw_fps = is_draw_fps
        self.idx_max_diff = idx_max_diff
        self.last_img = None
        self.last_pose = None
        self.fps_helper_img = FPSHelper()

    def show(self):
        is_first_frame = True
        while True:
            ts = time.time()
            # 获取img
            try:
                img_idx, img_raw = self.img_queue.get(timeout=1)
            except queue.Empty:
                if not is_first_frame:
                    key = cv2.waitKey(1)
                    if key in [ord('q'), ord('Q'), 27]:
                        break
                continue
            self.fps_helper_img.update()
            # 解码img
            img = None
            if self.is_show_img:
                if isinstance(img_raw, np.ndarray):
                    img = img_raw
                else:
                    img = self.decodeImg(img_raw)
            if img is None:
                img = np.zeros((self.cam_img_h, self.cam_img_w, 3), np.uint8)
            self.last_img = (img_idx, img)
            # 获取pose
            try:
                self.last_pose = self.pose_queue.get(timeout=1)
            except queue.Empty:
                continue
            # 绘制
            if self.last_pose is None:
                continue
            img_idx, img = self.last_img
            pose_idx, pose = self.last_pose
            if abs(img_idx - pose_idx) < self.idx_max_diff:
                self.drawPose(img, pose)
            if self.is_draw_fps:
                self.drawFps(img, self.fps_helper_img.fps)
            # 显示
            is_first_frame = False
            cv2.imshow(self.title, img)
            # 睡眠
            te = time.time()
            wait_time = 1
            if self.show_fps is not None:
                wait_time = 0 if self.show_fps == 0 else \
                        round(max(0, 1./self.show_fps-(te - ts)) * 1000)
            key = cv2.waitKey(wait_time)
            if key in [ord('q'), ord('Q'), 27]:
                break


    def decodeImg(self, img_str):
        t1 = time.time()
        img_data = np.frombuffer(img_str, dtype=np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        t2 = time.time()
        # print("img decode time: %.1fms" % ((t2-t1)*1000))
        if img is None:
            print("ERROR: img decode failed!\n");
            return
        return img


    def drawPose(self, img, pose:dict):
        if img is None or pose is None:
            return
        if 'boxes' in pose:
            for b in pose['boxes']:
                drawBox(img, b, b[-1], thickness=2, text_y_offset=38,
                        text_color=(30,30,30), text_size=1.5,
                        text_thickness=3)
        if 'kps' in pose:
            drawKps(img, pose['kps'], thr=self.kps_thr)
        if 'hand_dir' in pose:
            left_dir, right_dir = pose['hand_dir']
            drawActions2(img, pose['boxes'][0], left_dir, (200, 0, 0),
                    coord_offset=-20, font_size=1.2, thickness=10)
            drawActions2(img, pose['boxes'][0], right_dir, (0, 200, 0),
                    coord_offset=20, font_size=1.2, thickness=10)


    def drawFps(self, img, fps:float, x_offset=10, y_offset=30, font_size=1,
            background_color=(0, 0, 0), background_thickness=3,
            color=(0, 250, 250), thickness=2):
        # 绘制FPS背景(实现FPS描边)
        cv2.putText(img, "%.1f" % fps, (x_offset, y_offset),
                cv2.FONT_HERSHEY_COMPLEX, font_size, background_color,
                background_thickness)
        # 绘制FPS前景
        cv2.putText(img, "%.1f" % fps, (x_offset, y_offset),
                cv2.FONT_HERSHEY_COMPLEX, font_size, color, thickness)
        return img


class MediaSourceService(BaseThread):
    def __init__(self,
            img_read_queue:Queue,
            img_send_queue:Queue,
            img_show_queue:Queue,
            pose_recv_queue:Queue,
            pose_show_queue:Queue,
            ):
        super(MediaSourceService, self).__init__()
        self.img_read_queue = img_read_queue
        self.img_send_queue = img_send_queue
        self.img_show_queue = img_show_queue
        self.pose_recv_queue = pose_recv_queue
        self.pose_show_queue = pose_show_queue

    def _run(self):
        last_frame = None
        # Loop
        while self.isRunning():
            # 从读取队列获取一帧
            frame = self.popQueue(self.img_read_queue)
            if frame is None and last_frame is None:
                break
            # 存入发送队列
            if frame is not None:
                if not self.putQueue(self.img_send_queue, frame):
                    break
            # 将上一帧存入显示队列
            if last_frame is not None:
                if not self.putQueue(self.img_show_queue, last_frame):
                    break
            # 获取接收到的pose
            pose = self.popQueue(self.pose_recv_queue,
                    timeout=1 if last_frame is not None else 0.01)
            if pose is not None:
                self.pose_show_queue.put(pose)
            last_frame = frame


def main(
    source                 :Union[str, int] = '',
    net_local_ip           :str             = '0.0.0.0',
    net_local_port         :int             = 30000,
    net_local_stream_port  :int             = 30001,
    net_target_ip          :str             = '192.168.181.2',
    net_target_port        :int             = 30000,
    net_target_stream_port :int             = 30001,
    window_title           :str             = 'Human Pose',
    kps_thr                :float           = 0.6,
    cam_idx                :float           = 0,
    cam_fps                :int             = 30,
    cam_img_w              :int             = 1280,
    cam_img_h              :int             = 720,
    show_fps               :bool            = None,
    is_draw_fps            :bool            = None,
    is_show_img            :bool            = True,
    ):
    '''
    Demo

    Args:
    source: 输入源
        如果输入源（source）为空或None，使用设备摄像头;
        如果输入源为数字，使用主机摄像头;
        如果输入源为.mp4视频，读取.mp4视频;
        如果输入源为.jpg图片，读取.jpg图片;
        如果输入源为目录，读取该目录下所有的.jpg图片。

        ``注意：输入源图片宽和高必须是16的倍数，且尺寸小于1920x1080``
    net_local_ip: 本地监听IP
    net_local_port: 本地监听端口号
    net_local_stream_port: 本地监听数据流端口号
    net_target_ip: 目标IP
    net_target_port: 目标端口号
    net_target_stream_port: 目标数据流端口号
    window_title: UI窗口标题
    kps_thr: 关键点可见阈值，置信度小于该值不显示
    cam_idx: 加速板相机下标
    cam_fps: 加速板相机FPS
    cam_img_w: 加速板相机画面宽度
    cam_img_h: 加速板相机画面高度
    show_fps: 显示的速度，默认为None（输入源为Video时，FPS为cam_fps；输入源为图片时，
        FPS为0，任意键下一张图片）
    is_draw_fps: 是否渲染FPS到图片，默认为None（输入源为Video时，渲染FPS；输入源为
        图片时，不渲染FPS）
    is_show_img: 是否显示图片
    '''
    # 检查输入源
    source_type = None
    img_fpaths = None
    if source == '' or source is None:
        source_type = 'dev_camera'
    elif isinstance(source, int):
        source_type = 'video'
    elif isinstance(source, str):
        if osp.isdir(source):
            source_type = 'img'
            img_fpaths = [osp.join(source, x) for x in os.listdir(source) \
                        if osp.splitext(x)[1].lower() in ['.jpg', '.jpeg']]
            if len(img_fpaths) == 0:
                logger.error('The input source directory has no JPEG images')
                exit(0)
        elif osp.isfile(source):
            ext = osp.splitext(source)[1].lower()
            if ext in ['.mp4']:
                source_type = 'video'
            elif ext in ['.jpg', '.jpeg']:
                source_type = 'img'
                img_fpaths = [source]
            else:
                raise ValueError('Invalid input source')
    else:
        raise ValueError('Invalid input source')
    # 输入源为图片时，显示帧率设置为0，不渲染FPS，图片和pose index应一致
    idx_max_diff = 3
    if source_type == 'img':
        if show_fps is None:
            show_fps = 0
        if is_draw_fps is None:
            is_draw_fps = False
        idx_max_diff = 1
    else:
        if is_draw_fps is None:
            is_draw_fps = True

    # 检查图片尺寸
    if source_type == 'img':
        for img_fpath in img_fpaths:
            w, h = imagesize.get(img_fpath)
            if w % 16 != 0 or h % 16 != 0:
                logger.error(f'The length and width must be multiples of 16 ({img_fpath})')
                exit(1)
            if w * h > 1920*1080:
                logger.error(f'The image size must be less than 1920x1080 ({img_fpath})')
                exit(1)

    # 创建Msg Handler
    net_local_addr = (net_local_ip, net_local_port)
    net_target_addr = (net_target_ip, net_target_port)
    net_stream_local_addr = (net_local_ip, net_local_stream_port)
    net_stream_target_addr = (net_target_ip, net_target_stream_port)

    msg_handler = MsgUdpHandler(net_local_addr, net_target_addr, 1)
    msg_stream_handler = MsgUdpHandler(net_stream_local_addr,
            net_stream_target_addr, 1)
    dev_agent = DevAgent(msg_handler)

    # 设置设备属性
    dev_agent.setDevStatus(msg_pb2.DEV_STATUS_PAUSE)
    if source_type == 'dev_camera':
        dev_agent.setCameraParam(cam_idx, cam_img_w, cam_img_h, cam_fps)
        dev_agent.enableSendCamImgStream()
        dev_agent.enableCameraSource()
    else:
        dev_agent.enableSendHumanPoseStream()
        dev_agent.disableSendCamImgStream()
        dev_agent.enableImgStreamSource()
    msg_stream_handler.sendData(b'')
    dev_agent.setStreamTargetAddr('192.168.181.1', net_local_stream_port)
    msg_stream_handler.clearSocketRecvBuf(timeout=0.1)
    dev_agent.setDevStatus(msg_pb2.DEV_STATUS_PLAY)

    logger.info(f"dev status: {dev_agent.getDevStatus()}")
    logger.info(f"media source: {dev_agent.getMediaSource()}",)
    logger.info(f"send human pose flag: {dev_agent.isSendHumanPoseStream()}")
    logger.info(f"stream target addr: {dev_agent.getStreamTargetAddr()}")
    if source_type == 'dev_camera':
        logger.info(f"cam param:\n{dev_agent.getCameraParam()}")
        logger.info(f"cam real param:\n{dev_agent.getCameraRealParam()}")
        logger.info(f"send cam img flag: {dev_agent.isSendCamImgStream()}")

    # 创建 Services
    img_send_queue = Queue(1)
    img_show_queue = Queue(1)
    pose_recv_queue = Queue(2)
    pose_show_queue = Queue(1)

    if source_type == 'dev_camera':
        pose_show_queue = pose_recv_queue
        stream_recv_service = StreamRecvService(msg_stream_handler,
                img_show_queue, pose_recv_queue)
    else:
        stream_recv_service = StreamRecvService(msg_stream_handler, None,
                pose_recv_queue)
        img_send_service = ImgSendService(msg_stream_handler, img_send_queue)
        media_reader = VideoReader(source, cam_size=(cam_img_w,cam_img_h), cam_fps=cam_fps) \
                if source_type == 'video' else ImgsReader(img_fpaths)
        img_read_queue = media_reader.getImgQueue()
        media_service = MediaSourceService(img_read_queue, img_send_queue,
                img_show_queue, pose_recv_queue, pose_show_queue)

    # 创建显示
    cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)
    pose_displayer = HumanPoseDisplayer(window_title, img_show_queue,
            pose_show_queue,
            is_show_img, cam_img_w, cam_img_h, kps_thr,
            show_fps=show_fps, is_draw_fps=is_draw_fps,
            idx_max_diff=idx_max_diff)

    # 开始
    if source_type != 'dev_camera':
        media_reader.start()
        media_service.start()
        img_send_service.start()
    stream_recv_service.start()
    pose_displayer.show()

    # 等待结束
    if source_type != 'dev_camera':
        media_reader.stop()
        media_service.stop()
        img_send_service.stop()
    stream_recv_service.stop()

    if source_type != 'dev_camera':
        media_reader.join()
        media_service.join()
        img_send_service.join()
    stream_recv_service.join()


if __name__ == '__main__':
    fire.Fire(main)