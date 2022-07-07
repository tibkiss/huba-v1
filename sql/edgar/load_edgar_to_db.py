__author__ = 'tiborkiss'

import psycopg2
import pandas as pd
from bs4 import BeautifulSoup
import re
import urllib2
import sys


db_connection = psycopg2.connect(database='huba', host='192.168.211.31', user='tiborkiss', password='dbSh1t')
db_cursor = db_connection.cursor()

def load_edgar_master_to_db():
    base_path = '/Users/tiborkiss/devel/workspace/stocks/edgar/full-index'
    for year in range(2008, 2016):
        for qtr in ('QTR1', 'QTR2', 'QTR3', 'QTR4'):
            filename = base_path + '/%s/%s/master-converted.csv.gz' % (year, qtr)

            print 'Processing: ', filename

            input_data = pd.read_csv(filename, delimiter='|')

            for _, row in input_data.iterrows():
                sql_template = "INSERT INTO sec_filings(date_filed, symbol, cik, form_type) VALUES ('{0}', (SELECT symbol FROM cik_to_symbol WHERE cik='{1}'), '{1}', '{2}')"
                sql_query = sql_template.format(row['Date Filed'], row['CIK'], row['Form Type'])
                try:
                    db_cursor.execute(sql_query)
                except psycopg2.IntegrityError:
                    db_cursor.execute('ROLLBACK')
                else:
                    db_cursor.execute('COMMIT')


def get_cik_and_company_name_for_symbol(symbol):
    page = urllib2.urlopen('http://www.sec.gov/cgi-bin/browse-edgar?CIK=%s&owner=exclude&action=getcompany&Find=Search' % symbol)

    soup = BeautifulSoup(page.read(), 'lxml')
    companyNameSpan = soup.find('span', {'class': 'companyName'})
    #print companyNameSpan
    h1 = soup.find('h1')
    if h1 is not None:
        if str(h1).find('No matching Ticker Symbol') != -1:
            return None, None

    cik = re.findall(r'CIK=(\d*)\&', str(companyNameSpan), re.IGNORECASE)
    companyName = re.findall(r'<span class=\"companyName\">(.*)<acronym', str(companyNameSpan), re.IGNORECASE)
    #print soup.find(regex=re.compile(r'CIK=(\d*)\&', re.IGNORECASE))

    #print cik, companyName
    return cik[0], companyName[0]


def get_huba_all_symbols():
    base_path = '/Users/tiborkiss/devel/workspace/stocks/edgar/'
    filename = '%s/huba-all-symbols.txt' % base_path
    symbols = []

    with open(filename, 'r') as f:
        for row in f:
            symbols.append(row.rstrip())
    return symbols


def load_missing_cik_to_symbol():
    all_symbols = get_huba_all_symbols()

    for symbol in all_symbols:
        db_cursor.execute("SELECT count(1) FROM cik_to_symbol WHERE symbol=%s", (symbol,))
        count = db_cursor.fetchone()

        #print symbol, count
        if int(count[0]) == 0:
            cik, company_name = get_cik_and_company_name_for_symbol(symbol)
            print 'resolved missing: %s -> %s' % (symbol, cik)
            sys.stdout.flush()

            if cik is not None:
                db_cursor.execute("INSERT INTO cik_to_symbol (cik, symbol, company_name) VALUES (%s, %s, %s)",
                                  (cik, symbol, company_name))


# load_missing_cik_to_symbol()
load_edgar_master_to_db()
