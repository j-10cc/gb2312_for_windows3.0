"""Generate translations tied to original Win16 resource strings."""

from __future__ import annotations

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]


from pathlib import Path

from inspect_win16_resources import resources, strings


ROOT = _LAYOUT_ROOT
ENGLISH = ROOT / "src/test/native-gb2312/work/build/expanded/english"
TARGET = ROOT / "src/test/native-gb2312/gb2312_first/GBRES.H"

CONTROL_ICONS = {
    48: ("Color", "颜色"),
    49: ("Printers", "打印机"),
    50: ("Fonts", "字体"),
    51: ("International", "国际设置"),
    52: ("Ports", "端口"),
    53: ("Keyboard", "键盘"),
    54: ("Mouse", "鼠标"),
    55: ("Date/Time", "日期时间"),
    56: ("Desktop", "桌面"),
    57: ("Sound", "声音"),
    58: ("Network", "网络"),
    59: ("386 Enhanced", "386 增强"),
}

DIALOG_LABELS = {
    "Cancel": "取消", "OK": "确定",
    "File&name:": "文件名", "Directory:": "目录", "&Files:": "文件",
    "&Directories:": "目录", "&Make Backup": "建立备份",
    "&Text Only": "纯文本", "&Convert": "转换", "&No Conversion": "不转换",
    "&Copies:": "份数", "Pages:": "页码", "&All": "全部",
    "&From:": "从", "&To:": "到", "&Draft Quality": "草稿质量",
    "Confirm Page &Breaks": "确认分页", "&Up": "向上", "&Down": "向下",
    "&Confirm": "确认", "&Keep": "保留", "&Remove": "删除",
    "&Printer:": "打印机", "&Setup...": "设置",
    "&Find What:": "查找内容", "&Whole Word": "全字匹配",
    "&Match Upper/Lowercase": "区分大小写", "Find &Next": "查找下一个",
    "Change &To:": "替换为", "&Change": "替换",
    "&Page Number:": "页码", "Font &Name:": "字体名",
    "&Sizes:": "字号", "&Left Indent:": "左缩进",
    "&Right Indent:": "右缩进", "&First Line:": "首行",
    "&Positions:": "位置", "&Decimal:": "小数位",
    "&Warning Beep": "警告音", "Color &Schemes": "配色方案",
    "&Basic Colors:": "基本颜色", "&Custom Colors:": "自定义颜色",
    "&Default Printer": "默认打印机", "Installed &Printers:": "已安装打印机",
    "Installed &Fonts:": "已安装字体", "Sample of Font": "字体示例",
    "Key &Repeat Rate": "按键重复速度", "&Test Typematic:": "测试按键重复",
    "&Mouse Tracking Speed": "鼠标移动速度",
    "&Double Click Speed": "双击速度", "&Country:": "国家",
    "&Language:": "语言", "&Keyboard Layout:": "键盘布局",
    "&Measurement:": "度量单位", "&Date Format": "日期格式",
    "&Time Format": "时间格式", "&Number Format": "数字格式",
    "&Device Contention": "设备冲突", "Scheduling": "任务调度",
    "&Date": "日期", "&Time": "时间", "&Center": "居中",
    "&Tile": "平铺", "&Icon Spacing:": "图标间距",
    "&Command Line:": "命令行", "&Description:": "说明",
    "&Group File:": "群组文件", "&To Group:": "目标群组",
    "Program &Group": "程序群组", "Program &Item": "程序项目",
    "Run &Minimized": "最小化运行", "&Save Changes": "保存更改",
    "Current Selection:": "当前选择", "From Program Group:": "来源群组",
    "&File Name:": "文件名", "Change &Icon...": "更换图标",
    "&Browse...": "浏览", "&Height:": "高度", "&Width:": "宽度",
    "&Scaling:": "缩放", "&Number of copies:": "份数",
    "&Use Printer Resolution": "使用打印机分辨率",
    "&Monochrome bitmap": "单色位图", "&16 Color bitmap": "16 色位图",
    "&256 Color bitmap": "256 色位图", "Black and White": "黑白",
    "Colors:": "颜色", "Height:": "高度", "Width:": "宽度",
    "Planes:": "平面数", "&Red": "红", "&Green": "绿",
    "&Blue": "蓝", "&Default": "默认", "&Whole": "全部",
    "&Bottom:": "下", "&Footer:": "页脚", "&Header:": "页眉",
    "&Left:": "左", "&Right:": "右", "&Top:": "上",
    "&Hour Format:": "小时格式", "&Interval:": "间隔",
    "&Starting Time:": "开始时间", "&Special Time:": "特殊时间",
    "&Show Date:": "显示日期", "&Read Only": "只读",
    "&Go To:": "转到", "&Find:": "查找", "&Index Line:": "索引行",
    "&Number:": "号码", "&Add:": "添加", "&Port": "端口",
    "&Baud Rate": "波特率", "&Use Prefix": "使用前缀",
    "&Application Shortcut Key:": "应用快捷键",
    "&Background Priority:": "后台优先级",
    "&Foreground Priority:": "前台优先级",
    "&Program Filename:": "程序文件名",
    "&Start-up Directory:": "启动目录",
    "&Video Memory:": "视频内存", "&Video Mode:": "视频模式",
    "&Optional Parameters:": "可选参数",
    "&Close Window on Exit": "退出时关闭窗口",
    "&Detect Idle Time": "检测空闲时间",
    "&Network Queue:": "网络队列",
    "&Print Net Jobs Direct": "直接打印网络任务",
    "&Update Network Display": "刷新网络显示",
    "&Relative to:": "相对于", "&Playback": "播放",
    "Record &Mouse:": "录制鼠标", "Shortcut &Key": "快捷键",
    "&Find What:": "查找内容", "&Annotation:": "注释",
    "&Bookmark Name:": "书签名称", "&Go To Bookmark:": "转到书签",
    "&Search For:": "搜索内容", "&Delete": "删除",
    "&Arrange Icons": "排列图标", "&Cascade": "层叠",
    "&End Task": "结束任务", "&Switch To": "切换到",
    "Window &Title:": "窗口标题", "Memory Requirements:": "内存需求",
    "KB &Required": "所需 KB", "KB &Desired": "建议 KB",
    "Display Usage:": "显示方式", "F&ull Screen": "全屏",
    "&Windowed": "窗口", "Execution:": "运行方式",
    "&Background": "后台", "&Exclusive": "独占",
    "&Advanced...": "高级", "Multitasking Options": "多任务选项",
    "Memory Options": "内存选项", "EMS Memory:": "EMS 内存",
    "XMS Memory:": "XMS 内存", "KB &Limit": "上限 KB",
    "Loc&ked": "锁定", "KB Re&quired": "所需 KB",
    "KB L&imit": "上限 KB", "L&ocked": "锁定",
    "Uses &High Memory Area": "使用高端内存区",
    "Lock Applicatio&n Memory": "锁定应用内存",
    "Display Options": "显示选项", "Text": "文本",
    "Low Graphics": "低图形", "High Graphics": "高图形",
    "Monitor Por&ts:": "监视端口",
    "Graphics/Multiple Text": "图形/多文本",
    "Directly Modifies:": "直接修改",
    "COM&1": "串口 1", "COM&2": "串口 2",
    "COM&3": "串口 3", "COM&4": "串口 4",
    "No Screen &Exchange": "不交换屏幕",
    "Prevent Program S&witch": "禁止程序切换",
    "Reserve Shortc&ut Keys:": "保留快捷键",
}

