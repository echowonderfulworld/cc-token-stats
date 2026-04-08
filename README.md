# cc-token-stats

> Monitor your Claude Code token usage, costs, and model breakdown in the macOS menu bar.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/echowonderfulworld/cc-token-stats/main/install.sh | bash
```

## Features

- **Real-time token tracking** from Claude Code session files
- **API-equivalent cost** calculation (Opus / Sonnet / Haiku)
- **Per-model breakdown** with message counts and percentages
- **Multi-machine sync** via iCloud Drive (automatic, zero config)
- **Bilingual** — auto-detects system language (English / Chinese)
- **Subscription savings** — see how much your Pro/Max subscription saves vs API pricing

## Configuration

Edit `~/.config/cc-token-stats/config.json`:

| Key | Description | Default |
|-----|-------------|---------|
| `claude_dir` | Claude Code config directory | `~/.claude` |
| `sync_mode` | `"auto"` (iCloud), `"custom"`, or `"off"` | `"auto"` |
| `sync_repo` | Custom sync directory path | (empty) |
| `subscription` | Monthly cost in USD (0 = hide savings) | `0` |
| `subscription_label` | Tier name: "Pro", "Max", "Team" | (empty) |
| `language` | `"auto"`, `"en"`, or `"zh"` | `"auto"` |
| `machine_labels` | Friendly names for hostnames | (auto-detect) |
| `menu_bar_icon` | SwiftBar SF Symbol icon | `sfSymbol=sparkles.rectangle.stack` |

## Requirements

- macOS
- [Claude Code](https://claude.ai/download)
- Python 3.8+
- [SwiftBar](https://github.com/swiftbar/SwiftBar) (auto-installed)

## License

MIT
