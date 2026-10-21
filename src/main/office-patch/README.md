# Office 简体中文适配

## 项目目的

保存 Windows 3.0 下 Word / Excel 的中文适配、程序组和打印修补，及资源生成、链接工具。Word 原始发布源码在 `external/word11a-source`，合并源树在 `external/word11a-current`；本组件保留我们编写的实现和源码差异。

## 源码结构

下表路径相对本目录。外部输入的下载来源和目录要求见[根 README](../../../README.md#外部依赖与目录结构)。

| 路径 | 代码用途 |
| --- | --- |
| `office-w30/excel/cga/excel.c` | CGA 布局下启动 XLCORE.EXE、中文编辑、窗口和菜单适配 |
| `office-w30/excel/vga/excel.c` | VGA 布局下的同类适配 |
| `office-w30/program-group/OFFGROUP.C` | 通过程序管理器 DDE 增删中文办公程序项，CGA 使用短标题 |
| `office-w30/printer/pin_printer_args.py` | 包装 CEPSON.DRV 模态调用，保护设备名与端口名参数 |
| `office-w30/word/CASHMERE/*.patch` | Word 窗口、菜单、对话框、编辑和字符处理修改 |
| `office-w30/word/CASHMERE/asm` | 原生显示与字形格式处理的 16 位汇编差异 |
| `office-w30/word/CASHMERE/interp` | 宏解释器相关修改 |
| `office-w30/word/CASHMERE/wordtech` | GB2312 双字节格式化、编辑与字符定义修改 |
| `office-w30/word/CASHMERE/resource`、`office-w30/word/OPUS` | 资源头、命令表及链接输入差异 |
| `office-w30/word/source-map.json` | Word 源文件与原始发布路径、差异文件的对应关系 |
| `office-w30/recipe/build_52_*.py`、`build_53_*.py` | 菜单、消息、对话框及预览资源处理 |
| `office-w30/recipe/build_57_*.py` | 资源、系统菜单、Excel 和程序组处理逻辑 |
| `office-w30/recipe/rebuild_57_word.py`、`rebuild_57_about.py` | Word 系统菜单、关于窗口的源码修改及增量链接 |
| `office-w30/recipe/audit_ne.py`、`patch_53_runtime.py` | NE 边界分析与运行时显示字段修补 |
| `office-w30/recipe/patch_word_messages52.py`、`patch_word_sdm52.py` | Word 消息字段和 SDM 对话框资源处理 |
| `office-w30/recipe/patches` | 源码差异与启动器输入 |
| `office-w30/recipe/support/audit_pcode.py` | p-code 对象与链接关系分析 |
| `office-w30/recipe/support/rebuild_table_candidate.py` | 受影响模块的编译、汇编和链接辅助 |
| `office-w30/recipe/support/build_word_release.py`、`fixed_ui_data.py` | 固定 UI 字段处理实现及翻译数据 |
| `office-w30/recipe/support/patch_print.py` | 打印相关源码修补 |

其中 `CASHMERE` 对应原始发布源码的 `Opus` 实现，`OPUS` 保存链接和生成资源输入；未修改的供应方文件仅在 external 保存。完整的增量模块输入在 `external/office-recipe-inputs`，安装器在相邻 [install](../install/README.md)。

## 编译方法

### Excel 和程序组

从项目根目录配置 Open Watcom：

```powershell
$projectRoot = (Get-Location).Path
$env:WATCOM = "$projectRoot/external/open-watcom"
$env:PATH = "$env:WATCOM/binnt64;$env:PATH"
$env:INCLUDE = "$env:WATCOM/h;$env:WATCOM/h/win"
$env:LIB = "$env:WATCOM/lib286;$env:WATCOM/lib286/win"
```

以 CGA Excel 适配为例，在独立工作目录编译：

```powershell
$buildDir = "$projectRoot/src/test/office/work/excel-cga"
New-Item -ItemType Directory -Force $buildDir | Out-Null
Push-Location $buildDir
wcc -0 -bt=windows "$projectRoot/src/main/office-patch/office-w30/excel/cga/excel.c"
wlink system windows name EXCEL.EXE file excel.obj option modname=XLGB
Pop-Location
```

编译目标为 8086 Windows；这里只生成适配程序，Office 主程序及中文资源仍使用安装包中的对应文件。

VGA 版本将示例中的 `excel/cga/excel.c` 改为 `excel/vga/excel.c`，并换用 `work/excel-vga` 输出目录，其余编译、链接参数相同。程序组将源文件换为 `program-group/OFFGROUP.C`，以 `wlink system windows name OFFGROUP.EXE file OFFGROUP.obj` 链接。两套 Excel 输出均名为 EXCEL.EXE，分别置于 CGA、VGA 安装目录。

### Word

`office-w30/word` 中的 `.patch` 是我们对 Word 的修改，不独立编译。`office-w30/word/source-map.json` 记录原始文件、合并源树和差异文件的对应关系；保留 `CASHMERE`、`OPUS` 的原有构建路径。

原始发布源码位于 `external/word11a-source`；合并源树位于 `external/word11a-current`。补丁采用统一差异格式，保留源码的原字节和换行；编译时使用合并后的完整源树。

Word 编译使用 DOS 下的 `csl`、`im2obj`、MASM 和 LINK5：

```text
csl -nb -r -p -Q -mW -DPCODE -DWIN23 -DCRLF -DWIN -DFAST -Z. C:\CASHMERE\模块.c
im2obj -r -c -p -T@13 模块
masm -Mx -DWIN23 C:\CASHMERE\asm\disp1n.asm;
masm -Mx -DWIN23 C:\CASHMERE\asm\formatn2.asm;
link5 @opus.lnk
```

完整链接需要匹配的 p-code 工具、对象库、`PCODEMAP.OBJ/TXT`、`WINWORD.RES`、DOS 编译配置和链接响应文件。这些生成输入不随源码仓库提供，必须自行准备；只有原始源码和差异文件时，不能直接完成全部 Word 链接。辅助入口为 `office-w30/recipe/support/rebuild_table_candidate.py`。

### 打印和增量资源处理

从项目根目录运行 `python src/main/office-patch/office-w30/printer/pin_printer_args.py`，使用 `external/nasm` 汇编包装代码。它需要指定版本 CEPSON.DRV 预备在 `src/test/native-gb2312/work/build/GB2312-INSTALL/PAYLOAD/SYS`，输出到 `src/test/office-patch/work/printer`。

recipe 下的 Python 脚本直接运行，使用其引用的对象文件、映射表、翻译 JSON 和 DOS 编译配置；`support/patch_print.py` 需要同目录的 `print-source-patch.json`。这些输入不随源码仓库提供，缺少时相应入口无法独立运行。Excel 和程序组可按上文直接编译。
