# 中文系统与输入法测试源码

## 项目目的

GB*.C 和 PYPROBE.C 是窗口、字符、输入法与打印探针；pinyin21 保存拼音诊断实现；simplified_big5 保存位图解析脚本。原版介质在 external/media/windows，反汇编参考在 external/disassembly。

## 源码结构

- [build_huge_probe.py](build_huge_probe.py)
- [build_ime_probe.py](build_ime_probe.py)
- [build_print_probe.py](build_print_probe.py)
- [GBHUGE.C](GBHUGE.C)
- [GBICON.C](GBICON.C)
- [GBMISS.C](GBMISS.C)
- [GBNATST.C](GBNATST.C)
- [GBNATWRITE.C](GBNATWRITE.C)
- [GBPINTST.C](GBPINTST.C)
- [GBPYVIS.C](GBPYVIS.C)
- [GBPYWRITE.C](GBPYWRITE.C)
- [GBWINTRC.C](GBWINTRC.C)
- [GBWRITET.C](GBWRITET.C)
- [pinyin21/](pinyin21/)
- [PYPROBE.C](PYPROBE.C)
- [simplified_big5/](simplified_big5/)

## 编译方法

从项目根目录执行 `python src/test/native-gb2312/build_ime_probe.py --native` 或 `python src/test/native-gb2312/build_huge_probe.py`，使用 external/open-watcom 的 `-0 -bt=windows` 生成探针。打印探针使用 build_print_probe.py；其默认 GBPRINT.C 源码在 src/main/native-gb2312，`--write` 使用本目录 GBWRITET.C。来宾运行需要独立 DOS/Windows 测试环境。

[源码总入口](../../README.md)

### 拼音诊断与位图工具

`pinyin21/PY2SAVE.C`、`PY2SHOT.C` 是保存与截图探针，使用 `wcc -0 -bt=windows 文件.C`、`wlink system windows name 文件.EXE file 文件.obj` 编译链接。

`pinyin21/common-trace/PINYIN_NATIVE.C`、`PINYIN_DICT.H` 是向 0xE9 端口输出记录的诊断输入法。其编译方法如下：

设置 external/open-watcom 的 WATCOM、PATH、INCLUDE、LIB 后，在独立工作目录编译：

```text
wcc -0 -bt=windows -os PINYIN_NATIVE.C
wlink system windows name PHON.IME file PINYIN_NATIVE.obj export DLGPROC.1=PinyinDlgProc export IMEWNDPROC.2 option modname=PHON option stack=2048 option heapsize=256
```

先将 `pinyin21/common-trace` 中的两个源文件复制到工作目录，避免覆盖正式源码。实际诊断运行另需字典、INI、字体及可采集 0xE9 端口的来宾环境。

`pinyin21/TRACE_RUN.py` 需要 test_runtime、test_office 运行夹具；这两个模块不包含在仓库中，缺少时不能直接运行。诊断 C 源可按上面的命令编译。

`simplified_big5/render_mono.py` 使用 Python 标准库直接运行：`python src/test/native-gb2312/simplified_big5/render_mono.py 描述文件 原始位图 输出.png`，用于人工查看 Win16 单色设备位图输出。

外部工具和数据按[根 README](../../../README.md#外部依赖与目录结构)准备。
