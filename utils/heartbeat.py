import logging

import aiohttp

from config.settings import get_settings

logger = logging.getLogger(__name__)


async def send_heartbeat():
    """Ping the configured uptime heartbeat URL.

    Used with a "heartbeat"/"cron" style monitor (UptimeRobot, Better Stack, etc.):
    the monitor expects a request on a schedule and alerts if it stops arriving.
    This fits a long-polling bot that has no inbound HTTP port. No-op if unset.
    """
    settings = get_settings()
    url = settings.HEARTBEAT_URL
    if not url:
        return
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status >= 400:
                    logger.warning("Heartbeat ping returned HTTP %s", resp.status)
    except Exception as e:
        # A failed heartbeat must never crash the bot — just log it.
        logger.warning("Heartbeat ping failed: %s", e)