DIALOG_LABELS.update({
    "Create Directory": "建立目录",
    "Current directory is X": "当前目录为 ",
    "&Name:": "名称", "Serial &Ports:": "串行端口",
    "&Print:": "打印文件", "Search &For:": "搜索内容",
    "Search &Entire Disk": "搜索整个磁盘",
    "&Move": "移动", "&From:": "来源", "De&lete:": "删除",
    "&Hidden": "隐藏", "&Archive": "存档", "&System": "系统",
    "&Save Settings": "保存设置", "&Disk:": "磁盘",
    "&Copy...": "复制", "&Label:": "卷标",
    "&High Capacity": "高容量", "&Make System Disk": "制作系统盘",
    "&Drive Letter:": "驱动器号", "&Network Path:": "网络路径",
    "Pass&word:": "密码", "&Add to Previous List": "加入历史列表",
    "&Connect": "连接", "&Previous...": "历史记录",
    "Network &Paths:": "网络路径", "&Select": "选择",
    "Last &Modification Date": "最后修改日期",
    "Last Modification &Time": "最后修改时间",
    "&File Flags": "文件属性", "Set System &Default": "设为系统默认",
    "&Size": "大小", "&Type": "类型", "Si&ze": "大小",
    "&Set System Default": "设为系统默认",
    "&Directories": "目录", "&Programs": "程序",
    "Docu&ments": "文档", "&Other Files": "其他文件",
    "Show &Hidden/System Files": "显示隐藏和系统文件",
    "Confirm on &Delete": "删除时确认",
    "Confirm on &Subtree Delete": "删除子树时确认",
    "Confirm on &Replace": "覆盖时确认",
    "Confirm on &Mouse Operation": "鼠标操作时确认",
})

