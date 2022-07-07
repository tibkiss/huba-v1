"""Database handler module"""

import logging
from collections import namedtuple

import psycopg2cffi

log = logging.getLogger(__name__)


class DBHandler(object):
    yahoo_company_event = namedtuple('YahooCompanyEvent', ('event_date', 'symbol', 'event_type', 'event_content'))
    edgar_sec_filing = namedtuple('EDGARSECFiling', ('date_filed', 'symbol', 'cik', 'form_type'))
    company_earning = namedtuple('CompanyEarning', ('event_date', 'symbol', 'source',
                                                    'is_8k', 'is_10k', 'is_10q', 'is_upcoming'))

    def __init__(self, db_uri):
        self.db_uri = db_uri

        log.info("Connecting to DB: %s" % db_uri)

        self.connection = psycopg2cffi.connect(self.db_uri)
        self.cursor = self.connection.cursor()

    def store_yahoo_company_events(self, company_events, commit=True):
        for company_event in company_events:
            self.store_yahoo_company_event(company_event, commit=False)
        if commit:
            self.connection.commit()

    def store_yahoo_company_event(self, company_event, commit=True):
        query = "INSERT INTO yahoo_company_events(event_date, symbol, event_type, event_content) " \
                " SELECT %s, %s, %s, %s WHERE NOT EXISTS " \
                "    (SELECT 1 FROM yahoo_company_events WHERE " \
                "      event_date = %s and upper(symbol) = upper(%s) and event_content = %s)"
        self.cursor.execute(query,
                            (company_event.event_date, company_event.symbol,
                             company_event.event_type, company_event.event_content,
                             company_event.event_date, company_event.symbol, company_event.event_content))
        if commit:
            self.connection.commit()

    def load_yahoo_company_events(self, symbol):
        self.cursor.execute("SELECT event_date, symbol, event_type, event_content FROM yahoo_company_events "
                            "WHERE upper(symbol) = upper(%s) ORDER BY event_date", (symbol, ))
        result_set = self.cursor.fetchall()

        company_events = []
        for result in result_set:
            event_date, symbol, event_type, event_content = result
            company_events.append(self.yahoo_company_event(event_date, symbol, event_type, event_content))

        return company_events

    def store_edgar_sec_filings(self, sec_filings, commit=True):
        for sec_filing in sec_filings:
            self.store_edgar_sec_filing(sec_filing, commit=False)
        if commit:
            self.connection.commit()

    def store_edgar_sec_filing(self, sec_filing, commit=True):
        self.cursor.execute("INSERT INTO edgar_sec_filings(date_filed, symbol, cik, form_type) "
                             "VALUES (%s, %s, %s, %s)",
                            (sec_filing.date_filed, sec_filing.symbol, sec_filing.cik, sec_filing.form_type))
        if commit:
            self.connection.commit()

    def load_edgar_sec_filings(self, symbol):
        self.cursor.execute("SELECT date_filed, symbol, cik, form_type FROM edgar_sec_filings "
                            "WHERE upper(symbol) = upper(%s) ORDER BY date_filed", (symbol, ))
        result_set = self.cursor.fetchall()

        sec_filings = []
        for result in result_set:
            date_filed, symbol, cik, form_type = result
            sec_filings.append(self.edgar_sec_filing(date_filed, symbol, cik, form_type))

        return sec_filings

    def load_company_earnings(self, symbol, start_date, end_date, is_8k, is_10k, is_10q, is_upcoming):
        log.debug("Loading company earnings for %s between %s - %s", symbol, start_date, end_date)
        self.cursor.execute("SELECT event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming "
                            " FROM company_earnings "
                            " WHERE upper(symbol) = upper(%s) "
                            "       AND (is_8k = %s or is_10k = %s OR is_10q = %s OR is_upcoming = %s) AND "
                            "       event_date BETWEEN %s AND %s "
                            " ORDER BY event_date, source",
                            (symbol, is_8k, is_10k, is_10q, is_upcoming, start_date, end_date))
        result_set = self.cursor.fetchall()

        earnings = []
        for result in result_set:
            event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming = result
            earnings.append(self.company_earning(event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming))

        log.debug("Query yielded %d results", len(earnings))

        return earnings
