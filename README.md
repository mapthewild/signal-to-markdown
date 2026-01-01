# signal-to-markdown

Turn your Signal Desktop chat export (`.jsonl`) into clean, readable Markdown — one file per conversation. Pure Python, no dependencies.

> Python 3.8+ · MIT · macOS / Linux / Windows

## Is this the right tool?

Signal has several export and backup formats. This script only handles one.

| You have… | Use |
|---|---|
| A `.jsonl` file from Signal Desktop's chat-export feature | ✅ this tool |
| An encrypted Signal Secure Backup (requires a 30-digit passphrase) | [bepaald/signalbackup-tools](https://github.com/bepaald/signalbackup-tools) |
| Signal Desktop's `db.sqlite` from the app's config folder | [carderne/signal-export](https://github.com/carderne/signal-export) |
| A Signal Android `.backup` file | [bepaald/signalbackup-tools](https://github.com/bepaald/signalbackup-tools) |

Not sure? Open your file in a text editor. If it's plain text starting with `{"version":...}`, `{"account":...}`, `{"recipient":...}` records, you're in the right place.

## Quick start

Download `signal_export.py` from this repo, then:

```bash
# List conversations and message counts
python3 signal_export.py main.jsonl --list

# Extract one conversation to Markdown
python3 signal_export.py main.jsonl --chat "Pottery Class"
```

No install, no dependencies.

## What the output looks like

```markdown
# Pottery Class

## October 5, 2023

**Mira** — 11:23 AM
Anyone free Saturday?

**Theo** — 11:31 AM
> Anyone free Saturday?

I can be there by noon.

**You** — 11:47 AM
Sounds good.

*4:22 PM — Group updated*
```

When rendered (Obsidian, GitHub preview, VS Code, etc.) names appear bold, quoted replies indent, and system events italicize.

## Getting your `.jsonl` from Signal Desktop

Signal Desktop → Settings → Chats → **Export chat history**

Menu paths may shift between Signal Desktop versions; the chat-export feature shipped to Signal Desktop in 2026 as part of the local-backup rollout.

## Options

| Option | Description |
|---|---|
| `jsonl_file` | Path to the export (default: `main.jsonl`) |
| `-l`, `--list` | List all conversations and exit |
| `-c`, `--chat NAME` | Conversation to extract (case-insensitive substring match) |
| `-o`, `--output FILE` | Output file path (default: `<chat-name>.md`) |
| `--self-name NAME` | Label for your own messages (default: `You`) |

```bash
# Extract to a custom path
python3 signal_export.py --chat "Trail Runners" --output trail-runners.md

# Read from a non-default location
python3 signal_export.py /path/to/backup.jsonl --chat "Apartment Hunt"

# Use a name instead of "You"
python3 signal_export.py --chat "Trivia Tuesdays" --self-name "Mira"
```

## Notes

- **Timezone.** Timestamps render in your machine's local timezone.
- **Attachments** are referenced by filename in quoted replies; attachment files themselves are not extracted.
- **System events.** Group changes appear as `*Group updated*`. Other system events (calls, profile changes, expiry-timer changes) are skipped.
- **Privacy.** The script reads your `.jsonl` locally and writes Markdown to disk. Nothing is sent anywhere.

## Requirements

- Python 3.8+
- Standard library only

<details>
<summary>Signal JSONL format reference</summary>

| Record | Key | Description |
|---|---|---|
| Header | `version`, `backupTimeMs` | Export metadata |
| Account | `account` | Account info |
| Recipient | `recipient` | Contacts and groups |
| Chat | `chat` | Chat thread metadata (maps `chatId` to `recipientId`) |
| ChatItem | `chatItem` | Messages, replies, system events |
| StickerPack | `stickerPack` | Installed sticker packs |
| ChatFolder | `chatFolder` | Chat organization folders |

ChatItem subtypes handled by this script:
- `standardMessage` — Text messages. Body at `.text.body`, quoted replies at `.quote.text.body`.
- `updateMessage.groupChange` — Member joins/leaves, title changes, etc.

</details>

## License

MIT
