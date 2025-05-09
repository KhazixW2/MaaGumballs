<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <img alt="LOGO" src="https://cdn.jsdelivr.net/gh/MaaAssistantArknights/design@main/logo/maa-logo_512x512.png" width="256" height="256" />
</p>

<div align="center">

# MaaGumballs

</div>

本仓库为 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 所提供的项目模板，开发者可基于此模板直接创建自己的 MaaXXX 项目。

> **MaaFramework** 是基于图像识别技术、运用 [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) 开发经验去芜存菁、完全重写的新一代自动化黑盒测试框架。
> 低代码的同时仍拥有高扩展性，旨在打造一款丰富、领先、且实用的开源库，助力开发者轻松编写出更好的黑盒测试程序，并推广普及。

## 即刻开始

- [📄 快速开始](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/1.1-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B.md)
- [🎞️ 视频教程](https://www.bilibili.com/video/BV1yr421E7MW)
- [流水线协议](https://github.com/KhazixW2/MaaGumballs/docs/3.1-任务流水线协议)

## 如何使用

1. 点击链接下载最新[Release](https://github.com/KhazixW2/MaaGumballs/releases/tag/v0.7)包

2. 解压后双击`MFAAvalonia.exe`即可运行

### Windows

- 对于绝大部分用户，请下载 MaaGumballs-win-x86_64.zip
- 若确定自己的电脑是 arm 架构，请下载 MaaGumballs-win-aarch64.zip
- 请注意！Windows 的电脑几乎全都是 x86_64 的，可能占 99.999%，除非你非常确定自己是 arm，否则别下这个！_
- 解压后运行 MFAAvalonia.exe（图形化界面，推荐使用，老版本UI为MFAWPF.exe）或 MaaPiCli.exe（命令行）即可

### macOS

- 若使用 Intel 处理器，请下载 `MaaGumballs-macos-x86_64.zip`
- 若使用 M1, M2 等 arm 处理器，请下载 `MaaGumballs-macos-aarch64.zip`
- 使用方式：

  ```bash
  chmod a+x MaaPiCli
  ./MaaPiCli
  ```

### Linux

~~用 Linux 的大佬应该不需要我教~~

## 图形化界面

- <span style="font-size:25px;">[MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia/)</span>  
- 由社区大佬[SweetSmellFox](https://github.com/SweetSmellFox)编写的基于Avalonia的GUI,通过内置的MAAframework来直接控制任务流程  
- 打开本程序和模拟器后，先在右上方选择要控制的模拟器  
- 勾选想要执行的任务后**开始任务**，任务会顺序执行，***进入游戏***会启动游戏程序，其他任务需要游戏为开启状态  
- 点击部分任务右方的设置，可以配置任务属性和查看任务帮助
![alt text](GUI.png)
![alt text](GUI-2.png)

## 注意事项

- 提示“应用程序错误”，一般是缺少运行库，请安装一下 [vc_redist](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- 添加 `-d` 参数可跳过交互直接运行任务，如 `./MaaPiCli.exe -d`
- MAA framework 2.0 版本已支持 mumu 后台保活，会在 run task 时获取 mumu 最前台的 tab
- 基于mumu模拟器1600x900 dpi240开发，其它模拟器或分辨率如遇到问题，可首先尝试上述配置
- 因MAA基于720p开发图像识别，1280*720(240DPI)理论上有最强适配性，如1080p遇到问题，可换720p尝试
- 反馈问题请附上日志文件 `debug/maa.log`以及问题界面的截图，谢谢！

## 常用工具

1. 调试：[MaaDebugger](https://github.com/MaaXYZ/MaaDebugger) 进行调试json节点.
2. 截图、取色、取区域: [MFATools](https://github.com/SweetSmellFox/MFATools)
3. 代码集成环境：[集成开发环境文档](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/2.1-%E9%9B%86%E6%88%90%E6%96%87%E6%A1%A3.md)

## Todo（先画饼）

- [x]启动
  - [x]进入游戏大厅

- [ ]每日收菜
  - [x]每日签到
  - [x]炼金招牌
  - [x]派遣魔蜥
  - [x]每日扫荡
  - [x]天空探索
  - [x]遗迹探索
  - [x]荒野探索
  - [ ]马戏团任务
  - [ ]其他任务

- [ ]商店购物————
  - [ ]旅游商店——默认购买所有金币商品
  - [ ]佣兵商店——默认全部购买
  - [ ]天空商店——默认购买所有遗迹碎片商品
  - [ ]联盟商店——默认不购买
  - [ ]混沌商店——默认不购买

- [ ]战斗————阵容和地图隐藏可能要单独写，或者合并写
  - [√]自动刷失落降临限时副本
  - [ ]养狗速刷100层
  - [ ]王帝夜100层
  - [ ]白学100层
  - [ ]神锻速刷100层
  - [ ]xx地图隐藏

- [ ]外域探索
  - [ ]每日星域探索/征收——设置资源星/小行星
  - [ ]速刷情报
  - [ ]

- [ ]奖励
  - [ ]联盟任务一键完成
  - [ ]联盟礼包
  - [ ]邮件奖励
  - [ ]地图彩蛋

## 鸣谢

本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！

感谢以下开发者对本项目作出的贡献:

[![Contributors](https://contrib.rocks/image?repo=KhazixW2/MaaGumballs)](https://github.com/KhazixW2/MaaGumballs/graphs/contributors)
