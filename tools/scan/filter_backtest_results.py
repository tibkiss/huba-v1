import pandas as pd
import yql
from IPython import embed
import sys

proxy = False
if proxy:
    import tools.socks as socks
    import socket
    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 11080)
    socket.socket = socks.socksocket


def filter_results(csvFiles, maxDDPct=15.0, maxDDLen=150, minSharpe=1.3):
    # Load all the stocks from the csv files
    bt_results = pd.DataFrame()
    for csvFile in csvFiles:
        print 'Loading file: ', csvFile
        bt_results = bt_results.append(pd.read_csv(csvFile))
    print 'Loaded %d entries from the CSV Files' % len(bt_results)

    # Filter the results based on the DD & Sharpe criteria
    # TODO: Add DD Duration to the CSV files
    bt_results = bt_results[(bt_results['MaxDD'] <= maxDDPct) &
                            (bt_results['Sharpe'] >= minSharpe)]

    print "Sharpe & MaxDD Filter yielded %d results" % len(bt_results)

    # Create cache for the queries from yahoo
    yCache = {}

    # Download volume and 52 week lows from yahoo
    avgDailyVolumes = {0: [], 1: []}
    yearLows = {0: [], 1: []}

    # Create YQL connection
    y = yql.Public()

    # Walk through all the results
    for i in bt_results.index:
        # The pair is located in the second column of the csv with the format: [('Stock1'), ('Stock2')]
        pair = bt_results.ix[i]['Pairs']

        # Convert the format into tuple of instruments
        pair = pair.replace("[(", "").replace(")]", "").replace("'", "").replace(",","").split(" ")

        print 'Processing pair: %s' % pair

        # Query both instruments from volume
        for s, stock in enumerate(pair):
            if stock not in yCache:
                retryCnt = 6

                while retryCnt:
                    query = 'use "http://www.datatables.org/yahoo/finance/yahoo.finance.quotes.xml" as yahoo.finance.quotes;' \
                            'select AverageDailyVolume, YearLow from yahoo.finance.quotes where symbol = "%s"' % stock

                    yres = y.execute(query)

                    if len(yres.rows) == 0:
                        # Failed to download, retry if possible
                        avgDailyVolume = yearLow = pd.np.NaN
                        retryCnt -= 1
                        continue
                    else:
                        # Download succeeded, cache the value
                        yCache[stock] = yres

                        try:
                            avgDailyVolume = float(yCache[stock].rows[0]['AverageDailyVolume'])
                            yearLow = float(yCache[stock].rows[0]['YearLow'])
                        except TypeError:
                            avgDailyVolume = pd.np.NaN
                            yearLow = pd.np.NaN
                        retryCnt = 0
            else:
                # Load from the cache
                try:
                    avgDailyVolume = float(yCache[stock].rows[0]['AverageDailyVolume'])
                    yearLow = float(yCache[stock].rows[0]['YearLow'])
                except TypeError:
                    avgDailyVolume = pd.np.NaN
                    yearLow = pd.np.NaN

            # Add to the data series
            avgDailyVolumes[s].append(avgDailyVolume)
            yearLows[s].append(yearLow)

            #print '%s: %f %f' % (stock, avgDailyVolume, yearLow)

    # Add the volume and yearlow field to the Data series
    bt_results['AvgDailyVolumes0'] = pd.Series(avgDailyVolumes[0], index=bt_results.index)
    bt_results['YearLows0'] = pd.Series(yearLows[0], index=bt_results.index)
    bt_results['AvgDailyVolumes1'] = pd.Series(avgDailyVolumes[1], index=bt_results.index)
    bt_results['YearLows1'] = pd.Series(yearLows[1], index=bt_results.index)


    # Filter for volume
    # Max investment: $200k/10 pair = $10k per stock
    # Maximal stock count (max 1% of daily vol): ($10k/YearLow) * 100
    maxCapitalPerStock = 10000
    bt_results['VolumeCriteriaMet'] = ((bt_results['AvgDailyVolumes0'] >= ((maxCapitalPerStock / bt_results['YearLows0']) * 100)) &
                                       (bt_results['AvgDailyVolumes1'] >= ((maxCapitalPerStock / bt_results['YearLows1']) * 100)))

    # Sort results by Sharpe
    bt_results = bt_results.sort('Sharpe')

    print "Volume Filter yielded %d results" % len(bt_results)

    embed()


if __name__ == '__main__':
    filter_results(sys.argv[1:])
