# macOS 权限设置指南

要让 auto-test 脚本在 macOS 上完全正常工作，需要设置一些系统权限。

## 辅助功能权限 (必需)

AppleScript 自动化需要辅助功能权限才能发送键盘事件：

1. 打开 **系统偏好设置** > **安全性与隐私** > **隐私**
2. 在左侧列表中选择 **辅助功能**
3. 点击左下角的 🔒 锁图标并输入密码
4. 添加以下应用程序（如果存在）：
   - **Terminal** (如果你从 Terminal 运行脚本)
   - **iTerm2** (如果你使用 iTerm2)
   - **Python** 或 **python3** (Python 解释器)
   - **osascript** (AppleScript 解释器)

## 查找应用程序路径

如果不确定程序的路径，可以使用这些命令：

```bash
# 查找 Python 路径
which python3

# 查找 osascript 路径
which osascript

# 示例输出：
# /usr/bin/python3
# /usr/bin/osascript
```

## 验证权限设置

设置权限后，运行测试脚本验证：

```bash
python test_communication.py
```

如果看到类似错误：
```
"osascript"不允许发送按键
```

说明权限还没有正确设置。

## 手动测试 AppleScript

可以手动运行这个命令测试 AppleScript 权限：

```bash
osascript -e 'tell application "System Events" to keystroke "test"'
```

如果权限正确，这应该在当前活动窗口中输入 "test"。

## 备用方案

即使 AppleScript 不工作，脚本仍然会尝试其他通信方法：
- 剪贴板 + 声音通知
- TTY 直接输入
- 临时文件创建

## 故障排除

### 问题：AppleScript 找不到应用程序
**解决方案：**
- 确保 Claude Code 或目标应用程序正在运行
- 尝试使用应用程序的完整路径或不同的名称变体

### 问题：权限被拒绝
**解决方案：**
- 重新启动 Terminal/iTerm2 (权限更改后需要重启)
- 检查系统偏好设置中的权限列表
- 尝试手动添加 `/usr/bin/osascript` 到辅助功能列表

### 问题：剪贴板不工作
**解决方案：**
```bash
pip install pyperclip
```