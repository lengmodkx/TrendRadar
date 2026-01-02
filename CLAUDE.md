# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TrendRadar** is a Python-based news aggregation and analysis tool that:
- Crawls trending topics from 11+ Chinese platforms (Weibo, Zhihu, Bilibili, etc.)
- Supports RSS/Atom feed subscriptions
- Filters news by user-configured keywords
- Generates HTML reports and sends notifications to multiple channels
- Provides AI analysis capabilities via MCP (Model Context Protocol) server

**Version**: 4.6.0
**Language**: Python 3.10+
**Package Manager**: uv (recommended) or pip

## Development Commands

### Installation
```bash
# Windows (with script)
setup-windows.bat          # Install dependencies
setup-windows-en.bat       # English version

# macOS/Linux (with script)
./setup-mac.sh

# Manual installation
pip install -r requirements.txt
```

### Running the Application
```bash
# Run as module
python -m trendradar

# Run as installed command
trendradar

# Run MCP server
python -m mcp_server.server
trendradar-mcp

# Start HTTP MCP server (for AI clients)
start-http.bat              # Windows
./start-http.sh             # macOS/Linux
```

### Testing
There are no formal unit tests in this project. Testing is done by:
1. Running the application locally
2. Verifying notifications are received
3. Checking generated output files in `output/` directory

### Docker Deployment
```bash
cd docker
docker compose up -d                    # Start all services
docker compose up -d trendradar         # Start only news service
docker compose up -d trendradar-mcp     # Start only MCP AI service
```

### Build
```bash
# Build wheel package
pip install build
python -m build

# Build Docker images (see docker/ directory)
docker build -t trendradar .
```

## Architecture

### Core Components

**Main Application Flow** (`trendradar/__main__.py`):
1. `NewsAnalyzer` class orchestrates the entire pipeline
2. Loads configuration from `config/config.yaml`
3. Crawls data from platforms and RSS feeds
4. Processes and analyzes data
5. Generates reports and sends notifications

**Module Structure**:
- `trendradar/__main__.py` - Main entry point and analysis pipeline
- `trendradar/core/` - Core business logic (config, data analysis, frequency matching)
- `trendradar/crawler/` - Data fetching (hot lists and RSS feeds)
- `trendradar/storage/` - Storage abstraction (local SQLite, remote S3-compatible)
- `trendradar/report/` - Report generation (HTML, text, statistics)
- `trendradar/notification/` - Multi-channel notification dispatch
- `mcp_server/` - MCP AI analysis server with 17 tools

### Key Design Patterns

1. **AppContext Pattern** (`trendradar/context.py`):
   - Centralizes configuration and provides factory methods
   - Manages platform lists, time zones, and component creation
   - Use `self.ctx` to access configuration and create components

2. **Storage Abstraction** (`trendradar/storage/`):
   - `base.py` - Abstract base for storage backends
   - `local.py` - SQLite-based local storage
   - `remote.py` - S3-compatible cloud storage (R2, OSS, COS)
   - `manager.py` - Unified interface that auto-selects backend

3. **Notification System** (`trendradar/notification/`):
   - `dispatcher.py` - Routes to multiple channels (Feishu, Telegram, etc.)
   - `formatters.py` - Formats messages per platform
   - `senders.py` - Platform-specific sending logic
   - `batch.py` - Handles message size limits with batching

### Configuration System

**Main Config** (`config/config.yaml`):
- 7 logical sections: app, platforms, rss, report, notification, storage, advanced
- Environment variable override support (Docker/GitHub Actions)
- Multi-account support for all notification channels (use `;` separator)

**Keywords Config** (`config/frequency_words.txt`):
- 5 syntax types: normal, required (`+`), filtered (`!`), limited (`@N`), global filter (`[GLOBAL_FILTER]`)
- Word groups separated by blank lines
- Applied to both hot lists and RSS feeds

### Report Modes

Three distinct modes with different data handling:

1. **daily** - Accumulates all news from the day
2. **current** - Shows current trending list (uses full history for accurate stats)
3. **incremental** - Only pushes new content (zero duplicates)

Important: `current` mode loads complete historical data for statistics, not just latest crawl.

### MCP Server Architecture

**AI Analysis Tools** (`mcp_server/tools/`):
- `data_query.py` - Basic queries (latest news, by date, trending topics)
- `search_tools.py` - Advanced search (search_news, find_related_news)
- `analytics.py` - Trend analysis and data insights
- `storage_sync.py` - Remote storage synchronization
- `system.py` - System status and configuration
- `config_mgmt.py` - Configuration management

**Services** (`mcp_server/services/`):
- `data_service.py` - Data access layer with caching
- `parser_service.py` - Date parsing and query interpretation
- `cache_service.py` - Performance optimization for repeated queries

## Important Implementation Details

### Data Flow

1. **Crawling** (`crawler/fetcher.py`, `crawler/rss/`):
   - Fetches from 11+ platforms via newsnow API
   - Parses RSS/Atom feeds with feedparser
   - Normalizes URLs to avoid duplicates (e.g., Weibo `band_rank` params)

