# Office 修改诊断源码

## 项目目的

SCREENTX.C.patch 保存我们对 Word 屏幕文本诊断版本的修改；合并后的 C 文件在 external/office-test-inputs，原始底稿在 external/word11a-source。

## 源码结构

- [SCREENTX.C.patch](SCREENTX.C.patch)

## 编译方法

差异文件不独立编译，使用 external/office-test-inputs/SCREENTX.C。需加入 Word 的 CASHMERE / OPUS p-code 编译环境，以 CSL、IM2OBJ 编译后链接相应模块；完整命令与链接输入要求见 src/main/office-patch/README.md。

[源码总入口](../../README.md)

工具链和外部输入的下载、目录布局见[根 README](../../../README.md#外部依赖与目录结构)。
