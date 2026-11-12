import sys
from pathlib import Path
from lxml import etree


def fail(message: str) -> None:
    print(f"EPG validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate_epg.py <xml-file>")

    path = Path(sys.argv[1])
    if not path.is_file() or path.stat().st_size == 0:
        fail("EPG file is missing or empty")

    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError as error:
        fail(f"file is not well-formed XML: {error}")

    root = tree.getroot()
    channels = root.findall(".//channel")
    programmes = root.findall(".//programme")

    if not channels:
        fail("no <channel> elements found")
    if not programmes:
        fail("no <programme> elements found")

    invalid_channels = [
        channel for channel in channels
        if not (channel.get("id") or "").strip()
    ]
    if invalid_channels:
        fail(f"{len(invalid_channels)} channel entries have no usable id")

    invalid_programmes = [
        programme for programme in programmes
        if not (programme.get("channel") or "").strip()
        or not (programme.get("start") or "").strip()
        or not (programme.get("stop") or "").strip()
    ]
    if invalid_programmes:
        fail(
            f"{len(invalid_programmes)} programme entries are missing "
            "channel, start, or stop attributes"
        )

    print(
        f"EPG validation passed: {len(channels)} channels, "
        f"{len(programmes)} programmes"
    )


if __name__ == "__main__":
    main()
