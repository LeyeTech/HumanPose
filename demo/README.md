## HumanPose 测试客户端
用于测试HumanPose加速卡，运行环境Python3.7+。
```shell
# 环境安装（推荐使用conda创建环境）
pip install -i https://pypi.mirrors.ustc.edu.cn/simple -r requirements.txt
```

### 设备代理 dev_agent.py
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

### Demo demo.py
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
# 外部输入
################################################################################
# 使用主机摄像头0
python3 demo.py 0
# 读取指定的视频
python3 demo.py xxx.mp4
# 读取指定图片
python3 demo.py xxx.jpg
# 读取指定目录下所有的图片
python3 demo.py images
```

### 3D Demo demo3d.py
显示Box，Pose2d，动作判定结果和Pose3d。

使用方法与*demo.py*一致.
