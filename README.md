# Fintech Lark Radar

A small, self-hosted fintech/neobank news radar that polls RSS, Atom, Substack, and podcast feeds, classifies new items, deduplicates them in SQLite, and pushes concise updates to a Lark/Feishu group through a custom bot webhook.

## What It Does

- Polls configured feeds for fintech, neobank, payments, crypto, regtech, embedded finance, and related topics.
- Supports news sites, Substack feeds, blogs, and podcast RSS feeds.
- Deduplicates by canonical link/title hash in `data/radar.sqlite3`.
- Classifies each item with configurable keyword categories.
- Sends grouped updates to a Lark or Feishu group bot.
- Runs once for cron/serverless jobs or continuously with a polling interval.

## Quick Start

1. Create a Lark/Feishu group custom bot and copy its webhook URL.
2. Optional but recommended: enable signature verification and copy the bot secret.
3. Copy the environment template:

```bash
cp .env.example .env
```

4. Edit `.env`:

```bash
LARK_WEBHOOK_URL=https://open.larksuite.com/open-apis/bot/v2/hook/your-token
LARK_SECRET=your-signing-secret
```

For Feishu China tenants, the webhook host is usually `https://open.feishu.cn/...`.

To translate English updates into Chinese, add an OpenAI API key:

```bash
TRANSLATE_TO_ZH=true
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4.1-mini
```

5. Run a dry run:

```bash
python3 -m fintech_radar --once --dry-run
```

By default, the radar only considers items published in the last 3 days and excludes items dated more than 1 day in the future. Change those windows with `--lookback-days` and `--future-grace-days`.

6. Send to Lark:

```bash
python3 -m fintech_radar --once
```

7. Run continuously:

```bash
python3 -m fintech_radar --watch --interval 300
```

Or install a local macOS background schedule that runs every day at 09:00 and 18:00:

```bash
zsh scripts/install_launchd.sh
```

Check logs:

```bash
tail -f logs/launchd.out.log
tail -f logs/launchd.err.log
```

Remove the schedule:

```bash
zsh scripts/uninstall_launchd.sh
```

For a first production run, use a short lookback window to avoid flooding the group:

```bash
python3 -m fintech_radar --once --lookback-days 1
```

## Configuration

Edit `config/sources.json` to add or remove feeds.

Each source:

```json
{
  "name": "Finextra",
  "url": "https://www.finextra.com/rss/headlines.aspx",
  "type": "rss",
  "enabled": true,
  "tags": ["news", "banking"]
}
```

YouTube channels are also supported. Use a channel id if you have it:

```json
{
  "name": "Tokenized - YouTube",
  "url": "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx",
  "type": "youtube",
  "enabled": true,
  "tags": ["podcast", "youtube", "stablecoins", "payments"]
}
```

Or put the id directly:

```json
{
  "name": "Tokenized - YouTube",
  "url": "https://www.youtube.com/@tokenizedpod",
  "type": "youtube",
  "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
  "enabled": true,
  "tags": ["podcast", "youtube", "stablecoins", "payments"]
}
```

Plain `youtube.com/@handle` URLs need to be converted to channel ids before the radar can poll them reliably.

Edit `config/categories.json` to tune classification. Categories are assigned when item title, summary, or source tags match configured keywords.

## KOL And Social Sources

Many KOL sources on X/Twitter, LinkedIn, or private newsletters do not expose reliable public RSS feeds. Recommended options:

- Use official APIs where available.
- Use a paid RSS bridge service for specific creators.
- Add Substack/public newsletter RSS URLs directly.
- Add a custom adapter under `fintech_radar/sources/` if the source has a stable API.

## Deployment Options

- Local Mac/Linux machine with `--watch`.
- macOS `launchd` with `scripts/install_launchd.sh`, so Terminal does not need to stay open.
- GitHub Actions with `.github/workflows/fintech-radar.yml`, scheduled at 09:00 and 18:00 Asia/Shanghai.
- Cron job every 5 minutes:

```cron
*/5 * * * * cd /path/to/project && /usr/bin/python3 -m fintech_radar --once
```

- Docker, serverless scheduled jobs, or any VM that can reach the feed URLs and Lark webhook.

## GitHub Actions Deployment

1. Push this project to a GitHub repository.
2. In GitHub, open `Settings` -> `Secrets and variables` -> `Actions`.
3. Add repository secrets:

```text
LARK_WEBHOOK_URL
LARK_SECRET
OPENAI_API_KEY
```

4. Optional: add repository variable `OPENAI_MODEL`, for example `gpt-4.1-mini`.
5. Open `Actions` -> `Fintech Radar` -> `Run workflow` to test it manually.

The workflow runs at 09:00 and 18:00 Asia/Shanghai. It commits `data/radar.sqlite3` back to the repository after each run so deduplication survives across GitHub Actions runs.

## Notes

Lark custom bot webhooks support plain text and richer message types. This MVP sends compact text digests with title, Chinese summary, source, and link for reliability. Interactive cards can be added later once the taxonomy and message format feel right.
