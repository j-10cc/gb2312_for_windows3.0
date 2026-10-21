# CGA 驱动探针

## 项目目的

cga14test.asm 保存驱动探针汇编；build-cga-probe.bat 是 DDK 的汇编、链接及资源绑定命令。

## 源码结构

- [build-cga-probe.bat](build-cga-probe.bat)
- [cga14test.asm](cga14test.asm)

## 编译方法

批处理在将 external/win30ddk 挂载为 DOS C: 后执行，使用其 TOOLS/INCLUDE/LIB。主驱动构建入口是 `python src/main/cga-driver/build_cga_driver.py --trace`；它还需要预生成的中文字体。探针源不单独组成安装包。

[源码总入口](../../README.md)

工具链和外部输入的下载、目录布局见[根 README](../../../README.md#外部依赖与目录结构)。
