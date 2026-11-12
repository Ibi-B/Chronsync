import re
import sys
from datetime import datetime
from pathlib import Path
from lxml import etree


TIMESTAMP_PATTERN = re.compile(
    r"^(\d{14})(?:\s+([+-]\d{4}))?$"
)


def fail(message: str) -> None:
    print(f"EPG validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_xmltv_timestamp(value: str, field: str) -> tuple[datetime, bool]:
    match = TIMESTAMP_PATTERN.match(value.strip())
    if not match:
        fail(f"invalid XMLTV timestamp in {field}: {value!r}")

    timestamp, offset = match.groups()
    try:
        parsed = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
    except ValueError as error:
        fail(f"invalid calendar date or time in {field}: {value!r}: {error}")

    if offset:
        try:
            parsed = datetime.strptime(
                f"{timestamp} {offset}",
                "%Y%m%d%H%M%S %z",
            )
        except ValueError as error:
            fail(f"invalid timezone offset in {field}: {value!r}: {error}")

    return parsed, offset is not None


def validate(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        fail("EPG file is missing or empty")

    channel_ids = set()
    programme_channel_refs = set()
    channel_count = 0
    programme_count = 0

    try:
        context = etree.iterparse(
            str(path),
            events=("end",),
            tag=("channel", "programme"),
        )

        for _, element in context:
            if element.tag == "channel":
                channel_id = (element.get("id") or "").strip()
                if not channel_id:
                    fail("a channel entry has no usable id")
                if channel_id in channel_ids:
                    fail(f"duplicate channel id: {channel_id!r}")

                channel_ids.add(channel_id)
                channel_count += 1

            elif element.tag == "programme":
                channel_ref = (element.get("channel") or "").strip()
                start = (element.get("start") or "").strip()
                stop = (element.get("stop") or "").strip()

                if not channel_ref:
                    fail("a programme entry has no channel attribute")
                if not start or not stop:
                    fail("a programme entry is missing start or stop")

                start_time, start_has_offset = parse_xmltv_timestamp(start, "start")
                stop_time, stop_has_offset = parse_xmltv_timestamp(stop, "stop")

                if start_has_offset != stop_has_offset:
                    fail(
                        "programme start and stop timestamps must both include "
                        "or both omit a timezone offset: "
                        f"channel={channel_ref!r}, start={start!r}, stop={stop!r}"
                    )

                if stop_time <= start_time:
                    fail(
                        f"programme stop time is not later than start time: "
                        f"channel={channel_ref!r}, start={start!r}, stop={stop!r}"
                    )

                programme_channel_refs.add(channel_ref)
                programme_count += 1

            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]

    except etree.XMLSyntaxError as error:
        fail(f"file is not well-formed XML: {error}")

    if channel_count == 0:
        fail("no <channel> elements found")
    if programme_count == 0:
        fail("no <programme> elements found")

    unknown_references = programme_channel_refs - channel_ids
    if unknown_references:
        sample = ", ".join(sorted(unknown_references)[:5])
        fail(
            f"{len(unknown_references)} programme channel references "
            f"do not match a declared channel: {sample}"
        )

    print(
        f"EPG validation passed: {channel_count} channels, "
        f"{programme_count} programmes"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: validate_epg.py <xml-file>")

    validate(Path(sys.argv[1]))
