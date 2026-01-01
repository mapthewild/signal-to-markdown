#!/usr/bin/env python3
"""Extract a conversation from a Signal desktop backup JSONL export to Markdown."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_backup(jsonl_path):
    """Parse the JSONL backup into structured data."""
    recipients = {}
    chats = {}
    chat_items = []
    account_id = None

    with open(jsonl_path) as f:
        for line in f:
            obj = json.loads(line)

            if "account" in obj:
                account_id = obj["account"].get("recipientId")

            elif "recipient" in obj:
                r = obj["recipient"]
                rid = r["id"]
                name = None
                rtype = "contact"
                if "contact" in r:
                    c = r["contact"]
                    name = (c.get("profileGivenName", "") + " " + c.get("profileFamilyName", "")).strip()
                    if not name:
                        name = (c.get("systemGivenName", "") + " " + c.get("systemFamilyName", "")).strip()
                elif "group" in r:
                    rtype = "group"
                    snap = r["group"].get("snapshot", {})
                    title = snap.get("title", {})
                    name = title.get("title", "") if isinstance(title, dict) else str(title)
                recipients[rid] = {"name": name or f"Unknown ({rid})", "type": rtype}

            elif "chat" in obj and "chatItem" not in obj:
                c = obj["chat"]
                chats[c["id"]] = c.get("recipientId")

            elif "chatItem" in obj:
                chat_items.append(obj)

    return recipients, chats, chat_items, account_id


def list_conversations(recipients, chats, chat_items):
    """List all conversations with message counts."""
    counts = {}
    for item in chat_items:
        cid = item["chatItem"].get("chatId")
        counts[cid] = counts.get(cid, 0) + 1

    convos = []
    for chat_id, recipient_id in chats.items():
        r = recipients.get(recipient_id, {})
        convos.append({
            "chat_id": chat_id,
            "name": r.get("name", f"Unknown ({recipient_id})"),
            "type": r.get("type", "unknown"),
            "messages": counts.get(chat_id, 0),
        })

    convos.sort(key=lambda c: c["messages"], reverse=True)
    return convos


def find_chat(conversations, query):
    """Find a conversation by name (case-insensitive substring match)."""
    query_lower = query.lower()
    matches = [c for c in conversations if query_lower in c["name"].lower()]
    return matches


def format_timestamp(ms_str):
    """Convert millisecond epoch string to local datetime."""
    return datetime.fromtimestamp(int(ms_str) / 1000, tz=timezone.utc).astimezone()


def extract_message(chat_item, names):
    """Extract a message dict from a chatItem record."""
    ci = chat_item["chatItem"]
    ts = format_timestamp(ci["dateSent"])
    author = names.get(ci.get("authorId", ""), ci.get("authorId", "Unknown"))

    if "standardMessage" in ci:
        sm = ci["standardMessage"]
        body = sm.get("text", {}).get("body", "")
        quote_text = None
        if "quote" in sm:
            q = sm["quote"]
            qt = q.get("text")
            if isinstance(qt, dict):
                quote_text = qt.get("body", "")
            elif isinstance(qt, str):
                quote_text = qt
            if not quote_text and "attachments" in q:
                atts = q["attachments"]
                if atts:
                    quote_text = f"[Attachment: {atts[0].get('fileName', atts[0].get('contentType', 'file'))}]"
        return {"ts": ts, "author": author, "body": body, "quote": quote_text, "type": "message"}

    if "updateMessage" in ci:
        um = ci["updateMessage"]
        if "groupChange" in um:
            return {"ts": ts, "author": author, "body": None, "quote": None, "type": "group_change"}
        return {"ts": ts, "author": author, "body": None, "quote": None, "type": "update"}

    return None


def write_markdown(title, messages, output_path):
    """Write messages as markdown grouped by date."""
    current_date = None
    lines = [f"# {title}\n"]

    for msg in messages:
        ts = msg["ts"]
        date_str = ts.strftime("%B ") + str(ts.day) + ts.strftime(", %Y")
        hour_12 = ts.hour % 12 or 12
        time_str = f"{hour_12}:{ts.strftime('%M %p')}"

        if date_str != current_date:
            current_date = date_str
            lines.append(f"\n## {date_str}\n")

        if msg["type"] == "group_change":
            lines.append(f"*{time_str} — Group updated*\n")
            continue
        if msg["type"] == "update":
            lines.append(f"*{time_str} — System update*\n")
            continue

        lines.append(f"**{msg['author']}** — {time_str}")
        if msg["quote"]:
            for qline in msg["quote"].split("\n"):
                lines.append(f"> {qline}")
            lines.append("")
        if msg["body"]:
            lines.append(msg["body"])
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def slugify(text):
    """Convert text to a filename-safe slug."""
    return re.sub(r"[^\w\-]", "-", text.lower()).strip("-")


def main():
    parser = argparse.ArgumentParser(description="Extract a Signal conversation to Markdown.")
    parser.add_argument("jsonl", nargs="?", default="main.jsonl", help="Path to Signal backup JSONL file (default: main.jsonl)")
    parser.add_argument("-c", "--chat", help="Conversation name to extract (case-insensitive substring match)")
    parser.add_argument("-l", "--list", action="store_true", help="List all conversations and exit")
    parser.add_argument("-o", "--output", help="Output markdown file path (default: <chat-name>.md)")
    parser.add_argument("--self-name", default="You", help="Display name for your own messages (default: You)")
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl)
    if not jsonl_path.exists():
        print(f"Error: {jsonl_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {jsonl_path}...")
    recipients, chats, chat_items, account_id = parse_backup(jsonl_path)

    if account_id and account_id in recipients:
        recipients[account_id]["name"] = args.self_name

    conversations = list_conversations(recipients, chats, chat_items)

    if args.list:
        print(f"\n{'Name':<40} {'Type':<10} {'Messages':>8}")
        print("-" * 60)
        for c in conversations:
            if c["messages"] > 0:
                print(f"{c['name']:<40} {c['type']:<10} {c['messages']:>8}")
        return

    if not args.chat:
        print("\nNo conversation specified. Use --chat NAME or --list to see available conversations.")
        print("Example: python3 signal_export.py --chat 'Pottery Class'")
        sys.exit(1)

    matches = find_chat(conversations, args.chat)
    if not matches:
        print(f"No conversation matching '{args.chat}' found.", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        print(f"Multiple matches for '{args.chat}':")
        for m in matches:
            print(f"  - {m['name']} ({m['type']}, {m['messages']} messages)")
        print("Please use a more specific name.")
        sys.exit(1)

    target = matches[0]
    print(f"Extracting '{target['name']}' ({target['messages']} messages)...")

    names = {rid: r["name"] for rid, r in recipients.items()}
    messages = []
    for item in chat_items:
        if item["chatItem"].get("chatId") == target["chat_id"]:
            msg = extract_message(item, names)
            if msg:
                messages.append(msg)

    messages.sort(key=lambda m: m["ts"])

    output_path = Path(args.output) if args.output else Path(f"{slugify(target['name'])}.md")
    write_markdown(target["name"], messages, output_path)
    print(f"Done! {len(messages)} messages written to {output_path}")


if __name__ == "__main__":
    main()