# Static captions and messages from the original modules' STRING and MENU
# resources are also passed through ResourceLabel at runtime.
DIALOG_LABELS.update({
    "Copy Program Item": "复制程序项目",
    "Group File Error": "群组文件错误",
    "Group Properties Error": "群组属性错误",
    "Icon Extraction Error": "提取图标失败",
    "Application Execution Error": "程序运行错误",
    "Extremely Low on Memory": "内存严重不足",
    "Invalid Path": "路径无效",
    "Groups": "群组",
    "Real Mode": "实模式",
    "Standard Mode": "标准模式",
    "386 Enhanced Mode": "386 增强模式",
    "Microsoft Windows": "微软 Windows",
    "Network Path Specified": "指定了网络路径",
    "Removable Path Specified": "指定了可移动路径",
    "Cannot find any icons in this file": "文件中没有图标",
    "No association exists for the specified file.": "指定文件没有关联程序",
    "This program group file is already loaded.": "群组文件已经加载",
    "This program group already contains the maximum number of items.":
        "群组中的项目数已达上限",
    "The specified path is invalid.": "指定路径无效",
    "This will end your Windows session.": "即将结束 Windows 会话",
    "Control Panel - ": "控制面板 - ",
    "Color": "颜色", "Fonts": "字体", "Ports": "端口",
    "Mouse": "鼠标", "Desktop": "桌面",
    "Active": "活动", "Inactive": "非活动",
    "Active Border": "活动边框", "Inactive Border": "非活动边框",
    "Active Title Bar": "活动标题栏",
    "Inactive Title Bar": "非活动标题栏",
    "Application Workspace": "应用程序工作区",
    "Window Background": "窗口背景",
    "Window Frame": "窗口边框",
    "Window Text": "窗口文字",
    "Title Bar Text": "标题栏文字",
    "Menu Bar": "菜单栏", "Menu Text": "菜单文字",
    "Scroll Bars": "滚动条",
    "Sizing Grid": "调整网格",
    "Icons": "图标", "Pattern": "图案", "Patterns": "图案",
    "Wallpaper": "壁纸", "WallPaper": "壁纸",
    "Unlisted Pattern": "未列出的图案",
    "Unlisted printer": "未列出的打印机",
    "Windows Default": "Windows 默认",
    "No printers installed": "未安装打印机",
    "No fonts installed": "未安装字体",
    "No default printer": "没有默认打印机",
    "Font already installed": "字体已经安装",
    "Add Font Files": "添加字体文件",
    "Add unlisted printer": "添加未列出的打印机",
    "Save Scheme": "保存配色方案",
    "Custom Color Selector": "自定义颜色选择器",
    "Desktop - Edit Pattern": "桌面 - 编辑图案",
    "International - Currency Format": "国际设置 - 货币格式",
    "International - Date Format": "国际设置 - 日期格式",
    "International - Number Format": "国际设置 - 数字格式",
    "International - Time Format": "国际设置 - 时间格式",
    "Printers - Configure": "打印机 - 配置",
    "Printers - Network Connections": "打印机 - 网络连接",
    "Ports - Settings": "端口 - 设置",
    "Date & Time": "日期和时间",
    "Short Date Format": "短日期格式",
    "Long Date Format": "长日期格式",
    "Unable to connect": "无法连接",
    "Operation cancelled": "操作已取消",
    "Insufficient disk space": "磁盘空间不足",
    "Insufficient memory": "内存不足",
    "Cannot save new settings": "无法保存新设置",
    "Unable to create file": "无法创建文件",
    "Root directory": "根目录",
    "Search Results": "搜索结果",
    "Directory is empty": "目录为空",
    "No Files Found": "未找到文件",
    "No matching files were found.": "未找到匹配文件",
    "File Type": "文件类型",
    "Access Denied": "拒绝访问",
    "Out of Memory": "内存不足",
    "Cannot Print": "无法打印",
    "Copying Diskette": "正在复制软盘",
    "Formatting Diskette": "正在格式化软盘",
    "Format Complete": "格式化完成",
    "File Search Error": "文件搜索错误",
    "File System Error": "文件系统错误",
    "Network Error": "网络错误",
    "Previous Network Connections": "以前的网络连接",
    "Connect Network Drive": "连接网络驱动器",
    "Disconnect Network Drive": "断开网络驱动器",
    "Initializing Drive...": "正在初始化驱动器",
    "Printing File...": "正在打印文件",
    "Copying...": "正在复制",
    "Moving...": "正在移动",
    "Too Many Files": "文件过多",
})

