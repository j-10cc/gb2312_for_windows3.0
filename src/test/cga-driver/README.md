# CGA 驱动探针

## 项目目的

cga14test.asm 保存驱动探针汇编；build-cga-probe.bat 是 DDK 的汇编、链接及资源绑定命令。

## 源码结构

- [build-cga-probe.bat](build-cga-probe.bat)
- [cga14test.asm](cga14test.asm)
- [CAPTURE.C](CAPTURE.C)：启动程序管理器、测量标题字宽，保存正常程序组及最小化程序组的 CGA 显存。
- [check_captions.py](check_captions.py)：构造独立测试目录、编译探针、运行模拟器及生成截图。
- [test_system_font.py](test_system_font.py)：检查 7445 个汉字的宽度一致性，以及 ASCII、位图和字体布局不变。

## 编译方法

批处理在将 external/win30ddk 挂载为 DOS C: 后执行，使用其 TOOLS/INCLUDE/LIB。主驱动构建入口是 `python src/main/cga-driver/build_cga_driver.py --trace`；它还需要预生成的中文字体。探针源不单独组成安装包。

[源码总入口](../../README.md)

工具链和外部输入的下载、目录布局见[根 README](../../../README.md#外部依赖与目录结构)。

## 图标标题回归

```powershell
python src/test/cga-driver/test_system_font.py
python src/test/cga-driver/check_captions.py --prepare
python src/main/cga-driver/build_cga_system_font.py
python src/main/cga-driver/build_cga_driver.py --trace
python src/test/cga-driver/check_captions.py --driver src/test/native-gb2312/work/build/driver/CGA-TRACE.DRV --font src/test/native-gb2312/work/build/fonts/CGAS12.FON --label fixed
```

构造夹具使用 `release/W30SC21.ZIP` 和 external 中的原始中文介质、英文 CGA Logo、`win31igdrv/WINDOWS/MAIN.GRP` 模板；不执行图形 Setup。构建系统字体还需组件 README 中的原始 EGASYS.FON 容器。模拟器用 DOS 5.0 API、8086 预取 CPU、CGA 实模式，关闭 FPU、XMS、EMS、UMB。只在 `work/captions` 中运行；截图及测量记录留在该目录。比较修复前后时必须明确传入各自的字体文件，以免沿用上一次测试的字体。最终验证还应分别传入系统包和 Office 包中的正式 CGA.DRV。
