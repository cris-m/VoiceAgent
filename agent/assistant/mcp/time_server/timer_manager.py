import datetime
import pytz


class TimeManager:

    def __init__(self, local_timezone: str = "UTC"):
        try:
            self.local_timezone = pytz.timezone(local_timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            self.local_timezone = pytz.UTC

    def _word_phrase(self, hour: int, minute: int) -> str:
        words = {
            0: "midnight",
            1: "one",
            2: "two",
            3: "three",
            4: "four",
            5: "five",
            6: "six",
            7: "seven",
            8: "eight",
            9: "nine",
            10: "ten",
            11: "eleven",
            12: "noon",
            15: "quarter",
            20: "twenty",
            25: "twenty-five",
            30: "half",
            45: "quarter",
        }

        if minute == 0:
            return f"{words.get(hour, str(hour))} o'clock"
        elif minute == 15:
            return f"quarter past {words.get(hour, str(hour))}"
        elif minute == 30:
            return f"half past {words.get(hour, str(hour))}"
        elif minute == 45:
            next_h = (hour % 12) + 1
            return f"quarter to {words.get(next_h, str(next_h))}"
        elif minute < 30:
            min_word = words.get(minute, str(minute))
            return f"{min_word} past {words.get(hour, str(hour))}"
        else:
            mins_to = 60 - minute
            next_h = (hour % 12) + 1
            min_word = words.get(mins_to, str(mins_to))
            return f"{min_word} to {words.get(next_h, str(next_h))}"

    def get_current_time(self, timezone: str) -> dict:
        try:
            tz = pytz.timezone(timezone)
            current = datetime.datetime.now(tz)
            hour_12 = current.hour % 12 or 12
            minute = current.minute

            return {
                "timezone": timezone,
                "datetime": current.isoformat(),
                "is_dst": bool(current.tzinfo.dst(current)),
                "words": self._word_phrase(hour_12, minute),
                "utc_offset": current.strftime("%z"),
            }
        except pytz.exceptions.UnknownTimeZoneError:
            return {"error": f"Unknown timezone: {timezone}"}

    def convert_time(
        self, source_tz: str, time_str: str, target_tz: str
    ) -> dict:
        try:
            src_tz = pytz.timezone(source_tz)
            tgt_tz = pytz.timezone(target_tz)

            try:
                hour, minute = map(int, time_str.split(":"))
            except ValueError:
                return {"error": f"Invalid time format: {time_str}. Use HH:MM"}

            now = datetime.datetime.now(src_tz)
            src_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            tgt_dt = src_dt.astimezone(tgt_tz)

            offset_seconds = (
                tgt_dt.utcoffset().total_seconds()
                - src_dt.utcoffset().total_seconds()
            )
            offset_hours = offset_seconds / 3600

            src_hour_12 = src_dt.hour % 12 or 12
            tgt_hour_12 = tgt_dt.hour % 12 or 12

            return {
                "source": {
                    "timezone": source_tz,
                    "datetime": src_dt.isoformat(),
                    "words": self._word_phrase(src_hour_12, src_dt.minute),
                    "utc_offset": src_dt.strftime("%z"),
                },
                "target": {
                    "timezone": target_tz,
                    "datetime": tgt_dt.isoformat(),
                    "words": self._word_phrase(tgt_hour_12, tgt_dt.minute),
                    "utc_offset": tgt_dt.strftime("%z"),
                },
                "offset_hours": f"{offset_hours:+.1f}",
            }
        except pytz.exceptions.UnknownTimeZoneError as e:
            return {"error": f"Unknown timezone: {str(e)}"}

    def word_clock(self, timezone: str, precision_minutes: int = 1) -> dict:
        try:
            tz = pytz.timezone(timezone)
            now = datetime.datetime.now(tz)

            rounded_minute = int(round(now.minute / precision_minutes) * precision_minutes)
            if rounded_minute == 60:
                now += datetime.timedelta(hours=1)
                rounded_minute = 0

            hour_12 = now.hour % 12 or 12
            rounded_dt = now.replace(minute=rounded_minute, second=0, microsecond=0)

            return {
                "timezone": timezone,
                "datetime": rounded_dt.isoformat(),
                "words": self._word_phrase(hour_12, rounded_minute),
                "precision_minutes": precision_minutes,
            }
        except pytz.exceptions.UnknownTimeZoneError:
            return {"error": f"Unknown timezone: {timezone}"}

    def list_timezones(self) -> dict:
        timezones = sorted(pytz.all_timezones)
        return {
            "timezones": timezones,
            "count": len(timezones),
        }

    def validate_timezone(self, timezone: str) -> dict:
        try:
            pytz.timezone(timezone)
            return {"valid": True, "timezone": timezone}
        except pytz.exceptions.UnknownTimeZoneError:
            return {"valid": False, "timezone": timezone, "error": "Unknown timezone"}