# Remaining short labels and complete, unformatted messages from the stock
# Program Manager, Control Panel and File Manager resource tables.
DIALOG_LABELS.update({
    "Cannot find file; check to ensure the path and filename are correct.":
        "找不到文件，请检查路径和文件名",
    "Cannot rename the program group information file.":
        "无法重命名程序群组信息文件",
    "Cannot start more than one copy of the specified program.":
        "指定程序不能同时运行多个副本",
    "Close an application and try again.": "请关闭一个程序后重试",
    "Free Expanded Memory......": "可用扩展内存",
    "Free Memory......": "可用内存",
    "Free System Resources...": "可用系统资源",
    "Real Mode (Large Frame EMS)": "实模式（大页框 EMS）",
    "Real Mode (Small Frame EMS)": "实模式（小页框 EMS）",
    "SMARTDrive Using......": "SMARTDrive 占用",
    "The specified application is not a Windows or DOS program.":
        "指定的程序不是 Windows 或 DOS 程序",
    "This application requires a newer version of Microsoft Windows.":
        "此程序需要更新版本的 Windows",
    "This application requires Standard or Enhanced Mode Windows.":
        "此程序需要标准模式或增强模式 Windows",
    "Too many other files are currently in use.": "打开的文件过多",
    "&Border Width:": "边框宽度", "&Current": "当前",
    "&Data": "数据", "&Decimal Digits:": "小数位数",
    "&Decimal Separator:": "小数分隔符",
    "&Device Not Selected:": "未选设备",
    "&Disconnect": "断开连接", "&Flow Control": "流量控制",
    "&Granularity:": "粒度", "&Hue:": "色调",
    "&Idle (in sec.)": "空闲秒数", "&Leading Zero:": "前导零",
    "&List of Printers:": "打印机列表", "&Lum:": "亮度",
    "&Minimum Timeslice (in msec):": "最短时间片（毫秒）",
    "&Month Leading Zero (02 vs. 2)": "月份前导零",
    "&Negative:": "负数", "&Network Printer Connections:": "网络打印机连接",
    "&Order:": "顺序", "&Parity": "奇偶校验",
    "&Sat:": "饱和度", "&Status": "状态", "&Stop": "停止",
    "&Swap Left/Right Buttons": "交换左右按钮",
    "&Symbol:": "符号", "&Transmission Retry:": "重试传输",
    "(None)": "无", "&Add Printer >>": "添加打印机",
    "&Century (1990 vs. 90)": "四位年份",
    "&Day Leading Zero (07 vs. 7)": "日期前导零",
    "&Exclusive in Foreground": "前台独占",
    "C&urrency Format": "货币格式",
    "Cannot Change Windows Default": "无法更改 Windows 默认值",
    "Color &Palette >>": "调色板",
    "Cursor Blink &Rate": "光标闪烁速度",
    "D&ecimal Digits:": "小数位数",
    "Driver &Files:": "驱动文件", "Driver &Name:": "驱动名称",
    "Font &Files:": "字体文件", "Font File&name:": "字体文件名",
    "Font Sample": "字体示例", "Hardware": "硬件",
    "Installed &Printers:": "已安装打印机",
    "List &Separator:": "列表分隔符",
    "Maximum number of printers already installed":
        "已达到打印机安装数量上限",
    "O&rder:": "顺序", "Sample": "示例",
    "Save this color scheme as": "将此配色方案另存为",
    "Screen &Element:": "屏幕元素", "Short Date Separator cannot be empty":
        "短日期分隔符不能为空",
    "Slow": "慢", "Fast": "快", "Space": "空格",
    "Symbol &Placement:": "符号位置",
    "Timeouts (seconds)": "超时（秒）",
    "Windows in &Background:": "后台 Windows",
    "Windows in &Foreground:": "前台 Windows",
    "Cannot copy file to itself": "不能将文件复制到自身",
    "Currency symbol cannot be empty": "货币符号不能为空",
    "Date separator cannot be empty": "日期分隔符不能为空",
    "Decimal separator cannot be empty": "小数分隔符不能为空",
    "Default printer cannot be inactive": "默认打印机不能停用",
    "Invalid background value": "背景值无效",
    "Invalid border width entry": "边框宽度无效",
    "Invalid decimal digit entry": "小数位数无效",
    "Invalid decimal entry": "小数值无效",
    "Invalid delay entry": "延时值无效",
    "Invalid foreground value": "前景值无效",
    "Invalid Grid Granularity entry": "网格粒度无效",
    "Invalid Icon Spacing entry": "图标间距无效",
    "Invalid minimum slice value": "最短时间片无效",
    "Invalid network username": "网络用户名无效",
    "Insufficient memory to display all fonts": "内存不足，无法显示全部字体",
    "The local device name is invalid.": "本地设备名无效",
    "The network driver does not support this function.":
        "网络驱动程序不支持此功能",
    "This keyboard cannot change its speed.": "此键盘无法调节速度",
    "Unable to initialize ports": "无法初始化端口",
    "Unable to specify the number of copies.": "无法指定份数",
    "Cannot find path; check to ensure the path is correct.":
        "找不到路径，请检查路径",
    "Cannot remove the current directory": "无法删除当前目录",
    "Cannot rename to a different directory": "无法跨目录重命名",
    "Confirm Mouse Operation": "确认鼠标操作",
    "Copy Diskette Error": "复制软盘错误",
    "Copying system files": "正在复制系统文件",
    "Creating root directory": "正在建立根目录",
    "Destination is a subtree of the source.": "目标目录位于源目录内",
    "Destination is not a directory.": "目标不是目录",
    "Disconnect Drive": "断开驱动器",
    "Do you want to close the File Manager?": "要关闭文件管理器吗？",
    "Do you want to format another diskette?": "要格式化另一张软盘吗？",
    "Error Copying File": "复制文件错误",
    "Error Deleting File": "删除文件错误",
    "Error Moving File": "移动文件错误",
    "Error Renaming File": "重命名文件错误",
    "Exit File Manager": "退出文件管理器",
    "File Manager is already running.": "文件管理器已经运行",
    "Format command cancelled": "已取消格式化命令",
    "Format Diskette Error": "格式化软盘错误",
    "Formatting destination diskette": "正在格式化目标软盘",
    "Formatting will erase ALL data from your diskette.":
        "格式化将清除软盘上的全部数据",
    "Make System Diskette command cancelled": "已取消制作系统盘",
    "No association exists for this data file.":
        "此数据文件没有关联程序",
    "Now copying system files": "正在复制系统文件",
    "Now formatting diskette": "正在格式化软盘",
    "Reading the source disk": "正在读取源磁盘",
    "Select the destination diskette.": "请选择目标软盘",
    "Select the diskette to disconnect.": "请选择要断开的软盘",
    "Select the diskette to format.": "请选择要格式化的软盘",
    "Source and destination are the same.": "源和目标相同",
    "Source and destination drives are incompatible":
        "源驱动器和目标驱动器不兼容",
    "System Diskette Error": "系统软盘错误",
    "The current drive does not contain system files.":
        "当前驱动器没有系统文件",
    "The file to be printed cannot be found.": "找不到要打印的文件",
    "This drive contains the Windows system files and cannot be disconnected.":
        "此驱动器包含 Windows 系统文件，不能断开",
    "This operation will erase ALL data from the destination diskette.":
        "此操作将清除目标软盘上的全部数据",
    "Unable to add system files to this diskette": "无法向此软盘添加系统文件",
    "Unable to change attributes": "无法更改属性",
    "Unable to connect to network drive": "无法连接网络驱动器",
    "Unable to copy diskette": "无法复制软盘",
    "Unable to create directory": "无法建立目录",
    "Unable to disconnect network drive": "无法断开网络驱动器",
    "Unable to format diskette": "无法格式化软盘",
    "Unable to label disk": "无法设置卷标",
    "Unable to read entire directory.  Only a partial listing will be displayed.":
        "无法读取整个目录，仅显示部分文件",
    "View Other": "查看其他", "You cannot disconnect the current drive.":
        "不能断开当前驱动器",
    "You cannot format the current drive.": "不能格式化当前驱动器",
    "You must first select a diskette drive.": "请先选择软盘驱动器",
})