2. **Storage** (`storage/manager.py`):
   - SQLite is the primary data store
   - File structure: `output/{type}/{date}.db`
   - Types: `news` (hot lists), `rss` (feeds)
   - Auto-cleanup based on `retention_days` config

3. **Analysis** (`core/analyzer.py`, `core/frequency.py`):
   - Keyword matching with complex rules
   - Hotness scoring: 60% rank + 30% frequency + 10% hotness
   - Platform vs keyword grouping (controlled by `display_mode`)

### Notification Channels

Supported channels (all support multi-account via `;` separator):
- Feishu (webhook)
- DingTalk (webhook)
- WeWork (webhook, supports personal WeChat via `msg_type: text`)
- Telegram (bot_token + chat_id, requires pairing)
- Email (SMTP with auto-detection for 10+ providers)
- ntfy (topic + optional token, requires pairing)
- Bark (iOS push URL)
- Slack (webhook)

**Security**: Never commit webhooks to Git. Use GitHub Secrets or environment variables.

### Time Handling

- All timestamps use configured timezone (default: `Asia/Shanghai`)
- Format: `YYYY-MM-DD` for dates, `HH:MM:SS` for times
- Storage filenames use ISO date format
- Push window respects timezone for all comparisons

### Display Modes

- `keyword` (default): Groups news by matched keywords, shows `[PlatformName]`
- `platform`: Groups news by platform/source, shows `[Keyword]`

## Common Tasks

### Adding a New Platform

1. Edit `config/config.yaml` → `platforms` section
2. Add platform from newsnow: `{id: "platform-id", name: "Display Name"}`
3. See available platforms at: https://github.com/ourongxing/newsnow

### Adding a New Notification Channel

1. Implement sender in `notification/senders.py`
2. Add formatter in `notification/formatters.py` (if needed)
3. Add config in `config/config.yaml` → `notification.channels`
4. Update `notification/dispatcher.py` to dispatch to new channel
5. Add webhook/token config validation in `__main__.py:_has_notification_configured()`

### Modifying Report Content

- HTML templates: `report/html.py`, `report/rss_html.py`
- Text formatting: `report/formatter.py`
- Statistics calculation: `core/analyzer.py`

### MCP Server Debugging

```bash
# Start HTTP server
uv run python -m mcp_server.server --transport http --port 3333

# Test connection
curl http://localhost:3333/mcp

# Run MCP Inspector
npx @modelcontextprotocol/inspector
# Then connect to http://localhost:3333/mcp
```

## Environment-Specific Behavior

### GitHub Actions
- Environment detected via `GITHUB_ACTIONS=true`
- Storage backend: auto-selects remote if S3 configured
- Proxy: disabled by default
- Version check: enabled by default
- Requires "Check In" workflow every 7 days

### Docker
- Environment detected via `DOCKER_CONTAINER=true` or presence of `/.dockerenv`
- Storage backend: local SQLite
- Config override: Environment variables > config.yaml
- Web server available for browsing reports
- No browser auto-opening

### Local Development
- Proxy: controlled by `config.yaml`
- Browser: auto-opens HTML reports
- Storage: local SQLite by default

## Configuration Override Priority

Environment variables (Docker/GitHub Actions) > `config.yaml` > defaults

Key environment variables:
- `STORAGE_BACKEND` - Force backend selection
- `REPORT_MODE` - Override report mode
- `ENABLE_NOTIFICATION` - Toggle notifications
- `TZ` - Set timezone
- Channel-specific vars: `FEISHU_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, etc.

## File Locations

| File/Directory | Purpose |
|----------------|---------|
| `config/config.yaml` | Main configuration |
| `config/frequency_words.txt` | Keyword filtering rules |
| `output/` | Generated data and reports |
| `output/news/YYYY-MM-DD.db` | Hot list SQLite database |
| `output/rss/YYYY-MM-DD.db` | RSS feed SQLite database |
| `output/html/YYYY-MM-DD/` | HTML reports by date |
| `index.html` | Latest daily summary (GitHub Pages) |

## Dependencies

Core runtime dependencies:
- `requests` - HTTP client
- `pytz` - Timezone handling
- `PyYAML` - Config parsing
- `websockets` - MCP transport
- `fastmcp` - MCP server framework
- `feedparser` - RSS/Atom parsing
- `boto3` - S3-compatible storage

Development dependencies (in `pyproject.toml`):
- `hatchling` - Build backend
- `uv` - Package installer (recommended)

## Migration Notes

**v4.0.0 Breaking Changes**:
- Database structure completely rewritten (incompatible with v3.x)
- File paths changed to ISO format (`YYYY-MM-DD`)
- Storage abstraction added (local/remote/auto)
- MCP server requires SQLite data (TXT format removed from MCP)

**v4.5.0 RSS Support**:
- Added RSS/Atom feed crawling
- Unified keyword matching for hot lists + RSS
- Merged notifications (single message for both sources)
- Freshness filter to avoid old article duplicates
