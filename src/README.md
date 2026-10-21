# 源码与编译入口

开发代码位于 src/main，测试代码和夹具位于 src/test。外部工具链、供应方源码和原版介质按[根 README 的依赖说明](../README.md#外部依赖与目录结构)准备。

| 组件 | 开发代码 | 测试代码 |
| --- | --- | --- |
| Windows 简体中文术语版与全拼输入法 2.1 | [native-gb2312](main/native-gb2312/README.md) | [测试说明](test/native-gb2312/README.md) |
| 公共资源与格式工具 | [public-tools](main/public-tools/README.md) | [测试说明](test/public-tools/README.md) |
| CGA 显示驱动 | [cga-driver](main/cga-driver/README.md) | [测试说明](test/cga-driver/README.md) |
| Office 外部源码入口 | [office](main/office/README.md) | [测试说明](test/office/README.md) |
| Word / Excel 中文适配 | [office-patch](main/office-patch/README.md) | [测试说明](test/office-patch/README.md) |
| Windows / Office 安装器 | [install](main/install/README.md) | [测试说明](test/install/README.md) |

编译命令从项目根目录执行。Python 工具直接运行；DOS / Win16 C 使用 Open Watcom，汇编使用 NASM 或 DDK 内的 MASM。安装辅助程序的统一构建入口为 `python src/main/install/build.py`。其他组件的输入和输出路径见各自 README。

工作文件位于 `src/test/<组件>/work`，发布安装包位于 release。完整系统和 Word 链接所需的额外模板、资源及对象输入在对应组件中列明。
