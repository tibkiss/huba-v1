
-- Table to translate EDGAR's CIK to Ticker
-- Initial data obtained from: http://rankandfiled.com/#/data/tickers
-- Later enriched using EDGAR's lookup
create table cik_to_symbol (
    cik varchar not null,
    symbol varchar not null,
    company_name varchar,
    exchange varchar,
    sic varchar,
    business varchar,
    incorporated varchar,
    irs varchar,
    primary key (cik, symbol)
);

-- Table to store SEC Filings from EDGAR
create table edgar_sec_filings (
    date_filed date not null,
    symbol varchar not null,
    cik varchar not null,
    form_type varchar not null,
    primary key (date_filed, cik, form_type)
);

-- Table to store Yahoo Finance company events
create table yahoo_company_events (
    event_date date not null,
    symbol varchar not null,
    event_type varchar,              -- Upcoming or Recent
    event_content varchar not null,  -- The content of the event
    primary key (event_date, symbol, event_content)
);

-- Company event aggregator table, populated by edgar_sec_filings and yahoo_company_events
create table company_earnings (
    event_date date not null,
    symbol varchar not null,
    source varchar not null,
    is_8k boolean,
    is_10k boolean,
    is_10q boolean,
    is_upcoming boolean,
    primary key (event_date, symbol, source)
);

