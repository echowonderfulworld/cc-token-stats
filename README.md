# cc-pulse

> Claude Code usage dashboard in your macOS menu bar — costs, tokens, trends, multi-machine sync.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/echowonderfulworld/cc-pulse/main/install.sh | bash
```

## Features

- **Real-time token tracking** from Claude Code session files
- **Accurate cost calculation** — per-model pricing (Opus 4.5/4.6, Sonnet, Haiku)
- **7-day trend** with bar charts
- **Hourly activity heatmap**
- **Project ranking** — see which projects consume the most
- **Multi-machine sync** via iCloud Drive (automatic, zero config)
- **Subscription ROI** — see how much your Pro/Max subscription saves vs API pricing
- **Bilingual** — auto-detects system language (English / Chinese)

## Configuration

Edit `~/.config/cc-token-stats/config.json`:

| Key | Description | Default |
|-----|-------------|---------|
| `claude_dir` | Claude Code config directory | `~/.claude` |
| `sync_mode` | `"auto"` (iCloud), `"custom"`, or `"off"` | `"auto"` |
| `subscription` | Monthly cost in USD (0 = hide savings) | `0` |
| `subscription_label` | Tier name: "Pro", "Max", "Team" | (empty) |
| `language` | `"auto"`, `"en"`, or `"zh"` | `"auto"` |
| `machine_labels` | Friendly names for hostnames | (auto-detect) |

## Requirements

- macOS
- [Claude Code](https://claude.ai/download)
- Python 3.8+
- [SwiftBar](https://github.com/swiftbar/SwiftBar) (auto-installed)

## License

MIT
