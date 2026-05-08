import argparse
import logging
import sys
import traceback

from mcp.server.fastmcp import Context, FastMCP
from assistant.mcp.time_server.timer_manager import TimeManager


class TimeMCP:

    def __init__(self, local_timezone: str = "UTC"):
        self.local_timezone = local_timezone
        self._setup_logging()
        self.time_manager = TimeManager(local_timezone=local_timezone)
        self.mcp = FastMCP(name="Time MCP Server", version="1.0.0")
        self.register_tools()
        logging.info(f"Time MCP initialized (default timezone: {local_timezone})")

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(__name__)

    def register_tools(self) -> None:

        @self.mcp.tool("time_current")
        def get_current_time(timezone: str = None, ctx: Context = None) -> dict:
            """Get current time in specified timezone.

            Args:
                timezone: IANA timezone string (e.g., 'America/New_York', 'Europe/London')

            Returns:
                Current time with ISO datetime, DST status, and word representation
            """
            try:
                target_tz = timezone or self.local_timezone
                result = self.time_manager.get_current_time(target_tz)
                if ctx and "error" not in result:
                    ctx.info(f"Current time retrieved for {target_tz}")
                return result
            except Exception as e:
                if ctx:
                    ctx.error(f"Error getting current time: {e}")
                return {"error": str(e)}

        @self.mcp.tool("time_word_clock")
        def word_clock(timezone: str = None, precision: int = 1, ctx: Context = None) -> dict:
            """Get word clock representation of current time.

            Converts time to English words (e.g., 'quarter past three').

            Args:
                timezone: IANA timezone string (default: server's local timezone)
                precision: Round time to nearest N minutes (default: 1)

            Returns:
                Time as English phrase with datetime
            """
            try:
                target_tz = timezone or self.local_timezone
                result = self.time_manager.word_clock(target_tz, precision)
                if ctx and "error" not in result:
                    ctx.info(f"Word clock retrieved for {target_tz}")
                return result
            except Exception as e:
                if ctx:
                    ctx.error(f"Error getting word clock: {e}")
                return {"error": str(e)}

        @self.mcp.tool("time_convert")
        def convert_time(
            source_timezone: str,
            time_str: str,
            target_timezone: str,
            ctx: Context = None,
        ) -> dict:
            """Convert time between two timezones.

            Args:
                source_timezone: Source IANA timezone (e.g., 'America/New_York')
                time_str: Time in HH:MM format (e.g., '14:30')
                target_timezone: Target IANA timezone (e.g., 'Europe/London')

            Returns:
                Source and target times with offset information
            """
            try:
                result = self.time_manager.convert_time(
                    source_timezone, time_str, target_timezone
                )
                if ctx and "error" not in result:
                    ctx.info(
                        f"Time converted from {source_timezone} to {target_timezone}"
                    )
                return result
            except Exception as e:
                if ctx:
                    ctx.error(f"Error converting time: {e}")
                return {"error": str(e)}

        @self.mcp.tool("time_timezone_list")
        def list_timezones(ctx: Context = None) -> dict:
            """List all available IANA timezones.

            Returns:
                Sorted list of 400+ supported timezones with count
            """
            try:
                result = self.time_manager.list_timezones()
                if ctx:
                    ctx.info(f"Retrieved {result['count']} available timezones")
                return result
            except Exception as e:
                if ctx:
                    ctx.error(f"Error listing timezones: {e}")
                return {"error": str(e)}

        @self.mcp.tool("time_timezone_validate")
        def validate_timezone(timezone: str, ctx: Context = None) -> dict:
            """Validate if a timezone string is recognized.

            Args:
                timezone: Timezone string to validate (e.g., 'America/New_York')

            Returns:
                Validation result with 'valid' boolean field
            """
            try:
                result = self.time_manager.validate_timezone(timezone)
                if ctx:
                    status = "valid" if result.get("valid") else "invalid"
                    ctx.info(f"Timezone {timezone} is {status}")
                return result
            except Exception as e:
                if ctx:
                    ctx.error(f"Error validating timezone: {e}")
                return {"error": str(e)}

    def run(self) -> None:
        try:
            self.logger.info("Starting Time MCP server...")
            self.mcp.run(transport="stdio")
        except Exception as e:
            self.logger.error(f"Failed to start Time MCP server: {e}")
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Time MCP Server")
    parser.add_argument(
        "-t",
        "--timezone",
        default="UTC",
        help="Default timezone (IANA format, e.g., 'America/New_York'). Default: UTC",
    )

    args = parser.parse_args()

    time_mcp = TimeMCP(local_timezone=args.timezone)
    time_mcp.run()


if __name__ == "__main__":
    try:
        logging.info("Initializing Time MCP server")
        main()
    except KeyboardInterrupt:
        logging.info("Received shutdown signal. Gracefully shutting down...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
