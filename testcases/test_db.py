
from decimal import Decimal
import datetime

import pytest

import psycopg2cffi

from config import HUBA_DB_URI, HUBA_TEST_DB_URI
from tools.db import DBHandler

@pytest.fixture(scope="module")
def db_handler():
    return DBHandler(HUBA_TEST_DB_URI)

def cleanup(cursor):
    cursor.execute("DROP TABLE edgar_sec_filings;")
    cursor.execute("DROP TABLE cik_to_symbol;")
    cursor.execute("DROP TABLE yahoo_company_events;")
    cursor.execute("DROP TABLE company_earnings;")

def test_huba_db_sql_scripts(db_handler):
    cursor = db_handler.cursor
    connection = db_handler.connection

    cleanup(cursor)

    # Create the DB Tables in test DB. Will throw exception on error
    cursor.execute(open('sql/huba_db_ddl.sql', 'r').read())

    cursor.execute("INSERT INTO edgar_sec_filings VALUES('2015-04-20', 'AAPL', '123', '10-K')") # 10-K and 10-Q should merge into one cell
    cursor.execute("INSERT INTO edgar_sec_filings VALUES('2015-04-20', 'AAPL', '123', '10-Q')")
    cursor.execute("INSERT INTO edgar_sec_filings VALUES('2015-04-21', 'AAPL', '123', '8-K')")
    cursor.execute("INSERT INTO yahoo_company_events VALUES('2015-04-20', 'AAPL', 'recent', 'APPLE INC Files SEC form 10-K, Annual Report')")
    cursor.execute("INSERT INTO yahoo_company_events VALUES('2015-04-20', 'AAPL', 'recent', 'APPLE INC Files SEC form 10-Q, Quarterly Report')")
    cursor.execute("INSERT INTO yahoo_company_events VALUES('2015-04-22', 'AAPL', 'recent', 'APPLE INC Files SEC form 8-K, Change in Directors or Principal Officers')")
    cursor.execute("INSERT INTO yahoo_company_events VALUES('2015-04-23', 'AAPL', 'recent', 'Ex-Date for dividend payment of $0.52')")
    cursor.execute("INSERT INTO yahoo_company_events VALUES('2015-06-20', 'AAPL', 'upcoming', 'Earnings announcement')")

    # Execute the load script
    cursor.execute(open('sql/huba_load_company_earnings.sql', 'r').read())

    # Ensure that we have two events created in the result table
    cursor.execute("SELECT event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming "
                   "FROM company_earnings ORDER BY event_date, source")

    result_set = cursor.fetchall()

    assert len(result_set) == 5

    event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming = result_set[0]
    assert event_date == datetime.date(2015, 4, 20)
    assert symbol == 'AAPL'
    assert source == 'EDGAR'
    assert is_8k is False and is_10k is True and is_10q is True and is_upcoming is False

    event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming = result_set[1]
    assert event_date == datetime.date(2015, 4, 20)
    assert symbol == 'AAPL'
    assert source == 'Yahoo'
    assert is_8k is False and is_10k is True and is_10q is True and is_upcoming is False

    event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming = result_set[2]
    assert event_date == datetime.date(2015, 4, 21)
    assert symbol == 'AAPL'
    assert source == 'EDGAR'
    assert is_8k is True and is_10k is False and is_10q is False and is_upcoming is False

    event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming = result_set[3]
    assert event_date == datetime.date(2015, 4, 22)
    assert symbol == 'AAPL'
    assert source == 'Yahoo'
    assert is_8k is True and is_10k is False and is_10q is False and is_upcoming is False

    event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming = result_set[4]
    assert event_date == datetime.date(2015, 6, 20)
    assert symbol == 'AAPL'
    assert source == 'Yahoo'
    assert is_8k is False and is_10k is False and is_10q is False and is_upcoming is True


def test_huba_db_connectability():
    connection = psycopg2cffi.connect(HUBA_DB_URI)
    cursor = connection.cursor()

    cursor.execute("SELECT 3.14;")
    db_result = cursor.fetchall()

    assert len(db_result) == 1
    assert db_result[0] == (Decimal('3.14'), )


