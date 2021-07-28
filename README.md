# 乐野 AI加速板

[API 说明](https://github.com/LeyeTech/HumanPose/doc/api.md)

## 快速开始（Python）

### 下载源码，安装依赖
需要Python>=3.6.0
```shell
$ git clone https://github.com/LeyeTech/HumanPose.git
$ cd HumanPose
# 推荐使用国内软件源
$ pip install -i https://pypi.mirrors.ustc.edu.cn/simple -r requirements.txt
```

### 设置静态IP
将AI加速卡插入电脑USB口。

**Windows**:
- [安装驱动](https://github.com/LeyeTech/HumanPose/driver/windows_cdc_eem/README.md)
- [设置静态IP](https://github.com/LeyeTech/HumanPose/doc/windows_set_static_IP_address.md)

**Ubuntu**:
- 驱动自带，无需安装
- [设置静态IP](https://linuxconfig.org/how-to-configure-static-ip-address-on-ubuntu-18-04-bionic-beaver-linux)，
将AI加速板网卡的IP设置为192.168.181.2。

### 运行Demo
```shell
$ cd demo
$ python demo.py
```
demo的详细使用，参考demo目录下的[README.md](https://github.com/LeyeTech/HumanPose/demo/README.md)。
