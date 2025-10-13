# socradar/management/commands/import_telegram_json.py
import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware, is_naive

from socradar.models import CredentialLeak  # adjust if your app label differs

User = get_user_model()

def parse_dt(v):
    """
    Try a few datetime formats, return aware datetime or None.
    """
    if not v:
        return None
    if isinstance(v, (int, float)):
        # epoch seconds
        dt = datetime.utcfromtimestamp(v)
        return make_aware(dt)
    if isinstance(v, str):
        # try ISO first
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if is_naive(dt):
                dt = make_aware(dt)
            return dt
        except Exception:
            pass
        # fallback common formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(v, fmt)
                return make_aware(dt)
            except Exception:
                continue
    return None

class Command(BaseCommand):
    help = "Import Telegram scraper JSON export into CredentialLeak records."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Path to channel JSON")
        parser.add_argument(
            "--user",
            type=str,
            help="Username to assign as owner of these leaks (defaults to first superuser).",
        )
        parser.add_argument(
            "--default-severity",
            type=int,
            default=50,
            help="Default severity if not derivable from message.",
        )

    def handle(self, *args, **opts):
        path = Path(opts["json_path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        # choose a user to attach to (you can change your model if user is optional)
        user = None
        if opts.get("user"):
            user = User.objects.filter(username=opts["user"]).first()
            if not user:
                raise CommandError(f"User '{opts['user']}' not found")
        else:
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if not user:
                raise CommandError("No user in DB; create one or pass --user")

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # The repo exports messages; schema can vary per tool version.
        # We'll accept a list of dicts, or a dict with "messages".
        messages = data.get("messages") if isinstance(data, dict) else data
        if not isinstance(messages, list):
            raise CommandError("Unexpected JSON structure: expect list or {'messages': [...]}")

        created = 0
        for m in messages:
            # Try to extract useful fields robustly
            text = m.get("message") or m.get("text") or ""
            # Many exports provide "date" (ISO) and "id"
            leak_date = parse_dt(m.get("date"))
            message_id = m.get("id")

            # For your schema we must fill:
            #   cred_type, value, source, source_url, leak_date, severity, plaintext, content, tags, user
            # Since Telegram is the source, we set source="telegram:<channel>"
            peer = m.get("peer") or m.get("channel") or {}  # may be dict/name/username depending on exporter
            channel_name = None
            if isinstance(peer, dict):
                channel_name = peer.get("title") or peer.get("name") or peer.get("username")
            if not channel_name:
                channel_name = data.get("channel") if isinstance(data, dict) else "telegram"

            source = f"telegram:{channel_name}"
            source_url = None
            # If we have a message link, use it; else build a t.me link if username & id are known
            username = None
            if isinstance(peer, dict):
                username = peer.get("username")
            if username and message_id:
                source_url = f"https://t.me/{username}/{message_id}"

            # Decide cred_type + value.
            # We don't yet extract exact credentials from text; store raw text in 'content'
            cred_type = "username"  # fallback; you can post-process to tag emails/domains later
            value = (username or channel_name or "telegram")
            severity = opts["default_severity"]
            plaintext = False
            tags = []

            # Create the record if text not empty; you can relax this as needed
            if text.strip():
                CredentialLeak.objects.create(
                    user=user,
                    cred_type=cred_type,
                    value=value,
                    source=source,
                    source_url=source_url or "",
                    leak_date=leak_date,
                    severity=severity,
                    plaintext=plaintext,
                    content=text,
                    tags=tags,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {created} messages into CredentialLeak"))
