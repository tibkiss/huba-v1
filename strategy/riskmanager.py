import logging
log = logging.getLogger(__name__)

MIN_QTY = 5  # The minimal required qty


class RiskManager(object):
    """RiskManager is responsible for allocating the trade quantities for
    the various priced instruments. The position quantity is calculated using the
    trade capital, leverage, instrument per position and maximal position count."""

    def __init__(self, tradeCapital=100000, leverage=1.0, maxPositionCount=5, instrPerPosition=2, commission=None):
        self._positions = set()
        self._tradeCapital = tradeCapital
        self._leverage = leverage
        self._maxPositionCount = maxPositionCount
        self._instrPerPosition = instrPerPosition
        self._commission = commission

        log.info("Risk manager initialized: %s", self)

    def __repr__(self):
        return ("tradeCapital=%.2f, leverage=%.2f, maxPositionCount=%d, instrPerPosition=%d" %
                (self._tradeCapital, self._leverage, self._maxPositionCount, self._instrPerPosition))

    def setTradeCapital(self, capital):
        """Sets the trading capital"""
        self._tradeCapital = capital

    def getTradeCapital(self):
        """Returns the currently set trading capital"""
        return self._tradeCapital

    def _calcQty(self, price):
        """Calculates the maximal tradable quantity for the given price.
        Formula:
        capitalPerPosition = (tradeCapital * leverage) / maxPositionCount
        qty = capitalPerPosition / (price * instrPerPosition)

        ValueError is thrown if the quantity would be too low (< MIN_QTY).
        """
        capitalPerPosition = (self._tradeCapital * self._leverage) / self._maxPositionCount
        qty = int(capitalPerPosition / (price * self._instrPerPosition))

        # Calculate and subtract commission price if commission is provided.
        # This is not 100% precise but a good pessimist estimate about the available qty
        if self._commission:
            commission = self._commission.calculate(None, price, qty)
            capitalPerPosition -= (self._instrPerPosition * commission)
            qty = int(capitalPerPosition / (price * self._instrPerPosition))

        if qty < MIN_QTY:
            log.warning("Qty for new position is too small (%d < %d), entry not allowed", qty, MIN_QTY)
            raise ValueError('Qty is too small')
        else:
            return qty

    def addPosition(self, position, price=None):
        """Registers a position (e.g. one or more instruments). ValueError is thrown if
        all the slots are in use. Position could be anything, e.g.:
        string (instrument name), tuple of strings or Strategy instance.
        No error is reported if the position is already registered.

        If price is given the function returns the maximal
        tradable quantitiy for the given instrument (i.e. not position).
        If the maximal tradable quantity would be too low (< 5) ValueError is thrown
        If no price is given None is returned.
        """

        # Register if it is not registered and there is free space left
        if position not in self._positions:
            if len(self._positions) == self._maxPositionCount:
                # No more positions are allowed
                raise ValueError('All positions are in use')
            else:
                self._positions.add(position)

        # Return the qty (if price is given) or None
        if price:
            return self._calcQty(price)
        else:
            return None

    def removePosition(self, position):
        """Deregisters the position. A slot is freed from the position list

        Throws ValueError if the position was not registered before using addPosition.
        """
        if position not in self._positions:
            raise ValueError('Position (%s) is not registered' % str(position))
        else:
            self._positions.discard(position)
