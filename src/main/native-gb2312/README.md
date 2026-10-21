# Windows 3.0 简体中文术语版与全拼输入法 2.1

## 项目目的

实现原生 GB2312 Windows 3.0a 的简体中文术语、全拼输入法 2.1、中文字库和显示适配。

术语入口为 `build_terminology_variant.py`，包括控制面板、写字板、计算器、鼠标、内存等界面用语。全拼输入法 2.1 的源码为 `PINYIN_NATIVE.C`、`PINYIN_DICT.H`，由 `build_pinyin_ime.py` 编译；字典支持单字和词组。

## 源码结构

| 文件或目录 | 用途 |
| --- | --- |
| `build_terminology_variant.py` | 简体中文术语资源和 Setup 名称转换 |
| `PINYIN_NATIVE.C`、`PINYIN_DICT.H`、`build_pinyin_ime.py` | 全拼输入法 2.1、词典读取与构建入口 |
| `PINYIN.C`、`PYTOGGL.C` | 单字输入辅助实现和输入法切换工具；不作为 2.1 输入法的编译源 |
| `build_ime.py` | 原介质输入法字符表转换 |
| `GBDRAW.C`、`GBHOOK.C`、`GBLIVE.C`、`GBEDIT.C` | 中文绘制、窗口钩子、显示与编辑适配 |
| `GBIMEREG.C`、`GBMSGBX.C`、`GBPMON.C`、`GBPRINT.C` | 输入法注册、消息框、程序管理与打印适配 |
| `ne.py`、`patch_resources.py` | NE 解析及资源转换 |
| `patch_vga_driver.py`、`cffont_gb_bitmap.asm`、`cffont_gb_outline.asm` | GB2312 字体驱动修改 |
| `patch_winnls_ctrlspace.py` | 输入法切换键处理 |
| `build_resources.py`、`paginate_cga_menus.py` | 中文基础资源和 CGA 菜单布局 |
| `build_fonts.py` | CGA / VGA 中文点阵与轮廓字库生成 |
| `build_distribution.py`、`build_setup_media.py`、`build_setup_materials.py` | 系统载荷、Setup 介质与文本配置生成 |
| `render_escp.py`、`tools/make_fat12.py` | ESC/P 输出渲染和 FAT12 镜像生成 |

## 编译方法

外部工具和数据按[依赖说明](../../../README.md#外部依赖与目录结构)准备，以下命令均从项目根目录执行。

### 全拼输入法 2.1

```powershell
python src/main/public-tools/fetch_pinyin_common.py
python src/main/native-gb2312/build_pinyin_ime.py
```

输入为 PINYIN_NATIVE.C、PINYIN_DICT.H、Unihan.zip 和拼音公共数据，使用 Open Watcom `-0 -bt=windows -os` 编译。输出位于 `src/test/native-gb2312/work/build/pinyin21`，包含 PHON.IME、GBPY.DAT、IMEINFO.INI、WINNLS.DLL。

需预备 `src/test/native-gb2312/work/build/ime/IMEINFO.INI` 和 `work/build/patched/WINNLS.DLL` 模板。默认输出是普通输入法；`--diagnostics` 输出诊断版本。

### 简体中文术语资源

```powershell
python src/main/native-gb2312/build_terminology_variant.py
```

输入为 `src/test/native-gb2312/work/build/GB2312-SETUP`，输出为 `work/build/terminology/GB2312-SETUP`。基础介质由 build_setup_media.py 提供；build_resources.py、build_fonts.py、build_setup_materials.py 和 build_distribution.py 分别处理资源、字库、配置及载荷。全拼 2.1 输出须配套用于术语版介质，基础字符表转换不能替代全拼 2.1。

这些入口需要已展开的原版中文系统文件及对应配置。build_distribution.py、build_setup_materials.py 导入的 `test_display` 模块未包含在仓库中，不能直接独立运行。术语脚本的 GBPATH.C 输入须指向 `src/main/install/windows/GBPATH.C`；脚本内的组件根目录路径需相应配置。

### 字体与其他工具

`python src/main/native-gb2312/build_fonts.py` 使用 Unifont、Noto Serif SC、fontTools 和中文介质中的 CompuFont 容器；读取路径及输入版本由脚本的 BASE、NOTO、SOURCE_SHA256 定义。字体驱动修补使用 NASM，CGA 驱动编译见 [cga-driver](../cga-driver/README.md)。

FAT12 工具直接运行：`python src/main/native-gb2312/tools/make_fat12.py 输出.img 文件1 文件2`。先创建输出父目录，输入文件名须符合 DOS 8.3。
