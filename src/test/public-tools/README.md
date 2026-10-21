# 公共工具测试与图像检查

## 项目目的

包含字体验证、字体预览、CGA 转储图像化及测试环境组装工具，不保存原版 Windows 源码。

## 源码结构

- [complete_test_install.py](complete_test_install.py)
- [prepare_driver_test.py](prepare_driver_test.py)
- [preview_font.py](preview_font.py)
- [render_cga_dump.py](render_cga_dump.py)
- [verify_driver_media.py](verify_driver_media.py)
- [verify_font.py](verify_font.py)

## 编译方法

Python 直接运行，例如 `python src/test/public-tools/verify_font.py 字体文件`、`python src/test/public-tools/preview_font.py 字体文件 输出.png`、`python src/test/public-tools/render_cga_dump.py 转储.bin 输出.png`。图像工具需要 Pillow；安装环境组装脚本还需要调用者提供独立的已安装 Windows 目录。

[源码总入口](../../README.md)

工具链和外部输入的下载、目录布局见[根 README](../../../README.md#外部依赖与目录结构)。
