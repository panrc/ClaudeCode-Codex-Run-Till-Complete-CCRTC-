# Auto-Test Script

自动监控代码执行并使用 AI 修复错误的 Python 脚本。当代码出错时，会自动调用 `claude` 或 `codex` 命令让 AI 修复问题。

## 核心功能

- 🔍 **智能发现** CodeX/Claude Code 进程
- 📁 **自动获取** 目标进程的工作目录
- 🔄 **自动执行** 指定命令并捕获错误
- 🤖 **AI 自动修复** - 出错时调用 AI 命令：
  - 执行 `claude "错误信息和修复请求"`
  - 或执行 `codex "错误信息和修复请求"`
  - AI 会直接在项目目录中修复代码
- ⏱️ **智能重试** - 最多15次重试（考虑AI修复需要时间）
- 🎯 **稳定性监控** - 程序连续稳定运行指定时间后自动进入持续运行模式

## 工作原理

1. **发现进程** - 找到正在运行的 Claude Code 或 CodeX
2. **获取环境** - 提取进程的工作目录和命令类型
3. **执行测试** - 在目标目录运行你的命令
4. **AI修复** - 如果失败，在同目录执行：`claude "Command: xxx failed. Error: yyy. Please fix this."`
5. **等待修复** - 给AI时间分析和修改代码
6. **重试验证** - 重新运行命令检查是否修复
7. **持续运行** - 稳定后让程序正常运行

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
python auto_test.py "你的命令" 超时时间(秒)
```

### 示例

```bash
# 监控 Python 脚本执行，60秒稳定运行后认为成功
python auto_test.py "python my_script.py" 60

# 监控编译过程
python auto_test.py "make build" 30

# 监控测试运行
python auto_test.py "npm test" 45
```

## 工作流程

1. 脚本启动后会扫描系统中的 CodeX/Claude Code 进程（⭐标记高优先级进程）
2. 用户选择要绑定的目标进程
3. 脚本开始执行指定命令
4. **如果命令失败，错误信息会通过多种方式直接"输入"到绑定的进程中：**
   - 在 macOS 上，首先尝试 AppleScript 自动化，直接模拟键盘输入
   - 尝试窗口自动化，找到目标应用并发送按键
   - 尝试写入进程的 TTY 终端设备
   - 作为备用方案，会播放提示音并将错误信息复制到剪贴板
5. 等待进程响应并监控其活动(CPU/内存变化)
6. 使用指数退避算法重试执行，最多重试10次
7. 程序连续稳定运行指定时间后，切换到最终执行模式

## 测试功能

在使用主脚本之前，可以先测试通信功能：

```bash
# 测试各种通信方法是否正常工作
python test_communication.py
```

## 高级用法

```bash
# 针对 Python 项目
python auto_test.py "python -m pytest tests/" 30

# 针对 Node.js 项目
python auto_test.py "npm run test" 45

# 针对编译项目
python auto_test.py "make && ./my_program" 60

# 针对 Web 应用
python auto_test.py "npm run dev" 120
```

## 参数说明

- `command`: 要执行的命令(必需)
- `timeout`: 认为程序正常运行的时间阈值，单位为秒(必需)

## 系统要求

- Python 3.6+
- 支持 WSL、Linux、macOS
- 需要 psutil 库用于进程管理
- 可选 pyperclip 库用于剪贴板功能