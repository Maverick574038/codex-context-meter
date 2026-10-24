# codex-context-meter

[English README → README.en.md](README.en.md)

一个 Codex 上下文用量插件：实时反映**当前对话的上下文占用**和 **token 消耗**。提供两个版本：

- **`bin/codex-context-meter`** — 中文版（默认）
- **`bin/codex-context-meter-en`** — 英文版（同一逻辑，英文输出）
- **`bin/codex-context-meter-gui`** — 常驻网页面板（中文，见下）
- **`bin/codex-context-meter-gui-en`** — 常驻网页面板（English）
- **`bin/codex-context-meter-float`** — 桌面悬浮窗（中文，见下）
- **`bin/codex-context-meter-float-en`** — 桌面悬浮窗（English）

### 4. 桌面悬浮窗（无需浏览器）

```bash
bin/codex-context-meter-float         # 中文
bin/codex-context-meter-float-en      # English
```

无边框置顶半透明小窗：彩色圆环 + 百分比 + 用量/剩余，项目→会话两级下拉，⟳ 刷新，每 3 秒自动更新，按住拖动可移动位置。零依赖（macOS 自带 Tkinter）。

### 3. 常驻图形面板（GUI，桌面端推荐）

```bash
bin/codex-context-meter-gui           # 中文，自动打开浏览器
bin/codex-context-meter-gui-en        # English
```

启动本地页面 `http://localhost:8787`：彩色大圆环（绿/黄/红）+ 百分比 + 进度条 + 分类统计 + 逐轮趋势图，**每 3 秒自动刷新**。浏览器标签常驻即可；`--port` 可换端口，Ctrl+C 退出。零第三方依赖（Python 内置 HTTP 服务）。

## 功能

### 1. 状态栏模式（终端版 Codex CLI）

在聊天输入框下方显示：`🟢 37% · 73.5k/200k`

- 🟢 <60% / 🟡 60–85% / 🔴 >85%
- 通过 `tui.status_line` 配置接入，仅对**终端版 Codex CLI** 生效（桌面应用不渲染该状态区域）

### 2. 详细报告（桌面端/CLI 通用）

```bash
bin/codex-context-meter report        # 中文
bin/codex-context-meter-en report     # English
```

输出：当前上下文占用（已用/总量/百分比/剩余）、累计输入/缓存命中/输出/推理 token、逐轮趋势。桌面端用户直接用它即可。

## 安装

```bash
git clone https://github.com/Maverick574038/codex-context-meter.git
cd codex-context-meter
./install.sh            # 配置终端 CLI 状态栏（可选）
```

桌面端无需安装，直接跑 `report`。建议加个别名：

```bash
echo 'alias cx="~/Codex上下文插件/bin/codex-context-meter report"' >> ~/.zshrc
```

`install.sh` 会幂等写入 `~/.codex/config.toml` 的 `tui.status_line`，已有配置先备份不覆盖。

## 数据来源

按优先级自动选择：
1. `tui.status_line` 钩子经 stdin 传入的会话 JSON（CLI 实时）
2. 最新 rollout 文件 `~/.codex/sessions/**/*.jsonl` 的 `token_count` / `turn_context` 事件（桌面端与 CLI 都写）

「上下文占用」取最后一轮请求的真实 token 量，不采用累计值。桌面端数据有几分钟级落盘延迟属正常现象。

## 环境变量 / 参数

- `CODEX_HOME`：覆盖 Codex 配置目录（默认 `~/.codex`）
- `CCM_LANG=en`：强制英文输出
- `--sessions-dir <dir>`：report 模式指定会话目录（测试用）

## 自测

```bash
bin/codex-context-meter report --sessions-dir tests/fixtures
echo '{"context_window":200000,"tokens_in_context":90000}' | bin/codex-context-meter
```

## License

MIT
