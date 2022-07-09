# What is this?

This repo holds the very first algo trading strategy I have developed and live traded from 2012 to 2016.

It was built using [PyAlgoTrade](https://github.com/gbeced/pyalgotrade) with the Pair Trading / Stat Arb 
guidelines posted in [Ernie Chan's Quantitative Trading book](https://amzn.to/3arFQNz).


# Why are you releasing it?

It created lower-than-expected live trading returns, so I moved on. I think it might be useful for others as learning material.

Even though it made [some profits live](https://github.com/tibkiss/huba-v1/blob/master/logs/trades-real.csv), it wasn't up to my expectation:
The initial [capital](https://github.com/deltaray-io/huba-v1/blob/master/logs/equities-real.csv) trading this strategy was $40k. 
While continuously adding savings to the account, it ended up making $6k over the 3-year period. Even if we ignore the fact that additional
was capital was deployed to the account the CAGR would be around 5%. 

I made two other iterations of this strategy: [huba-v2](https://github.com/tibkiss/huba-v2) and [huba-v3](https://github.com/tibkiss/huba-v3/)
will be released shortly, with similar commentary.

# What was the approach?

Finding cointegrated pairs and trading them long/short when they drift too far apart from their expected fair price.
You can find all the details in Ernie's [first](https://amzn.to/3arFQNz) and [second](https://amzn.to/3OLJf8W) book on the subject.

# What did u do step by step?

1) Purchased minute data from iqfeed, ingested it
2) Implemented Statistical Arbitrage as discussed in [the book](https://amzn.to/3arFQNz)
3) Created a liquidity and price filter to filter out non-tradable stocks
4) Created pairs for each equity sector
5) Did a bruteforce on half of my data
6) Picked the best looking pairs, which *seemed* to make sense
7) Validated them on my other half of the data
8) Picked the ones which still remained reasonable and [put it](https://github.com/tibkiss/huba-v1/blob/main/config.py) into paper trading
9) After gaining confidence put the best pairs to live trading
10) Explored AD-Fuller tests, Hurst exponents, Earnings filters and bunch of other stup
11) Profit of 6k after 4 years
12) Moved on to zipline based implementation (huba-v2)

# What have you learned from this?

0) Max time in trade is a *must*. huba-v1 didn't have this implemented, but [huba-v2](https://github.com/tibkiss/huba-v3) has this feature.
1) Running this strategy for 3 years had a serious opportunity cost.
2) Getting intra-day data was challenging and expensive at the time.
3) Finding pairs by grid-search (even in the same industries) is expensive and often results from spurious discoveries.


# What others can learn from this?

Some pairs I [traded](https://github.com/deltaray-io/huba-v1/blob/master/config.py) might still show correlation.


# Why is the code not pythonic?

Coming from C/C++ background this was my first serious Python project.

# How did you search for pairs?

The whole solution was migrated to PyPy so that we have reasonable speed. Then machines were crunching data for weeks. 
The pair-scan results are located [here](https://github.com/deltaray-io/huba-v1/tree/master/pairscan).


# What's next?

Over time I have created two additional iterations of the StatArb strategy:
 - [huba-v2](https://github.com/tibkiss/huba-v2) : Using Zipline
 - [huba-v3](https://github.com/tibkiss/huba-v3) : Using QuantConnect's Lean

After these iterations I gave up and moved to Mean Reversion and Momentum Strategies.

Most recently I learned Options Trading and created a [backtester service](https://deltaray.io) for income strategies.

# I made this work, what shall I do now?

If you don't mind sharing with me, that is awesome. 

Drop me a mail at tibor (d0t) kiss (at-sign) gmail (d0t) com.

If you don't feel like sharing, that's also fine. Enjoy the ride! :)

# I have something to say publicly about this strategy.

Please use the [Discussion Board](https://github.com/tibkiss/huba-v1/discussions/).

# Can I buy you a coffee?

[Sure](https://ko-fi.com/tiborkiss), thank you for your consideration!


# What is HUBA?

It is a joke delivered as an acronym: Highly Unorthodox Broker Agent.

I must admit: nothing is unorthodox about this approach (it is well studied). 

When I started developing this strategy Hungary's Minister of Economy [Huba Gyorgy, Matolcsy](https://hu.wikipedia.org/wiki/Matolcsy_Gy%C3%B6rgy_(k%C3%B6zgazd%C3%A1sz))
started campaigning with his 'Unorthodox' approaches. 
I thought this project will be as qualified as his decisions, hence the name.
