"""Run the persistent chat queue as a dedicated foreground process."""

import os
import signal
import threading

from django.core.management.base import BaseCommand, CommandError

from home.gemini_queue import run_chat_worker, wake_worker


class Command(BaseCommand):
    help = "Run the persistent chat queue worker until shutdown is requested."

    def handle(self, *args, **options):
        if os.environ.get("SUPERHARRY_GEMINI_CHAT") != "1":
            raise CommandError("Set SUPERHARRY_GEMINI_CHAT=1 to enable the chat worker.")

        stop_event = threading.Event()

        def request_shutdown(_signum=None, _frame=None):
            stop_event.set()
            wake_worker()

        watched_signals = (signal.SIGTERM, signal.SIGINT)
        previous_handlers = {signum: signal.getsignal(signum) for signum in watched_signals}
        try:
            for signum in watched_signals:
                signal.signal(signum, request_shutdown)
            try:
                run_chat_worker(stop_event)
            except KeyboardInterrupt:
                request_shutdown()
                self.stderr.write(
                    "Keyboard interrupt received; any interrupted claim remains subject to stale-claim recovery."
                )
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