DIALOG_LABELS.update({
    "&Separator:": "分隔符", "1&2 hour": "12 小时制",
    "2&4 hour": "24 小时制", "1000 &Separator:": "千位分隔符",
    "A buffer error has occurred.": "缓冲区错误",
    "A handle error has occurred.": "句柄错误",
    "A job error has occurred.": "作业错误",
    "A network error has occurred.": "网络错误",
    "A pointer error has occurred.": "指针错误",
    "A print job error has occurred.": "打印作业错误",
    "A queue error has occurred.": "队列错误",
    "A value error has occurred.": "数值错误",
    "Access to the network device is denied": "网络设备拒绝访问",
    "Already connected.": "已经连接",
    "Already running Control Panel.": "控制面板已经运行",
    "An unknown network error has occurred.": "发生未知网络错误",
    "Do you want to use the current driver or install a new driver?":
        "使用当前驱动程序，还是安装新驱动程序？",
    "Drive door open": "驱动器舱门未关闭",
    "EMS detected.  Reboot Windows to see new background Wallpaper.":
        "检测到 EMS，请重新启动 Windows 以显示新墙纸",
    "English": "英语", "Even": "偶校验", "Odd": "奇校验",
    "Metric": "公制", "None": "无", "Mark": "标记位",
    "Xon / Xoff": "软件流控", "Unnamed Disk": "未命名磁盘",
    "Spooler currently in use": "后台打印程序正在使用",
    "The network driver does not support connecting to network printer queues.":
        "网络驱动程序不支持连接网络打印队列",
    "Apr": "四月", "April": "四月",
    "Aug": "八月", "August": "八月",
    "Dec": "十二月", "December": "十二月",
    "Feb": "二月", "February": "二月",
    "Jan": "一月", "January": "一月",
    "Jul": "七月", "July": "七月",
    "Jun": "六月", "June": "六月",
    "Mar": "三月", "March": "三月",
    "May": "五月", "Nov": "十一月", "November": "十一月",
    "Oct": "十月", "October": "十月",
    "Sep": "九月", "September": "九月",
    "Fri": "周五", "Friday": "星期五",
    "Mon": "周一", "Monday": "星期一",
    "Sat": "周六", "Saturday": "星期六",
    "Sun": "周日", "Sunday": "星期日",
    "Thu": "周四", "Thursday": "星期四",
    "Tue": "周二", "Tuesday": "星期二",
    "Wed": "周三", "Wednesday": "星期三",
    "Are you sure that you want to continue?": "确定继续吗？",
    "Are you sure that you want to format the diskette in":
        "确定格式化此驱动器中的软盘吗：",
    "Current directory is C": "当前目录为 C",
    "Current directory is N": "当前目录为 N",
    "Current directory is U": "当前目录为 U",
    "Details": "详细信息", "Drive A:": "驱动器 A：",
    "Insert destination diskette": "插入目标软盘",
    "Insert source and destination diskettes": "插入源软盘和目标软盘",
    "Insert source diskette": "插入源软盘",
    "Insufficient disk space; delete one or more unnecessary files and try again.":
        "磁盘空间不足，请删除不需要的文件后重试",
    "Insufficient memory; close one or more Windows applications and try again.":
        "内存不足，请关闭部分 Windows 程序后重试",
    "Now Copying diskette in ": "正在复制驱动器中的软盘 ",
    "Please insert the diskette to format into": "请插入要格式化的软盘",
    "Please insert the source diskette into": "请插入源软盘",
    "Press Cancel if you want to abort.": "按“取消”可中止",
    "the selected files": "所选文件",
})


