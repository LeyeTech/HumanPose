#coding: utf-8

from logging import log
import os
import cv2
import time
import fire
import numpy as np
import queue
import imagesize
import os.path as osp
from queue import Queue
from loguru import logger
from typing import Union

from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.opengl as gl

import msg_pb2
from dev_agent import DevAgent
from msg_udp_handler import MsgUdpHandler
from vis import drawBox, drawKps, drawActions2, drawText
from vis import KPS_SKELETONS, KPS_JOINTS
from fps_helper import FPSHelper

from demo import VideoReader, ImgsReader, ImgSendService, StreamRecvService, \
    MediaSourceService


class HumanPoseWidget(gl.GLViewWidget):
    def __init__(self,
            img_queue:Queue,
            pose_queue:Queue,
            kps_thr:float,
            show_fps:float=None,
            is_draw_fps:bool=True,
            is_show_img:bool=True,
            kps3d_max_height=3000,
            kps3d_z_offset=0.5,
            idx_max_diff=5,
            parent=None):
        super().__init__(parent)
        self.img_queue = img_queue
        self.pose_queue = pose_queue
        self.kps_thr = kps_thr
        self.show_fps = show_fps
        self.kps3d_max_height = kps3d_max_height
        self.kps3d_z_offset = kps3d_z_offset
        self.is_draw_fps = is_draw_fps
        self.is_show_img = is_show_img
        self.idx_max_diff = idx_max_diff
        self.initUi()
        self.last_frame = None
        self.last_pose = None
        self.fps_helper = FPSHelper()
        self.last_update_time = None
        self.any_key_pressed = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.handleTimeout)

    def initUi(self):
        self.opts['distance'] = 1000
        # 初始化GL图片
        self.gl_img = gl.GLImageItem(np.zeros((640, 360, 4), dtype=np.ubyte),
                glOptions='opaque')
        self.addItem(self.gl_img)
        # 初始化GL网格
        self.gl_grid_x = gl.GLGridItem(QtGui.QVector3D(640,640,1))
        self.addItem(self.gl_grid_x)
        self.gl_grid_y = gl.GLGridItem(QtGui.QVector3D(640,640,1))
        self.addItem(self.gl_grid_y)
        self.gl_grid_z = gl.GLGridItem(QtGui.QVector3D(640,640,1))
        self.addItem(self.gl_grid_z)
        self.updateItemTransform((640, 360))
        # 初始化Pose3d骨骼
        self.skeleton_items = []
        for  _ in range(len(KPS_SKELETONS)):
            pts = np.array([[0, 0, 0], [0, 0, 0]])
            color = (0, 0, 0, 0)
            plt = gl.GLLinePlotItem(pos=pts, color=color, width=5,
                    antialias=True)
            self.addItem(plt)
            self.skeleton_items.append(plt)
        # 初始化Pose3d骨骼关键点
        self.joint_items = []
        for _ in range(len(KPS_JOINTS)):
            pos = np.zeros((1, 3))
            color = (0, 0, 0, 0)
            sp = gl.GLScatterPlotItem(pos=pos, color=color, size=0.1,
                    pxMode=False)
            self.addItem(sp)
            self.joint_items.append(sp)
        # 添加坐标轴
        ax = gl.GLAxisItem(QtGui.QVector3D(64,64,64))
        self.addItem(ax)


    def start(self):
        self.timer.start(0)

    def keyPressEvent(self, ev):
        super().keyPressEvent(ev)
        # 按键'Q'或'Esc'，关闭窗口
        if ev.key() in [QtCore.Qt.Key.Key_Q, QtCore.Qt.Key.Key_Escape]:
            self.close()
        if ev.key() not in self.noRepeatKeys:
            self.any_key_pressed = True


    def mouseMoveEvent(self, ev):
        '''重载鼠标移动方法
        fix: 鼠标没按下时，mousePos属性不存在
        '''
        lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
        if not hasattr(self, 'mousePos'):
            self.mousePos = lpos
        super().mouseMoveEvent(ev)


    def handleTimeout(self):
        # 控制显示FPS
        if self.show_fps is not None and self.last_update_time is not None:
            if self.show_fps == 0:
                if not self.any_key_pressed:
                    return
                self.any_key_pressed = False
            else:
                if time.time()-self.last_update_time < 1/self.show_fps:
                    return
        # 获取img
        if self.last_frame is None:
            frame = None
            while not self.img_queue.empty():
                frame = self.img_queue.get()
            if frame is not None:
                # 解码
                img_idx, img = frame
                if isinstance(img, bytes):
                    img = self.decodeImg(img)
                self.last_frame = (img_idx, img)
                self.fps_helper.update()
        # 获取pose
        pose = None
        while not self.pose_queue.empty():
            pose = self.pose_queue.get()
        if pose is None:
            return
        self.last_pose = pose
        if self.last_frame is None:
            return
        # 更新
        if self.updateImg():
            self.last_frame = None
            self.last_update_time = time.time()

    def decodeImg(self, img_str):
        img_data = np.frombuffer(img_str, dtype=np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        if img is None:
            print("ERROR: img decode failed!\n");
            return
        return img

    def updatePose3d(self, kps):
        # Draw skeletons
        for i, (idx_s, idx_e, color, thickness) in enumerate(KPS_SKELETONS):
            if kps[idx_s][-1] == 0 or kps[idx_e][-1] == 0:
                self.skeleton_items[i].setData(color=(0, 0, 0, 0))
                continue
            kp_s = np.array(kps[idx_s][:-1], dtype=np.float32)
            kp_e = np.array(kps[idx_e][:-1], dtype=np.float32)
            pts = np.row_stack((kp_s, kp_e))
            color = [color[2]/255., color[1]/255., color[0]/255., 1]
            self.skeleton_items[i].setData(pos=pts, color=color)
        # Draw joints
        for i, (radius, color, thickness) in enumerate(KPS_JOINTS):
            if kps[i][-1] == 0:
                self.joint_items[i].setData(color=(0, 0, 0, 0))
                continue
            kp = np.array(kps[i][:-1], dtype=np.float32)
            pos = kp.reshape(1, 3)
            self.joint_items[i].setData(pos=pos, color=(1,1,1,1))

    def resetPose3d(self):
        kps3d = [[0, 0, 0, 0]] * len(KPS_JOINTS)
        self.updatePose3d(kps3d)

    def fixKps3d(self, kps3d, kps2d, img_size):
        img_w, img_h = img_size
        # 调整kps3d到图片尺寸（近似）
        scale = img_h / self.kps3d_max_height
        kps3d = [[p[0]*scale, p[1]*scale, p[2]*scale, p[3]] for p in kps3d]
        # 调整根节点坐标
        kp2d_root = kps2d[-1]
        x_diff = kp2d_root[0] - (img_w / 2)
        y_diff = kp2d_root[1] - (img_h / 2)
        z_diff = max(img_size) * (self.kps3d_z_offset - 0.5)
        kps3d = [[p[0]-x_diff, p[1]+z_diff, p[2]-y_diff, p[3]] for p in kps3d]
        return kps3d

    def updateItemTransform(self, img_size, grid_num=20):
        img_w, img_h = img_size
        grid_size = max(img_w, img_h)
        grid_size_half = grid_size / 2
        grid_space = grid_size / grid_num
        # 更新gl_img变换矩阵
        self.gl_img.resetTransform()
        self.gl_img.rotate(-90, 1, 0, 0)
        self.gl_img.rotate(90, 0, 1, 0)
        self.gl_img.translate(img_w/2, -grid_size_half+1, img_h/2)
        # 更新gl_grid_x大小和变换矩阵
        self.gl_grid_x.setSize(grid_size, grid_size, 1)
        self.gl_grid_x.resetTransform()
        self.gl_grid_x.rotate(90, 0, 1, 0)
        self.gl_grid_x.translate(-grid_size_half, 0, 0)
        self.gl_grid_x.setSpacing(grid_space, grid_space, 1)
        # 更新gl_grid_y大小和变换矩阵
        self.gl_grid_y.setSize(grid_size, grid_size, 1)
        self.gl_grid_y.resetTransform()
        self.gl_grid_y.rotate(90, 1, 0, 0)
        self.gl_grid_y.translate(0, -grid_size_half, 0)
        self.gl_grid_y.setSpacing(grid_space, grid_space, 1)
        # 更新gl_grid_z大小和变换矩阵
        self.gl_grid_z.setSize(grid_size, grid_size, 1)
        self.gl_grid_z.resetTransform()
        self.gl_grid_z.translate(0, 0, -grid_size_half)
        self.gl_grid_z.setSpacing(grid_space, grid_space, 1)


    def updateImg(self):
        if self.last_frame is None:
            return
        img_idx, img = self.last_frame
        img_h, img_w = img.shape[:2]
        if self.last_pose is None:
            return
        pose_idx, pose = self.last_pose
        # human数据与图片idx相差太远，则不绘制
        if abs(pose_idx-img_idx) > self.idx_max_diff:
            return
        # 更新GL变换坐标
        if self.gl_img.data.shape[0] != img_w or \
                self.gl_img.data.shape[1] != img_h:
            self.updateItemTransform((img_w, img_h))
        # 绘制Pose
        if 'boxes' in pose:
            for b in pose['boxes']:
                drawBox(img, b, b[-1], thickness=2, text_y_offset=38,
                        text_color=(30,30,30), text_size=1.5,
                        text_thickness=3)
        if 'kps' in pose:
            drawKps(img, pose['kps'])
        if 'kps3d' in pose:
            kps3d = self.fixKps3d(pose['kps3d'], pose['kps'],
                    (img.shape[1], img.shape[0]))
            self.updatePose3d(kps3d)
        else:
            self.resetPose3d()
        if 'hand_dir' in pose:
            left_dir, right_dir = pose['hand_dir']
            drawActions2(img, pose['boxes'][0], left_dir, (200, 0, 0),
                    coord_offset=-20, font_size=1.2, thickness=10)
            drawActions2(img, pose['boxes'][0], right_dir, (0, 200, 0),
                    coord_offset=20, font_size=1.2, thickness=10)
        # 绘制fps到图像
        if self.is_draw_fps:
            drawText(img, "%.1f" % self.fps_helper.fps, 10, 30)
        # 更新图片
        if self.is_show_img:
            img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
            # 注意：这里发生严重的内存泄漏
            self.gl_img.setData(img_rgba)
        return True


def main(
    source          :Union[str, int] = '',
    net_local_ip    :str             = '0.0.0.0',
    net_target_ip   :str             = '192.168.181.2',
    net_port        :int             = 30000,
    net_stream_port :int             = 30001,
    window_title    :str             = 'Human Pose',
    kps_thr         :float           = 0.6,
    cam_idx         :int             = 0,
    cam_fps         :int             = 30,
    cam_img_w       :int             = 1280,
    cam_img_h       :int             = 720,
    show_fps        :bool            = None,
    is_draw_fps     :bool            = None,
    is_show_img     :bool            = True,
    kps3d_max_height:float           = 2000.,
    kps3d_z_offset  :float           = 0.5,
    ):
    '''
    3D Demo

    Args:
    source: 输入源
        如果输入源（source）为空或None，使用设备摄像头;
        如果输入源为数字，使用主机摄像头;
        如果输入源为.mp4视频，读取.mp4视频;
        如果输入源为.jpg图片，读取.jpg图片;
        如果输入源为目录，读取该目录下所有的.jpg图片。

        ``注意：输入源图片宽和高必须是16的倍数，且尺寸小于1920x1080``
    net_local_ip: 本地监听IP
    net_target_ip: 目标IP
    net_port: 属性通信端口
    net_stream_port: 数据流通信端口
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
    kps3d_max_height: 3d骨骼最大高度
    kps3d_z_offset: 3d骨骼里图片的距离（图片最大的一边*kps3d_z_offset）
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
    # 输入源为图片时，显示帧率设置为0，不渲染FPS
    if source_type == 'img':
        if show_fps is None:
            show_fps = 0
        if is_draw_fps is None:
            is_draw_fps = False
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
    net_local_addr = (net_local_ip, net_port)
    net_target_addr = (net_target_ip, net_port)
    net_stream_local_addr = (net_local_ip, net_stream_port)
    net_stream_target_addr = (net_target_ip, net_stream_port)

    msg_handler = MsgUdpHandler(net_local_addr, net_target_addr, 1)
    msg_stream_handler = MsgUdpHandler(net_stream_local_addr,
            net_stream_target_addr, 1)
    dev_agent = DevAgent(msg_handler)

    # 设置设备属性
    time.sleep(0.1)
    if source_type == 'dev_camera':
        dev_agent.setCameraParam(cam_idx, cam_img_w, cam_img_h, cam_fps)
        dev_agent.enableSendCamImgStream()
        dev_agent.enableCameraSource()
    else:
        dev_agent.enableSendHumanPoseStream()
        dev_agent.disableSendCamImgStream()
        dev_agent.enableImgStreamSource()
    dev_agent.setDevStatus(msg_pb2.DEV_STATUS_PLAY)
    time.sleep(0.1)

    logger.info(f"dev status: {dev_agent.getDevStatus()}")
    logger.info(f"media source: {dev_agent.getMediaSource()}",)
    logger.info(f"send human pose flag: {dev_agent.isSendHumanPoseStream()}")
    if source_type == 'dev_camera':
        logger.info(f"cam param:\n{dev_agent.getCameraParam()}")
        logger.info(f"cam real param:\n{dev_agent.getCameraRealParam()}")
        logger.info(f"send cam img flag: {dev_agent.isSendCamImgStream()}")

    # 创建 Services
    img_send_queue = Queue(1)
    img_show_queue = Queue(1)
    pose_recv_queue = Queue(3)
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
    app = pg.mkQApp(window_title)
    cw = HumanPoseWidget(img_show_queue, pose_show_queue,
            kps_thr=kps_thr,
            kps3d_max_height=kps3d_max_height,
            kps3d_z_offset=kps3d_z_offset,
            show_fps=show_fps,
            is_draw_fps=is_draw_fps,
            is_show_img=is_show_img)
    cw.setWindowTitle(window_title)
    cw.show()

    # 开始
    if source_type != 'dev_camera':
        media_reader.start()
        media_service.start()
        img_send_service.start()
    stream_recv_service.start()
    cw.start()
    pg.exec()

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