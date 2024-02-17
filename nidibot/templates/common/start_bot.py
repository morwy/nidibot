#!/usr/bin/env python

import logging
import os
import signal
import sys

from nidibot.nidibot import Nidibot


def shutdown_signal_handler(_1, _2):
    logging.critical("Caught SIGINT signal, nidibot will be shut down.")
    sys.exit(0)


if __name__ == "__main__":
    #
    # Catch Ctrl+C signal for notifying about bureau shutdown.
    #
    signal.signal(signal.SIGINT, shutdown_signal_handler)

    bot = Nidibot(os.path.dirname(os.path.realpath(__file__)))
    bot.start()