def test_store_yahoo_company_event(db_handler):
    cleanup(db_handler.cursor)

    db_handler.cursor.execute(open('sql/huba_db_ddl.sql', 'r').read())

    db_handler.store_yahoo_company_events([DBHandler.yahoo_company_event(event_date='2015-06-12', symbol='IBM',
                                                                         event_type='upcoming',
                                                                         event_content='Earnings announcement'),
                                          DBHandler.yahoo_company_event(event_date='2015-05-10', symbol='IBM',
                                                                        event_type='recent',
                                                                        event_content='whatevs')], commit=False)

    results = db_handler.load_yahoo_company_events('IBM')
    assert len(results) == 2
    assert results[0].event_date == datetime.date(2015, 5, 10)
    assert results[0].symbol == 'IBM'
    assert results[0].event_type == 'recent'
    assert results[0].event_content == 'whatevs'

    assert results[1].event_date == datetime.date(2015, 6, 12)
    assert results[1].symbol == 'IBM'
    assert results[1].event_type == 'upcoming'
    assert results[1].event_content == 'Earnings announcement'


def test_edgar_sec_filings(db_handler):
    cleanup(db_handler.cursor)

    db_handler.cursor.execute(open('sql/huba_db_ddl.sql', 'r').read())

    # Insert test data to the tables
    db_handler.store_edgar_sec_filings([DBHandler.edgar_sec_filing(date_filed='2015-07-07', symbol='AAPL',
                                                                   cik='0123', form_type='10-K'),
                                        DBHandler.edgar_sec_filing(date_filed='2015-08-08', symbol='GE',
                                                                   cik='0124', form_type='ZZ1')], commit=False)

    results = db_handler.load_edgar_sec_filings('AAPL')

    assert len(results) == 1
    assert results[0].date_filed == datetime.date(2015, 7, 7)
    assert results[0].symbol == 'AAPL'
    assert results[0].cik == '0123'
    assert results[0].form_type == '10-K'

    results = db_handler.load_edgar_sec_filings('GE')
    assert results[0].date_filed == datetime.date(2015, 8, 8)
    assert results[0].symbol == 'GE'
    assert results[0].cik == '0124'
    assert results[0].form_type == 'ZZ1'

