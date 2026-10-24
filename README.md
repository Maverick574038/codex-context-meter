# codex-context-meter

一个 Codex CLI 状态栏插件：在聊天输入框下方实时显示**当前对话的上下文占用**和 **token 消耗**——彩色小圆圈（🟢 <60% / 🟡 60–85% / 🔴 >85%）+ 百分比 + 用量。另附 `report` 命令输出详细 token 分类统计。

A Codex CLI status-line plugin that shows live context-window usage and token consumption below the chat input box, plus a detailed `report` command.

## 预览 / Preview

```
🟢 32% · 64.2k/200k tokens
```

## 安装 / Install

```bash
git clone https://github.com/<you>/codex-context-meter.git
cd codex-context-meter
./install.sh
```

`install.sh` 会把下面这段写入 `~/.codex/config.toml`（已有 `status_line` 时会先备份并提示手动替换，绝不静默覆盖）：

```toml
[tui]
status_line = ["/path/to/codex-context-meter/bin/codex-context-meter"]
```

重启 Codex 即可。

## 数据来源 / How it works

按优先级自动选择（任一可用即可）：

1. Codex `tui.status_line` 钩子通过 **stdin** 传入的会话 JSON；
2. 最新的会话 rollout 文件 `~/.codex/sessions/**/*.jsonl` 中的 `token_count` / `turn_context` 事件（含 `total_token_usage`、`model_context_window`）。

任何解析失败都静默降级为空行，绝不影响 Codex 主界面。

## 详细报告 / Detailed report

```bash
bin/codex-context-meter report
```

输出：当前上下文占用（已用/总量/百分比/剩余）、累计 input / cached input / output / reasoning token、逐 turn 趋势。

## 环境变量

- `CODEX_HOME`：覆盖 Codex 配置目录（默认 `~/.codex`）。
- `--sessions-dir <dir>`：`report` 模式指定会话目录（用于测试）。

## 兼容性说明

- Codex 桌面端没有独立的 UI 插件 API；本插件走官方 `tui.status_line` 通道，在渲染该状态区域的版本（含内嵌 TUI 的桌面端）中生效。若升级后无显示，请确认你的版本支持 `tui.status_line`。
- 不同版本 rollout 文件字段可能有变动：解析器宽松匹配字段名，缺失时显示 `?` 而非报错。

## 开发自测 / Self-test

```bash
python3 bin/codex-context-meter report --sessions-dir tests/fixtures
echo '{"context_window":200000,"tokens_in_context":90000}' | python3 bin/codex-context-meter
```

## License

MIT
