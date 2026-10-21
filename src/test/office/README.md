# Office 构建与运行工作目录

## 项目目的

存放 Office 编译输出和运行文件，供应用适配测试使用。

## 源码结构

本目录为工作目录入口；原版输入位于 `external/media/office/word11a`、`excel21d`，测试输出使用 work 子目录。中文适配测试源码位于 [office-patch](../office-patch/README.md)，安装测试位于 [install](../install/README.md)。

## 编译方法

本目录没有独立编译目标。Excel / OFFGROUP 编译命令见[开发组件说明](../../main/office-patch/README.md)，外部输入按[根 README](../../../README.md#外部依赖与目录结构)准备。
