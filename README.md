# Windows 3.0 简体中文支持

本项目提供采用简体中文术语的原生 GB2312 Windows 3.0a、全拼输入法 2.1，以及 Word 1.1a / Excel 2.1d 中文适配。

- [源码及编译入口](src/README.md)：开发代码在 `src/main`，测试代码和数据在 `src/test`。
- [外部依赖与目录结构](#外部依赖与目录结构)：下载来源、文件布局及构建所需输入。
- [使用手册](docs/README.md)：安装、输入法、Word 和 Excel 使用说明。
- `release/W30SC21.ZIP`：Windows 简体中文术语版，包含全拼输入法 2.1。
- `release/GB30SC21.ZIP`：Word / Excel 简体中文安装包，支持 DOS 5.0 和 8086。

`src/main/native-gb2312/build_terminology_variant.py` 负责简体中文术语转换；`build_pinyin_ime.py` 以 `PINYIN_NATIVE.C`、`PINYIN_DICT.H` 构建全拼输入法 2.1。基础资源和字符表转换工具也是这个组件的构建输入。

## 许可证

本项目原创代码、文档、资源及其构建成果采用[非商业研究、实验与教育许可（禁止再分发）](LICENSE)，与 Word 1.1a 原许可采用同等的用途与再分发限制：仅限非商业研究、实验和教育，禁止向第三方发布或再分发原件及衍生作品，包括源码、补丁、二进制和安装包。

Word 1.1a 及其他第三方内容继续适用其原许可；本项目许可证不额外授予第三方内容的分发权。这是附带限制的源码可用许可，并非允许自由再分发的开源许可。

## 外部依赖与目录结构

`external/` 由 Git 忽略。克隆仓库后，按所需组件准备以下工具和数据；本节随仓库提供，不依赖 external 中的 README。

### 按构建目标准备

| 构建目标 | 必需输入 |
| --- | --- |
| Windows / Office 安装辅助程序 | Python 3.11 或以上、Open Watcom 2.0 |
| Excel 中文适配、OFFGROUP 程序组工具 | Open Watcom 的 Win16 头文件和 16 位 Windows 库 |
| 全拼输入法 2.1 | Open Watcom、Unihan 16.0.0、Jieba 与词组读音数据、IMEINFO.INI 和 WINNLS.DLL 模板 |
| 中文字体、Windows 资源和介质 | Windows 原版介质、Unifont、OpenCC 字符映射、Noto Serif SC、fontTools、Pillow，以及组件文档列出的展开文件和配置输入 |
| CGA 显示驱动 | Windows 3.0 DDK、DOSBox-X、中文点阵字库；字体驱动修补另需 NASM |
| Word 源码编译和链接 | Word 1.1a 原始源码、本项目差异、DOS p-code 工具、匹配的对象库、映射和资源文件 |

### 工具链和 Python 库

| 依赖 | 获取入口 | 本地位置与要求 |
| --- | --- | --- |
| Open Watcom 2.0 | [官方发布页](https://github.com/open-watcom/open-watcom-v2/releases) | 安装或解包至 `external/open-watcom`；须包含 `binnt64/wcc.exe`、`wcl.exe`、`wlink.exe`、`wrc.exe`、`wdump.exe`，以及 `h/win`、`lib286/win`、`lib286/dos` |
| NASM 2.16.03 | [官方版本目录](https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/) | Windows 包解压后使 `nasm.exe`、`ndisasm.exe` 位于 `external/nasm/nasm-2.16.03` |
| DOSBox-X | [官方网站](https://dosbox-x.com/) | Windows MinGW SDL2 包，保持配套 DLL；脚本读取 `external/dosbox-x/mingw-build/mingw-sdl2/dosbox-x.exe` |
| fontTools、Pillow | [fontTools](https://pypi.org/project/fonttools/)、[Pillow](https://pypi.org/project/Pillow/) | 安装到运行构建脚本的 Python 环境；也可放在 `external/pydeps` 并加入 PYTHONPATH |

在项目根目录安装 Python 依赖的一种方式：

```powershell
python -m pip install --target external/pydeps fonttools==4.66.1 Pillow==12.3.0
$env:PYTHONPATH = "$((Get-Location).Path)/external/pydeps;$env:PYTHONPATH"
```

### 字体、字符映射和拼音数据

| 依赖 | 获取入口与版本 | 文件放置方法 |
| --- | --- | --- |
| GNU Unifont 14.0.01 | [官方源码归档](https://unifoundry.com/pub/unifont/unifont-14.0.01/) | 将源码包内容放入 `external/unifont`，保留 `font/plane00/unifont-base.hex`、`font/plane00/wqy.hex` 及许可文件 |
| Unicode Unihan 16.0.0 | [Unicode 16.0 数据目录](https://www.unicode.org/Public/16.0.0/ucd/) | 下载其中的 Unihan.zip，保存为 `external/unihan/Unihan.zip`，无需解压 |
| Jieba v0.42.1 | [上游源码](https://github.com/fxsjy/jieba/tree/v0.42.1) | `jieba/dict.txt` 保存为 `external/pinyin-common/jieba-dict.txt`；LICENSE 保存为 `jieba-LICENSE` |
| phrase-pinyin-data v0.19.0 | [上游源码](https://github.com/mozillazg/phrase-pinyin-data/tree/v0.19.0) | `pinyin.txt` 保存为 `external/pinyin-common/phrase-pinyin.txt`；LICENSE 保存为 `phrase-LICENSE` |
| OpenCC 字符映射 | [上游源码](https://github.com/BYVoid/OpenCC)，提交 `3ac34aa439a9908dd49fa92b5174b46314787ac2` | `data/dictionary/TSCharacters.txt` 与 LICENSE 放入 `external/licenses/opencc` |
| Noto Serif SC 可变字体 | [Google Fonts 字体目录](https://github.com/google/fonts/tree/main/ofl/notoserifsc) | 构建脚本读取 `C:/Windows/Fonts/NotoSerifSC-VF.ttf`；可将下载的可变字体另存为此名，或调整脚本的 NOTO 路径。文件版本须符合 `build_fonts.py` 的 SOURCE_SHA256 定义 |
| CMEX 字体 | [上游源码](https://github.com/bluebat/cmexfonts) | 放入 `external/cmexfonts`，保留 `cmex16m.bdf`、`cmex24m.bdf`、LICENSE；供相关字体参考与工具使用 |

拼音公共数据也可从项目根目录执行以下命令获取，文件版本由脚本指定：

```powershell
python src/main/public-tools/fetch_pinyin_common.py
```

许可文件按使用组件放在 `external/licenses`：Unifont 的 COPYING 对应 `UNIFONT-COPYING.txt`，字体 OFL 对应 `OFL-1.1.txt`，[Unicode 许可](https://www.unicode.org/license.txt)对应 `UNICODE-LICENSE.txt`。拼音数据的许可证保留在 `pinyin-common` 内。

### Windows / Office 原版介质和源码

| 输入 | 位置与内容 |
| --- | --- |
| Windows 3.0a 英文介质 | `external/media/windows/windows30a`，须能读取 SETUP.INF、CGA 驱动、字体及 Setup 所需文件 |
| Windows 3.0a 繁体中文介质 | `external/media/windows/windows30a-tc`，提供中文资源、CompuFont 字体及输入法组件 |
| Windows 3.2 中文介质 | `external/media/windows/windows32`，供相关中文资源和字体输入使用 |
| Word 1.1a / Excel 2.1d 介质 | `external/media/office/word11a`、`external/media/office/excel21d` |
| Windows 3.0 DDK | `external/win30ddk`；必须包含 `display/1plane/bw/cgaherc/cga`、`fonts/system/ega/egasys.fnt`、`include`、`lib/c51` 和 `tools`。工具中需有 MASM、LINK4、RC、RCPP、EXE2BIN |
| 参考驱动 | 从 [win31igdrv 上游](https://github.com/joncampbell123/win31igdrv) 获取，放入 `external/win31igdrv`，保留 WINDOWS、DDK 等目录 |
| Word 1.1a 源码 | 从 [Computer History Museum 发布页](https://computerhistory.org/blog/microsoft-word-for-windows-1-1a-source-code/) 获取，原 ZIP 放入 `external/word11a-source`，解压目录为 `tree/Word 1.1a CHM Distribution`，其下为 Opus、OpusEtAl、OpusProg |

Windows / Office 安装介质和 Windows 3.0 DDK 需自行从所持介质准备；这里没有可核实的原厂公开下载入口。参考驱动仓库中的 Windows 3.1 DDK 不能直接视作上述 Windows 3.0 DDK 的同目录替代品。

Word 合并源树使用 `external/word11a-current/CASHMERE`、`OPUS` 布局。按 `src/main/office-patch/office-w30/word/source-map.json` 的 `original` 字段复制原始源码至 `final` 路径，再应用对应 `patch` 差异；`original` 为空的条目由新增文件差异提供。`external/office-recipe-inputs` 和 `office-test-inputs` 同样由原始 Word 模块与相应差异准备，不是另一个公开下载包。具体编译输入见 [Office 组件说明](src/main/office-patch/README.md)。

### 目录示例

```text
external/
  open-watcom/{binnt64,h,lib286}/
  nasm/nasm-2.16.03/{nasm.exe,ndisasm.exe}
  dosbox-x/mingw-build/mingw-sdl2/dosbox-x.exe
  pydeps/{fontTools,PIL}/
  unifont/font/plane00/{unifont-base.hex,wqy.hex}
  unihan/Unihan.zip
  pinyin-common/{jieba-dict.txt,phrase-pinyin.txt,jieba-LICENSE,phrase-LICENSE}
  licenses/{OFL-1.1.txt,UNICODE-LICENSE.txt,UNIFONT-COPYING.txt}
  licenses/opencc/{TSCharacters.txt,LICENSE}
  cmexfonts/{cmex16m.bdf,cmex24m.bdf,LICENSE}
  media/windows/{windows30a,windows30a-tc,windows32}/
  media/office/{word11a,excel21d}/
  win30ddk/{display,fonts,include,lib,tools}/
  win31igdrv/{WINDOWS,DDK}/
  word11a-source/tree/Word 1.1a CHM Distribution/{Opus,OpusEtAl,OpusProg}/
  word11a-current/{CASHMERE,OPUS}/
  office-recipe-inputs/
  office-test-inputs/
  disassembly/
```

原版压缩介质需要先展开到相应组件读取的工作目录。完整 Windows 介质组装还依赖配置辅助模块；Word 链接依赖匹配的对象库、映射和资源。仅下载上述公开依赖不等于可以直接执行所有组装入口，具体要求以各组件 README 为准。`disassembly` 是参考材料，不是安装器或输入法编译的必需输入。
