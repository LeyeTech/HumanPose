#coding: utf-8

import time


class FPSHelper(object):
    def __init__(self, fps=30.0, interval=0.5, coeff=0.2):
        self.fps        = fps
        self._interval  = interval
        self._coeff     = coeff
        self._cnt       = 0
        self._last_time = None

    def update(self):
        if self._last_time is None:  # 第一次
            self._last_time = time.time()
            self._cnt = 0
            return self.fps
        self._cnt += 1
        time_now = time.time()
        time_diff = time_now - self._last_time
        if time_diff >= self._interval:
            self._last_time = time_now
            fps_tmp = self._cnt / time_diff
            # print(f"_fps: {_fps}, fps_idx_last: {self.fps_idx_last}, fps_idx: {self.fps_idx}, time_diff: {time_diff}")
            self.fps = self.fps * (1-self._coeff) + fps_tmp * self._coeff
            self._cnt = 0
        return self.fps
