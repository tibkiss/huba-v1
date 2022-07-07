import sys
import traceback
import logging
log = logging.getLogger(__name__)

from tools import log_exception, DT_FMT


class Strategy(object):
    def __init__(self, symbols, brokerAgent, now):
        self.symbols = symbols
        self._ba = brokerAgent
        self._broker = brokerAgent.getBroker()
        self._now = now

        self.alive = True

    def _runGuarded(self, fct, *args, **kwargs):
        if self.alive:
            try:
                return fct(*args, **kwargs)
            except Exception as e:
                log_exception()
                self._log_error("Exception in strategy, disabling")
                self.alive = False

    def _log_error(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.ERROR):
            fmt_str = "<%s> %s %s" % (self._now.strftime(DT_FMT), self.symbols, msg)
            log.error(fmt_str, *args, **kwargs)

    def _log_warning(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.WARNING):
            fmt_str = "<%s> %s %s" % (self._now.strftime(DT_FMT), self.symbols, msg)
            log.warning(fmt_str, *args, **kwargs)

    def _log_warn(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.WARNING):
            fmt_str = "<%s> %s %s" % (self._now.strftime(DT_FMT), self.symbols, msg)
            log.warning(fmt_str, *args, **kwargs)

    def _log_info(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.INFO):
            fmt_str = "<%s> %s %s" % (self._now.strftime(DT_FMT), self.symbols, msg)
            log.info(fmt_str, *args, **kwargs)

    def _log_debug(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.DEBUG):
            fmt_str = "<%s> %s %s" % (self._now.strftime(DT_FMT), self.symbols, msg)
            log.debug(fmt_str, *args, **kwargs)

    def onBars(self, bar, instrument):
        """Called when an a new bar arrived for the stock"""
        raise NotImplementedError('onBars is not implemented')

    def onBars_Guarded(self, bar, instrument):
        return self._runGuarded(self.onBars, bar, instrument)

    def onOrderUpdate(self, order):
        """Called when an order is updated. E.g. completed, cancelled, etc."""
        raise NotImplementedError('onOrderUpdate is not implemented')

    def onOrderUpdate_Guarded(self, order):
        return self._runGuarded(self.onOrderUpdate, order)

    def stop(self):
        """Called when the Strategy is finished"""
        raise NotImplementedError('stop is not implemented')

    def stop_Guarded(self):
        return self._runGuarded(self.stop)