def cbytes(text: str) -> str:
    return "".join(f"\\x{byte:02X}" for byte in text.encode("gb2312"))


def normalize(text: str) -> str:
    return text.replace("&", "").replace(".", "").rstrip()


def main() -> None:
    control_strings = {number: value for kind, block, _, payload
                       in resources(ENGLISH / "CONTROL.EXE") if kind == 6
                       for number, value in strings(payload, block)}
    for number, (english, _) in CONTROL_ICONS.items():
        if control_strings.get(number) != english:
            raise ValueError(f"CONTROL.EXE STRING {number} changed")
    file_strings = {number: value for kind, block, _, payload
                    in resources(ENGLISH / "WINFILE.EXE") if kind == 6
                    for number, value in strings(payload, block)}
    if file_strings.get(126) != "Directory Tree":
        raise ValueError("WINFILE.EXE STRING 126 changed")
    dialog_strings = set()
    for name in (
        "CALC.EXE", "CALENDAR.EXE", "CARDFILE.EXE", "CLIPBRD.EXE",
        "CLOCK.EXE", "CONTROL.EXE", "NOTEPAD.EXE", "PBRUSH.EXE",
        "PIFEDIT.EXE", "PRINTMAN.EXE", "PROGMAN.EXE", "RECORDER.EXE",
        "REVERSI.EXE", "SOL.EXE", "SYSEDIT.EXE", "TASKMAN.EXE",
        "TERMINAL.EXE", "WINFILE.EXE", "WINHELP.EXE", "WRITE.EXE",
    ):
        for kind, block, _, payload in resources(ENGLISH / name):
            if kind == 6:
                dialog_strings.update(value for _, value in
                                      strings(payload, block))
            elif kind in (4, 5):
                import re
                dialog_strings.update(part.decode("cp1252", "replace")
                                      for part in re.findall(rb"[ -~]{2,}",
                                                             payload))
    missing = set(DIALOG_LABELS) - dialog_strings
    if missing:
        raise ValueError(f"Dialog labels not in original resources: {missing}")
    rows = ["/* Generated from original Windows 3.0 NE dialog resources. */",
            "typedef struct { unsigned short id; const char *english; const char *chinese; } GBRESICON;",
            "static GBRESICON gb_control_icons[] = {"]
    for number, (english, chinese) in CONTROL_ICONS.items():
        rows.append(f'    {{{number}, "{english}", "{cbytes(chinese)}"}},')
    rows += ["};", "#define GB_CONTROL_ICON_COUNT 12",
             "typedef struct { const char *english; const char *chinese; } GBRESLABEL;",
             "static GBRESLABEL gb_dialog_labels[] = {"]
    label_map = {}
    for english, chinese in DIALOG_LABELS.items():
        key = normalize(english)
        if key in label_map and label_map[key] != chinese:
            raise ValueError(f"Conflicting translations for {key}")
        label_map[key] = chinese
    for english in sorted(label_map, key=str.upper):
        chinese = label_map[english]
        rows.append(f'    {{"{normalize(english)}", "{cbytes(chinese)}"}},')
    rows += ["};", f"#define GB_DIALOG_LABEL_COUNT {len(label_map)}", ""]
    TARGET.write_text("\n".join(rows), encoding="ascii")
    print(TARGET)


if __name__ == "__main__":
    main()
