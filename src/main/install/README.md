# Windows / Office 安装器

## 项目目的

提供 Windows 的 DOS 安装批处理、路径与术语配置工具，以及支持 DOS 5.0 / 8086 的 Office 安装、卸载和恢复程序。

## 源码结构

| 文件或目录 | 用途 |
| --- | --- |
| `build.py` | 编译 Office 安装器、GBPATH、GBTERM |
| `build_office_dos5.py` | 编译 Office DOS 安装器 |
| `publish_install_no_checks.py` | 将安装程序和使用手册写入发布 ZIP |
| `windows/INSTALL.BAT`、`FINALIZE.BAT` | Windows 安装与 Setup 后配置 |
| `windows/GBPATH.C`、`build_path_tool.py` | 路径、显示配置处理及其编译入口 |
| `windows/GBTERM.C` | 简体中文术语处理 |
| `office/install62.c` | INSTALL、REMOVE、RECOVER 共用实现 |
| `office/ini62.h`、`group64.h`、`tables62.h` | INI、程序组和复制文件表 |

## 编译方法

按[依赖说明](../../../README.md#外部依赖与目录结构)准备 Python 和 Open Watcom。从项目根目录执行：

```powershell
python src/main/install/build.py
```

Office 使用 `-0 -bt=dos -ml -ot -k24576`，Windows 辅助程序使用 `-0 -bt=dos`，目标为 8086 DOS。输出及日志位于 `src/test/install/work/build`；Office 安装器位于 compiler，Windows 辅助程序位于 windows。BAT 文件直接随安装包使用。

单独编译 Office 可执行 `python src/main/install/build_office_dos5.py`；单独编译 GBPATH 可执行 `python src/main/install/windows/build_path_tool.py`。

发布命令为 `python src/main/install/publish_install_no_checks.py`，需要 release 下两份完整 ZIP、上述编译输出、`src/test/install/work/no-checks/results.json` 和 `src/test/install/fixtures/release` 数据。此命令更新安装程序和手册，不生成 Windows / Office 主程序。
