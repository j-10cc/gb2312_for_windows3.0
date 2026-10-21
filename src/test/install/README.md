# 安装器测试

## 项目目的

检查 DOS 安装、配置操作和发布介质。

## 源码结构

| 路径 | 用途 |
| --- | --- |
| `test_install_no_checks.py` | 安装场景和配置结果检查 |
| `dos_runner.py` | DOSBox-X 运行接口 |
| `verify_final_media.py` | ZIP、路径、编码和配套组件检查 |
| `fixtures/release` | 主机端介质对照数据 |

## 编译方法

Python 脚本直接执行。依赖按[根 README](../../../README.md#外部依赖与目录结构)准备。

```powershell
python src/main/install/build.py
python src/test/install/verify_final_media.py
```

安装场景可运行 `python src/test/install/test_install_no_checks.py`，要求 DOSBox-X、两份发布 ZIP 和安装器编译结果，工作目录为 `src/test/install/work/no-checks`。fixtures 中的清单和摘要仅用于主机测试，不是 DOS 安装程序的运行输入。
