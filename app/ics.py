"""Builds an iCalendar (.ics) feed so deadlines show up in Google, Outlook or Apple Calendar.

Follows RFC 5545: CRLF line endings, escaped text, lines folded at 75 octets.
"""

from datetime import UTC, datetime, timedelta

from app.models import Deadline


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Split long lines: continuation lines start with a space. Counts bytes, not characters."""
    out, current = [], b""
    for ch in line:
        b = ch.encode()
        limit = 75 if not out else 74  # continuation lines lose one byte to the leading space
        if len(current) + len(b) > limit:
            out.append(current.decode())
            current = b""
        current += b
    out.append(current.decode())
    return "\r\n ".join(out)


def _stamp(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def build_calendar(deadlines: list[Deadline], host: str, now: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//uni-deadline-tracker//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Uni deadlines",
    ]
    for d in deadlines:
        summary = f"{d.module.code}: {d.title}" if d.module else d.title
        if d.status == "submitted":
            summary = f"✓ {summary}"
        description = []
        if d.weight_percent is not None:
            description.append(f"Worth {d.weight_percent}% of the module")
        if d.notes:
            description.append(d.notes)
        lines += [
            "BEGIN:VEVENT",
            f"UID:deadline-{d.id}@{host}",
            f"DTSTAMP:{_stamp(now)}",
            # A 30-minute event ending at the deadline, so it shows as a block before it's due.
            f"DTSTART:{_stamp(d.due_at - timedelta(minutes=30))}",
            f"DTEND:{_stamp(d.due_at)}",
            f"SUMMARY:{_escape(summary)}",
        ]
        if description:
            lines.append(f"DESCRIPTION:{_escape(chr(10).join(description))}")
        if d.status != "submitted":
            lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_escape(summary)}", "TRIGGER:-P1D", "END:VALARM"]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
