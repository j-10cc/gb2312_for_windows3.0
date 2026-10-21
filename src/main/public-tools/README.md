# 公共资源与格式工具

## 项目目的

提供 NE 文件检查、SZDD 解压、字体与拼音数据生成、资源转换和 ZIP 读取。pinyin-phrases.tsv 是自有词组补充；外部词库和字形在 external。

## 源码结构

- [audit_gb2312_stock_strings.py](audit_gb2312_stock_strings.py)
- [build_big5_simplified_fonts.py](build_big5_simplified_fonts.py)
- [build_font.py](build_font.py)
- [build_gb2312_app_fonts.py](build_gb2312_app_fonts.py)
- [build_gb2312_cga.py](build_gb2312_cga.py)
- [build_gb2312_group_ui.py](build_gb2312_group_ui.py)
- [build_gb2312_input_data.py](build_gb2312_input_data.py)
- [build_gb2312_keyboard.py](build_gb2312_keyboard.py)
- [build_gb2312_menu_ui.py](build_gb2312_menu_ui.py)
- [build_gb2312_pinyin.py](build_gb2312_pinyin.py)
- [build_gb2312_resource_ui.py](build_gb2312_resource_ui.py)
- [build_gb2312_shell_ui.py](build_gb2312_shell_ui.py)
- [build_gb2312_ui_data.py](build_gb2312_ui_data.py)
- [build_legible_fonts.py](build_legible_fonts.py)
- [build_wife_b5q.py](build_wife_b5q.py)
- [build_wife_big5_bitmap.py](build_wife_big5_bitmap.py)
- [build_wife_big5_outline.py](build_wife_big5_outline.py)
- [cleanup_setup_test.ps1](cleanup_setup_test.ps1)
- [compare_ne.py](compare_ne.py)
- [expand_szdd.py](expand_szdd.py)
- [fetch_pinyin_common.py](fetch_pinyin_common.py)
- [fix_win30_ne_version.py](fix_win30_ne_version.py)
- [inspect_ne.py](inspect_ne.py)
- [inspect_win16_resources.py](inspect_win16_resources.py)
- [package_big5_simplified.py](package_big5_simplified.py)
- [package_big5_simplified_vga.py](package_big5_simplified_vga.py)
- [package_gb2312_first.py](package_gb2312_first.py)
- [package_io.py](package_io.py)
- [patch_setup_cga.py](patch_setup_cga.py)
- [pinyin-phrases.tsv](pinyin-phrases.tsv)
- [pinyin_common.py](pinyin_common.py)

## 编译方法

Python 工具直接运行，无需编译。例如：

```powershell
python src/main/public-tools/inspect_ne.py 待分析文件.EXE --segments
python src/main/public-tools/build_gb2312_pinyin.py src/test/public-tools/work/GBPY.DAT
```

拼音生成依赖 external/unihan、external/pinyin-common；字体工具按所用入口需要 Pillow、fontTools 或 OpenCC 数据。每个脚本的命令参数以其 argparse 定义为准；带固定路径的介质工具还需要先准备相应展开输入。

[源码总入口](../../README.md)

外部数据的下载和放置方法见[根 README](../../../README.md#外部依赖与目录结构)。build_gb2312_pinyin.py 的命令行入口生成单字词典；全拼 2.1 的单字和词组组合由 [native-gb2312](../native-gb2312/README.md) 的 build_pinyin_ime.py 生成。