def test_load_company_earnings(db_handler):
    cleanup(db_handler.cursor)

    db_handler.cursor.execute(open('sql/huba_db_ddl.sql', 'r').read())

    # Insert test data to the tables
    db_handler.store_edgar_sec_filings([
                                        DBHandler.edgar_sec_filing(date_filed='2015-04-08', symbol='DATA',
                                                                   cik='0123', form_type='10-K'),
                                        DBHandler.edgar_sec_filing(date_filed='2015-04-08', symbol='DATA',
                                                                   cik='0123', form_type='8-K'),
                                        DBHandler.edgar_sec_filing(date_filed='2015-08-08', symbol='DATA',
                                                                   cik='0123', form_type='10-K'),
                                        DBHandler.edgar_sec_filing(date_filed='2015-08-08', symbol='DATA',
                                                                   cik='0123', form_type='10-Q'),
                                        DBHandler.edgar_sec_filing(date_filed='2015-08-22', symbol='RACE',
                                                                   cik='0124', form_type='10-Q'),
                                        DBHandler.edgar_sec_filing(date_filed='2015-08-24', symbol='RACE',
                                                                   cik='0124', form_type='10-Q/A'),
                                        DBHandler.edgar_sec_filing(date_filed='2015-08-28', symbol='RACE',
                                                                   cik='0124', form_type='10-K/A'),
                                        DBHandler.edgar_sec_filing(date_filed='2015-08-30', symbol='RACE',
                                                                   cik='0124', form_type='8-K/A'),
                                        ],
                                       commit=False)
    db_handler.store_yahoo_company_events([
                                           DBHandler.yahoo_company_event(event_date='2015-08-12', symbol='DATA',
                                                                         event_type='upcoming',
                                                                         event_content='Earnings announcement'),
                                           DBHandler.yahoo_company_event(event_date='2015-08-08', symbol='DATA',
                                                                         event_type='recent',
                                                                         event_content='TABLEAU SOFTWARE INC Files SEC form 10-Q, Quarterly Report'),
                                           DBHandler.yahoo_company_event(event_date='2015-08-08', symbol='DATA',
                                                                         event_type='recent',
                                                                         event_content='TABLEAU SOFTWARE INC Files SEC form 10-K, Annual Report'),
                                           DBHandler.yahoo_company_event(event_date='2015-08-06', symbol='DATA',
                                                                         event_type='recent',
                                                                         event_content='Ex-Date for dividend payment of $1.30'),
                                           DBHandler.yahoo_company_event(event_date='2015-08-18', symbol='FAA',
                                                                         event_type='recent',
                                                                         event_content='FAA WHATEVS ENV Files SEC form 10-K/A, Nyente 1'),
                                           DBHandler.yahoo_company_event(event_date='2015-08-19', symbol='FAA',
                                                                         event_type='recent',
                                                                         event_content='FAA WHATEVS ENV Files SEC form 10-Q/A, Nyente 2'),
                                           DBHandler.yahoo_company_event(event_date='2015-08-21', symbol='FAA',
                                                                         event_type='recent',
                                                                         event_content='FAA WHATEVS ENV Files SEC form 8-K/A, Nyente 3'),
                                           ],
                                          commit=False)

    db_handler.cursor.execute(open('sql/huba_load_company_earnings.sql', 'r').read())

    # For the symbol + date range filter the 2015-08-08 earning (by edgar & yahoo) and the 2015-08-12 upcoming yahoo
    # earning should appear
    results = db_handler.load_company_earnings('DATA', '2015-08-01', '2015-08-30', True, True, True, True)
    assert len(results) == 3

    assert results[0].event_date == datetime.date(2015, 8, 8)
    assert results[0].symbol == 'DATA'
    assert results[0].source in ('Yahoo', 'EDGAR')
    assert results[0].is_8k is False
    assert results[0].is_10k is True and results[0].is_10q is True
    assert results[0].is_upcoming is False

    assert results[1].event_date == datetime.date(2015, 8, 8)
    assert results[1].symbol == 'DATA'
    assert results[1].source in ('Yahoo', 'EDGAR')
    assert results[1].is_8k is False
    assert results[1].is_10k is True and results[1].is_10q is True
    assert results[1].is_upcoming is False

    assert results[2].event_date == datetime.date(2015, 8, 12)
    assert results[2].symbol == 'DATA'
    assert results[2].source == 'Yahoo'
    assert results[2].is_8k is False
    assert results[2].is_10k is False and results[2].is_10q is False and results[2].is_upcoming is True

    # For the symbol + date range filter the 2015-04-01, 2015-08-08 and 2015-08-12 events should appear
    results = db_handler.load_company_earnings('DATA', '2015-01-01', '2015-12-30', True, True, True, True)
    assert len(results) == 4
    assert results[0].event_date == datetime.date(2015, 4, 8)
    assert results[0].symbol == 'DATA'
    assert results[0].source == 'EDGAR'
    assert results[0].is_10k is True and results[0].is_10q is False and results[0].is_upcoming is False

    # Load the lonely event for RACE
    results = db_handler.load_company_earnings('RACE', '2015-01-01', '2015-12-30', True, True, True, True)
    assert len(results) == 1
    assert results[0].event_date == datetime.date(2015, 8, 22)
    assert results[0].symbol == 'RACE'
    assert results[0].source == 'EDGAR'
    assert results[0].is_10k is False and results[0].is_10q is True and results[0].is_upcoming is False


    results = db_handler.load_company_earnings('FAA', '2015-01-01', '2015-12-31', True, True, True, True)
    assert len(results) == 0

