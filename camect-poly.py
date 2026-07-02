#!/usr/bin/env python
#
from pathlib import Path

import markdown2
from udi_interface import Interface, LOGGER
import sys

""" Grab My Controller Node """
from nodes import CamectController, VERSION


def load_config_doc(polyglot):
    """Publish CONFIG.md before PG3 requests customparamsdoc on startup."""
    cfg_md = Path(__file__).resolve().parent / 'CONFIG.md'
    if not cfg_md.is_file():
        return
    try:
        polyglot.setCustomParamsDoc(
            markdown2.markdown_path(
                str(cfg_md),
                extras=['tables', 'fenced-code-blocks'],
            )
        )
    except Exception:
        LOGGER.exception('Failed to convert/set CONFIG.md as custom params doc')


if __name__ == "__main__":
    try:
        polyglot = Interface([])
        polyglot.start(VERSION)
        load_config_doc(polyglot)
        polyglot.updateProfile()
        CamectController(polyglot, 'controller', 'controller', 'Camect Controller')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        LOGGER.warning("Received interrupt or exit...")
        polyglot.stop()
    except Exception as err:
        LOGGER.error('Excption: {0}'.format(err), exc_info=True)
    sys.exit(0)
