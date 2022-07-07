from tools import IS_PYPY

if not IS_PYPY:
    from statsmodels.tsa.stattools import adfuller
else:
    def adfuller(*args, **kwargs):
        raise NotImplementedError("ADFuller is not implemented on PyPy")