__author__ = 'tiborkiss'

import numpy as np

class KalmanFilter(object):
    def __init__(self, delta=0.0001, Ve=0.001):
        # OLS: delta=0.000000001
        self._delta = delta
        self._x = np.ones(2)
        self._yhat = 0
        self._e = 0
        self._Q = 0
        self._K = 0
        self._R = np.zeros((2, 2))
        self._P = np.zeros((2, 2))
        self._beta = np.zeros(2)
        self._Vw = self._delta / (1 - self._delta) * np.eye(2)
        self._Ve = Ve

    def update(self, x, y):
        # State covariance prediction
        self._R = self._P + self._Vw

        # Measurement prediction
        self._x[0] = x
        self._yhat = self._x.dot(self._beta)

        # Measurement variance prediction
        self._Q = self._x.dot(self._R).dot(self._x.transpose()) + self._Ve

        # Measurement prediction error
        self._e = y - self._yhat

        # Kalman gain
        self._K = self._R.dot(self._x.transpose()) / self._Q

        # State update
        self._beta += self._K * self._e

        # State covariance update
        self._P = self._R - self._K.dot(self._x) * self._R

        # Return hedge ratio, prediction error and variance
        return 1/self._beta[0], self._e, self._Q
