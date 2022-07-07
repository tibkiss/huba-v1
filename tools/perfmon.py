__author__ = 'tiborkiss'

import time
import logging
log = logging.getLogger(__name__)

class PerformanceMonitor(object):
    def __init__(self, run_cnt, run_per_iter=1, report_interval=100):
        self._run_cnt = run_cnt
        self._run_per_iter = run_per_iter
        self._report_interval = report_interval
        self._start = None
        self._stop = None
        self._iter = None   # Iteration count
        self._intervalStart = None # Interval start time
        self._intervalSpeed = None # Iter/Seconds
        self._lastReport = 0
        self.reset()

        log.info ("%d tasks to complete", run_cnt)

    def reset(self):
        self._start = time.time()
        self._stop = None
        self._iter = 0
        self._intervalStart = self._start
        self._intervalSpeed = 0

    def __str__(self):
        if self._start and self._stop:
            elapsed = self._stop - self._start
            ret = "Overall performance: %.2f sec/iter" % (float(elapsed) / float(self._iter))
        else:
            ret = "Interval performance: %.2f sec/iter" % (self._intervalSpeed)

        return ret

    def iterate(self, cnt=1):
        cnt *= self._run_per_iter
        self._iter += cnt

        report_block = int(self._iter) / int(self._report_interval)
        if report_block > self._lastReport:
            self._lastReport = report_block
            now = time.time()
            elapsed = now - self._intervalStart

            self._intervalSpeed = float(elapsed) / float(self._report_interval) # Sec / iter
            self._intervalStart = now

            remCnt = self._run_cnt - self._iter
            remTime = remCnt / self._intervalSpeed
            log.info('Performance: %.2f sec/iter, processed: %d, remaining %d, remaining time: %.2fs',
                      self._intervalSpeed, self._iter, remCnt, remTime)


    def stop(self):
        self._stop = time.time()

        log.info("Finished. Peformance: %s", str(self))