import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validate_epg import validate


class ValidateEpgTests(unittest.TestCase):
    def write_and_validate(self, xml: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.xml"
            path.write_text(xml, encoding="utf-8")
            validate(path)

    def assert_validation_fails(self, xml: str, expected: str) -> None:
        with self.assertRaises(SystemExit) as context:
            self.write_and_validate(xml)

        self.assertEqual(context.exception.code, 1)
        with patch("sys.stderr") as stderr:
            self.write_and_validate(xml)
            self.assertIn(expected, stderr.write.call_args[0][0])

    def test_accepts_timestamps_without_offsets(self) -> None:
        self.write_and_validate(
            """
            <tv>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
              <programme channel="channel-1" start="20260101000000" stop="20260101010000">
                <title>Programme</title>
              </programme>
            </tv>
            """
        )

    def test_accepts_timestamps_with_matching_offsets(self) -> None:
        self.write_and_validate(
            """
            <tv>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
              <programme channel="channel-1" start="20260101000000 +0200" stop="20260101010000 +0200">
                <title>Programme</title>
              </programme>
            </tv>
            """
        )

    def test_accepts_programme_before_channel(self) -> None:
        self.write_and_validate(
            """
            <tv>
              <programme channel="channel-1" start="20260101000000" stop="20260101010000">
                <title>Programme</title>
              </programme>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
            </tv>
            """
        )

    def test_rejects_mixed_timezone_presence(self) -> None:
        self.assert_validation_fails(
            """
            <tv>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
              <programme channel="channel-1" start="20260101000000 +0200" stop="20260101010000">
                <title>Programme</title>
              </programme>
            </tv>
            """,
            "must both include or both omit a timezone offset",
        )

    def test_rejects_invalid_calendar_date(self) -> None:
        self.assert_validation_fails(
            """
            <tv>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
              <programme channel="channel-1" start="20261301000000" stop="20261301010000">
                <title>Programme</title>
              </programme>
            </tv>
            """,
            "invalid calendar date or time",
        )

    def test_rejects_invalid_timezone_offset(self) -> None:
        self.assert_validation_fails(
            """
            <tv>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
              <programme channel="channel-1" start="20260101000000 +2500" stop="20260101010000 +2500">
                <title>Programme</title>
              </programme>
            </tv>
            """,
            "invalid timezone offset",
        )

    def test_rejects_stop_not_after_start(self) -> None:
        self.assert_validation_fails(
            """
            <tv>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
              <programme channel="channel-1" start="20260101010000" stop="20260101010000">
                <title>Programme</title>
              </programme>
            </tv>
            """,
            "stop time is not later than start time",
        )

    def test_rejects_unknown_channel_reference(self) -> None:
        self.assert_validation_fails(
            """
            <tv>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
              <programme channel="channel-2" start="20260101000000" stop="20260101010000">
                <title>Programme</title>
              </programme>
            </tv>
            """,
            "do not match a declared channel",
        )

    def test_rejects_duplicate_channel_id(self) -> None:
        self.assert_validation_fails(
            """
            <tv>
              <channel id="channel-1"><display-name>Channel 1</display-name></channel>
              <channel id="channel-1"><display-name>Channel 1 duplicate</display-name></channel>
              <programme channel="channel-1" start="20260101000000" stop="20260101010000">
                <title>Programme</title>
              </programme>
            </tv>
            """,
            "duplicate channel id",
        )


if __name__ == "__main__":
    unittest.main()
