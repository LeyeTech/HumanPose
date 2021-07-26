#coding: utf-8

import struct
import msg_pb2
from msg_udp_handler import *


class DevAgent(object):
    def __init__(self, msg_handler:MsgUdpHandler):
        self.msg_handler = msg_handler

    ############################################################################
    # Get Prop
    ############################################################################
    def getProp(self, prop_id, timeout=None, **args):
        # 发送获取属性的消息
        self.msg_handler.sendGetPropMsg(prop_id, **args)
        # 接收消息
        msg = self.msg_handler.recvMsg(timeout)
        if msg is None:
            return None
        # 解析cmd
        cmd = struct.unpack('H', msg['payload'][:2])[0]
        if cmd != MSG_GET_CMD_RESPONS(msg_pb2.MSG_CMD_GET_PROPERTY):
            print("ERROR: Would cmd(%04x) but got cmd(%04x)" % \
                (msg_pb2.MSG_CMD_GET_PROPERTY, cmd))
            return None
        # 解析proto
        rsp = msg_pb2.RspGetProp()
        rsp.ParseFromString(msg['payload'][2:])
        # 检查状态和属性ID
        if rsp.status != msg_pb2.MSG_STATUS_OK:
            print("ERROR: Got prop(%04x) failed! status: %04x" % \
                    (prop_id, rsp.status))
            return None
        if rsp.prop_id != prop_id:
            print("ERROR: Would prop(%04x) but got prop(%04x)" % (prop_id,
                    rsp.prop_id))
            return None
        return rsp

    def getDevStatus(self):
        '''获取设备状态'''
        rsp = self.getProp(msg_pb2.MSG_PROP_DEVICE_STATUS)
        return None if rsp is None else rsp.dev_status

    def getDevBaseInfo(self):
        '''获取设备基本信息'''
        rsp = self.getProp(msg_pb2.MSG_PROP_DEVICE_BASE_INFO)
        return None if rsp is None else rsp.dev_base_info

    def getTemperature(self):
        '''获取温度'''
        rsp = self.getProp(msg_pb2.MSG_PROP_TEMPERATURE)
        return None if rsp is None else rsp.temperature

    def getAppNewVersion(self):
        '''获取App新版本'''
        rsp = self.getProp(msg_pb2.MSG_PROP_APP_NEW_VERSION)
        return None if rsp is None else rsp.app_new_version

    def getAppVersions(self):
        '''获取App所有版本'''
        rsp = self.getProp(msg_pb2.MSG_PROP_APP_VERSIONS)
        return None if rsp is None else [x for x in rsp.app_versions]

    def getMediaSource(self):
        '''获取媒体输入源'''
        rsp = self.getProp(msg_pb2.MSG_PROP_MEDIA_SOURCE)
        return None if rsp is None else rsp.media_source

    def getCameraParam(self):
        '''获取相机参数'''
        rsp = self.getProp(msg_pb2.MSG_PROP_CAM_PARAM)
        return None if rsp is None else rsp.cam_param

    def getCameraRealParam(self):
        '''获取相机实际运行参数'''
        rsp = self.getProp(msg_pb2.MSG_PROP_CAM_REAL_PARAM)
        return None if rsp is None else rsp.cam_param_real

    def getCameraCtrl(self, _id):
        '''获取相机Ctrl'''
        cam_ctrl = {'id': _id}
        rsp = self.getProp(msg_pb2.MSG_PROP_CAM_CTRL, cam_ctrl=cam_ctrl)
        return None if rsp is None else rsp.cam_ctrl

    def isSendCamImgStream(self):
        '''是否发送图片流'''
        rsp = self.getProp(msg_pb2.MSG_PROP_ENABLE_CAM_IMG_STREAM)
        return None if rsp is None else rsp.is_send_cam_img_stream

    def isEnableAi(self):
        '''是否使能AI'''
        rsp = self.getProp(msg_pb2.MSG_PROP_ENABLE_AI)
        return None if rsp is None else rsp.is_enable_ai

    def getStreamTargetAddr(self):
        '''获取数据流目标地址'''
        rsp = self.getProp(msg_pb2.MSG_PROP_STREAM_TARGET_ADDR)
        return None if rsp is None else rsp.stream_target_addr

    def isSendHumanPoseStream(self):
        '''是否发送HumanPose'''
        rsp = self.getProp(msg_pb2.MSG_PROP_ENABLE_HUMAN_POSE_STREAM)
        return None if rsp is None else rsp.is_send_human_pose_stream

    def getHumanBoxModelParam(self):
        '''获取HumanBox模型参数'''
        rsp = self.getProp(msg_pb2.MSG_PROP_HUMAN_BOX_MODEL_PARAM)
        return None if rsp is None else rsp.human_box_model_param

    def getHumanPose3dModelParam(self):
        '''获取HumanPose3d模型参数'''
        rsp = self.getProp(msg_pb2.MSG_PROP_HUMAN_POSE3D_MODEL_PARAM)
        return None if rsp is None else rsp.human_pose3d_model_param

    def getHumanBoxTrackParam(self):
        '''获取HumanBox追踪参数'''
        rsp = self.getProp(msg_pb2.MSG_PROP_HUMAN_BOX_TRACK_PARAM)
        return None if rsp is None else rsp.human_box_track_param

    def getHumanPose2DFilterParam(self):
        '''获取HumanPose2D过滤器参数'''
        rsp = self.getProp(msg_pb2.MSG_PROP_HUMAN_POSE2D_FILTER_PARAM)
        return None if rsp is None else rsp.human_pose2d_filter_param

    def getHandActionClsParam(self):
        '''获取手部动作分类参数'''
        rsp = self.getProp(msg_pb2.MSG_PROP_HUMAN_HAND_ACTION_CLS_PARAM)
        return None if rsp is None else rsp.hand_action_cls_param

    ############################################################################
    # Set Prop
    ############################################################################
    def setProp(self, proto_obj, timeout=None):
        # 发送设置属性的消息
        self.msg_handler.sendSetPropMsg(proto_obj)
        # 获取消息
        msg = self.msg_handler.recvMsg(timeout)
        if msg is None:
            return False
        # 解析cmd
        cmd = struct.unpack('H', msg['payload'][:2])[0]
        if cmd != MSG_GET_CMD_RESPONS(msg_pb2.MSG_CMD_SET_PROPERTY):
            print("ERROR: Would cmd(%04x) but got cmd(%04x)" % \
                (msg_pb2.MSG_CMD_SET_PROPERTY, cmd))
            return False
        # 解析proto
        rsp = msg_pb2.RspSetProp()
        rsp.ParseFromString(msg['payload'][2:])
        # 检查状态和属性ID
        if rsp.status != msg_pb2.MSG_STATUS_OK:
            print("ERROR: Got prop(%04x) failed! status: %04x" % \
                    (proto_obj.prop_id, rsp.status))
            return False
        if rsp.prop_id != proto_obj.prop_id:
            print("ERROR: Would prop(%04x) but got prop(%04x)" % \
                    (proto_obj.prop_id, rsp.prop_id))
            return False
        return True

    def setDevStatus(self, dev_status):
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_DEVICE_STATUS
        req.dev_status = dev_status
        return self.setProp(req)

    def play(self):
        '''设置设备状态为Play'''
        return self.setDevStatus(msg_pb2.DEV_STATUS_PLAY)

    def pause(self):
        '''设置设备状态为Pause'''
        return self.setDevStatus(msg_pb2.DEV_STATUS_PAUSE)

    def setMediaSource(self, source):
        '''设置媒体输入源'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_MEDIA_SOURCE
        req.media_source.type = source
        return self.setProp(req)

    def enableCameraSource(self):
        '''使用设备相机为输入源'''
        return self.setMediaSource(msg_pb2.MEDIA_CAMERA)

    def enableImgStreamSource(self):
        '''使用外部图片流为是输入源'''
        return self.setMediaSource(msg_pb2.MEDIA_IMAGE_STREAM)

    def setCameraParam(self, idx, width, height, fps=30,
            pix_fmt=msg_pb2.CameraParam.JPEG):
        '''设置相机参数'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_CAM_PARAM
        req.cam_param.idx = idx
        req.cam_param.width = width
        req.cam_param.height = height
        req.cam_param.fps = fps
        req.cam_param.pix_fmt = pix_fmt
        return self.setProp(req)

    def setCameraCtrl(self, _id, value):
        '''设置相机Ctrl（修改相机曝光，亮度，对比度等）'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_CAM_CTRL
        req.cam_ctrl.id = _id
        req.cam_ctrl.value = value
        return self.setProp(req)

    def setSendCamImgStream(self, flag:bool):
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_ENABLE_CAM_IMG_STREAM
        req.is_send_cam_img_stream = flag
        return self.setProp(req)

    def enableSendCamImgStream(self):
        '''使能发送图片流'''
        return self.setSendCamImgStream(True)

    def disableSendCamImgStream(self):
        '''取消发送图片流'''
        return self.setSendCamImgStream(False)

    def setEnabelAi(self, enable:bool):
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_ENABLE_AI
        req.is_enable_ai = enable
        return self.setProp(req)

    def enableAi(self):
        '''使能AI'''
        return self.setEnabelAi(True)

    def disableAi(self):
        '''暂停AI'''
        return self.setEnabelAi(False)

    def setStreamTargetAddr(self, ip, port):
        '''设置数据流目标地址'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_STREAM_TARGET_ADDR
        req.stream_target_addr.ip = ip
        req.stream_target_addr.port = port
        return self.setProp(req)

    def setSendHumanPoseStreamEnable(self, flag:bool):
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_ENABLE_HUMAN_POSE_STREAM
        req.is_send_human_pose_stream= flag
        return self.setProp(req)

    def enableSendHumanPoseStream(self):
        '''使能发送HUmanPose数据流'''
        return self.setSendHumanPoseStreamEnable(True)

    def disableSendHumanPoseStream(self):
        '''取消发送HUmanPose数据流'''
        return self.setSendHumanPoseStreamEnable(False)

    def setHumanBoxModelParam(self, thr:float, iou_thr:float,
            min_width:int, min_height:int):
        '''设置HumanBox模型参数'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_HUMAN_BOX_MODEL_PARAM
        req.human_box_model_param.thr = thr
        req.human_box_model_param.iou_thr = iou_thr
        req.human_box_model_param.min_width = min_width
        req.human_box_model_param.min_height = min_height
        return self.setProp(req)

    def setHumanPose3dModelParam(self, kps_thr:float):
        '''设置HumanPose3d模型参数'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_HUMAN_POSE3D_MODEL_PARAM
        req.human_pose3d_model_param.kps_thr = kps_thr
        return self.setProp(req)

    def setHumanBoxTrackParam(self, roi_x:float, roi_y:float, roi_w:float,
            roi_h:float, roi_overlap_thr:float, roi_overlap_coeff:float):
        '''设置HumanBox追踪参数'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_HUMAN_BOX_TRACK_PARAM
        req.human_box_track_param.roi.x = roi_x
        req.human_box_track_param.roi.y = roi_y
        req.human_box_track_param.roi.w = roi_w
        req.human_box_track_param.roi.h = roi_h
        req.human_box_track_param.roi_overlap_thr = roi_overlap_thr
        req.human_box_track_param.roi_overlap_coeff = roi_overlap_coeff
        return self.setProp(req)

    def setHumanPose2dFilterParam(self, R_std:float, Q_std:float, dt:float,
            P_x:float, P_v:float, v_thr:float, est_err:int):
        '''设置HumanPose2d过滤器参数'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_HUMAN_POSE2D_FILTER_PARAM
        req.human_pose2d_filter_param.R_std   = R_std
        req.human_pose2d_filter_param.Q_std   = Q_std
        req.human_pose2d_filter_param.dt      = dt
        req.human_pose2d_filter_param.P_x     = P_x
        req.human_pose2d_filter_param.P_v     = P_v
        req.human_pose2d_filter_param.v_thr   = v_thr
        req.human_pose2d_filter_param.est_err = est_err
        return self.setProp(req)

    def setHandActionClsParam(self, up_thr:float, down_thr:float,
            left_thr:float, right_thr:float, front_thr:float, back_thr:float):
        '''设置手部动作分类参数'''
        req = msg_pb2.ReqSetProp()
        req.prop_id = msg_pb2.MSG_PROP_HUMAN_HAND_ACTION_CLS_PARAM
        req.hand_action_cls_param.up_thr    = up_thr
        req.hand_action_cls_param.down_thr  = down_thr
        req.hand_action_cls_param.left_thr  = left_thr
        req.hand_action_cls_param.right_thr = right_thr
        req.hand_action_cls_param.front_thr = front_thr
        req.hand_action_cls_param.back_thr  = back_thr
        return self.setProp(req)

    def switchAppVersion(self, version):
        '''切换软件版本号'''
        req = msg_pb2.ReqSwitchAppVersion()
        req.app_version = version
        self.msg_handler.sendMsg(msg_pb2.MSG_CMD_SWITCH_APP_VERSION, req)
        msg_ret = self.msg_handler.recvMsg(1);
        if msg_ret is None:
            return False
        cmd = struct.unpack('H', msg_ret['payload'][:2])[0]
        if cmd != MSG_GET_CMD_RESPONS(msg_pb2.MSG_CMD_SWITCH_APP_VERSION):
            print("ERROR: Would cmd(%04x) but got cmd(%04x)" % \
                (msg_pb2.MSG_CMD_SWITCH_APP_VERSION, cmd))
            return False
        rsp = msg_pb2.RspSwitchAppVersion()
        rsp.ParseFromString(msg_ret['payload'][2:])
        if rsp.app_version != version:
            return False
        return rsp.status == msg_pb2.MSG_STATUS_OK

    def rebootSystem(self):
        '''重启设备'''
        self.msg_handler.sendMsg(msg_pb2.MSG_CMD_REBOOT_SYSTEM)
        msg_ret = self.msg_handler.recvMsg(1);
        if msg_ret is None:  # 超时代表重启成功
            return True
        cmd = struct.unpack('H', msg_ret['payload'][:2])[0]
        if cmd != MSG_GET_CMD_RESPONS(msg_pb2.MSG_CMD_REBOOT_SYSTEM):
            print("ERROR: Would cmd(%04x) but got cmd(%04x)" % \
                (msg_pb2.MSG_CMD_REBOOT_SYSTEM, cmd))
            return False
        rsp = msg_pb2.RspRebootSystem()
        rsp.ParseFromString(msg_ret['payload'][2:])
        return rsp.status == msg_pb2.MSG_STATUS_OK


if __name__ == '__main__':
    import os
    import fire

    net_local_ip = os.getenv('LOCAL_IP', '0.0.0.0')
    net_local_port = int(os.getenv('LOCAL_PORT', 20000))
    net_target_ip = os.getenv('TARGET_IP', '192.168.181.2')
    net_target_port = int(os.getenv('TARGET_PORT', 30000))
    socket_timeout = int(os.getenv('TIMEOUT', 1))
    net_local_addr  = (net_local_ip, net_local_port)
    net_target_addr = (net_target_ip, net_target_port)

    msg_handler = MsgUdpHandler(net_local_addr, net_target_addr, socket_timeout)
    dev_agent = DevAgent(msg_handler)
    fire.Fire(dev_agent)
