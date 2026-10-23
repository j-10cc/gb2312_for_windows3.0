# GB2312 CGA 显示驱动

## 项目目的

为 Windows 3.0 CGA 显示提供 GB2312 双字节绘制及配套系统字体。

## 源码结构

| 文件 | 用途 |
| --- | --- |
| `chcga_overlay.inc` | 中文双字节字符绘制实现 |
| `build_chcga_probe.py` | 将覆盖实现、中文点阵接入 DDK 驱动源码 |
| `build_cga_driver.py` | 执行 DDK 汇编、链接、资源绑定，输出 CGA.DRV |
| `build_cga_system_font.py` | 在 FON 容器中生成 12 像素 CGA 系统字体 |
| `make_dispatch_driver.py` | 生成驱动分派适配代码 |

## 编译方法

按[依赖说明](../../../README.md#外部依赖与目录结构)准备 Windows 3.0 DDK 和 DOSBox-X；DDK 放在 external/win30ddk，参考源码放在 external/win31igdrv。

从项目根目录执行：

```powershell
python src/main/cga-driver/build_cga_system_font.py
python src/main/cga-driver/build_cga_driver.py
```

系统字体输入为 `src/test/native-gb2312/work/build/expanded/chinese/EGASYS.FON` 和 DDK 的 `fonts/system/ega/egasys.fnt`。驱动输入还包括 `work/build/fonts/CHCGA12.FNT`、`CHCGA10.FNT`、`CHCGA08.FNT`；字体生成方法见 [native-gb2312](../native-gb2312/README.md)。

脚本在 DOSBox-X 内调用 DDK 的 MASM、LINK4 和 RC。字体输出至 `work/build/fonts/CGAS12.FON`，驱动输出至 `work/build/driver/CGA.DRV`。添加 `--trace` 可生成独立诊断驱动。

系统字体的 `A1–FE` 字节宽度固定为 8 像素，与覆盖绘制的每汉字 16 像素步进一致；ASCII 宽度和点阵不变。不能直接用未修正的英文 EGA 字体宽度表替代，否则程序管理器可能按较小的测量宽度裁掉标题末字。原因和验证见 [CGA 图标标题修复记录](../../../docs/review/cga-icon-captions.md)，测试入口见 [CGA 探针](../../test/cga-driver/README.md)。
