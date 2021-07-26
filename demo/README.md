# HumanPose 测试客户端
用于测试HumanPose加速卡，运行环境Python3.7+。
```shell
# 环境安装（推荐使用conda创建环境）
pip install -i https://pypi.mirrors.ustc.edu.cn/simple -r requirements.txt
```

## 设备代理 dev_agent.py
用于设置和读取设备属性，可单独运行。

依赖：`protobuf>=3.6 fire`

使用说明：
```shell
# 查看帮助
python3 dev_agent.py -- --help
# 获取设备基础信息
python3 dev_agent.py getDevBaseInfo
# 获取摄像头信息
python3 dev_agent.py getCameraRealParam
# 获取设备温度
python3 dev_agent.py getTemperature
# 查看当前输入源
python3 dev_agent.py getMediaSource

# 设置摄像头（下标0，尺寸为640x480）
python3 dev_agent.py setCameraParam 0 640 480
# 使能AI
python3 dev_agent.py enableAi
# 使能图片传输
python3 dev_agent.py enableSendCamImgStream
# 取消图片传输
python3 dev_agent.py disableSendCamImgStream
# 切换输入源为外部图片流
python3 dev_agent.py enableImgStreamSource
# 切换输入源为设备摄像头
python3 dev_agent.py enableCameraSource
```

## Demo demo.py
显示Box，Pose2d和动作判定结果。

使用说明：

demo第一个参数为输入源：
- 如果输入源（source）为空或None，使用设备摄像头;
- 如果输入源为数字，使用主机摄像头;
- 如果输入源为.mp4视频，读取.mp4视频;
- 如果输入源为.jpg图片，读取.jpg图片;
- 如果输入源为目录，读取该目录下所有的.jpg图片。

**注意**：输入源图片宽和高必须是16的倍数，且尺寸小于1920x1080。
```shell
# 查看帮助
python3 demo.py -- --help

################################################################################
# 使用加速板摄像头
################################################################################
# 使用默认参数运行，键盘'q'或'Esc'退出程序
python3 demo.py
# 设置摄像头尺寸为640x480
python3 demo.py --cam_img_w 640 --cam_img_h 480
# 设置摄像头尺寸为1280x720，但不显示图片
python3 demo.py --cam_img_w 1280 --cam_img_h 720 --is_show_img False

################################################################################
# 使用外部输入源
################################################################################
# 使用主机摄像头0
python3 demo.py 0
# 推理指定的视频
python3 demo.py xxx.mp4
# 推理指定图片
python3 demo.py xxx.jpg
# 推理指定目录下所有的图片
python3 demo.py images
```

## 3D Demo demo3d.py
显示Box，Pose2d，动作判定结果和Pose3d。

使用方法与*demo.py*一致.

**注意**：该demo有内存泄漏，输入源为摄像头或视频时，内存会很快增加；输入源为单张图片时，内存不会增加。建议3d demo用于图片的Pose预测。

## UDP代理的使用
如果demo在连接有AI加速板的主机上跑时，可使用udp代理透传。
```shell
# udp 代理: external_access--> front_port --> back_port --> target_addr
# udp_proxy.py 可以在python2.7+和python3.7+下运行，不依赖额外库。
python udp_proxy.py --help

# 使用案例
# PC --> E5(192.168.7.4) --> AI加速板(192.168.181.2)

# E5 开启UDP代理
## 开启udp 30000（AI加速板）代理
python udp_proxy.py 30010 30020 192.168.181.2 30000 -v
## 开启udp 30001（AI加速板）代理
python udp_proxy.py 30011 30021 192.168.181.2 30001 -v

# PC 运行dev_agent.py
## 获取设备基础信息
TARGET_IP=127.0.0.1 TARGET_PORT=30010 python dev_agent.py getDevBaseInfo

# PC 运行demo.py
## 使用AI加速板摄像头 键盘'q'或'Esc'退出程序
### 注意：net_local_stream_port要与udp代理back_port一致。
python demo.py \
  --net_target_ip 192.168.7.4 \
  --net_target_port 30010 \
  --net_target_stream_port 30011 \
  --net_local_stream_port 30021 \
  --cam_img_w 640 \
  --cam_img_h 480

## 推理本地图片
python demo.py images \
  --net_target_ip 192.168.7.4 \
  --net_target_port 30010 \
  --net_target_stream_port 30011 \
  --net_local_stream_port 30021
```