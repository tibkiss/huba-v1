TRUNCATE company_events;

INSERT INTO company_events (event_date, symbol, event_source, event_type, event_content)
    SELECT date_filed, ticker, 'EDGAR', NULL, form_type FROM sec_filings;


ALTER TABLE sec_filings DROP CONSTRAINT sec_filings_pkey;


select count(1) from company_events;


create table edgar_sec_filings (
  date_filed date not null,
  symbol varchar not null,
  cik varchar not null,
  form_type varchar not null,
  primary key (date_filed, cik, form_type)
);

alter table sec_filings rename ticker to symbol;

insert into edgar_sec_filings select distinct * from sec_filings;

drop table sec_filings;


select * from sec_filings where date_filed = '2008-02-14' and ticker='OPLK';

--- Get the index sizes
SELECT
    t.tablename,
    indexname,
    c.reltuples AS num_rows,
    pg_size_pretty(pg_relation_size(quote_ident(t.tablename)::text)) AS table_size,
    pg_size_pretty(pg_relation_size(quote_ident(indexrelname)::text)) AS index_size,
    CASE WHEN indisunique THEN 'Y'
       ELSE 'N'
    END AS UNIQUE,
    idx_scan AS number_of_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_tables t
LEFT OUTER JOIN pg_class c ON t.tablename=c.relname
LEFT OUTER JOIN
    ( SELECT c.relname AS ctablename, ipg.relname AS indexname, x.indnatts AS number_of_columns, idx_scan, idx_tup_read, idx_tup_fetch, indexrelname, indisunique FROM pg_index x
           JOIN pg_class c ON c.oid = x.indrelid
           JOIN pg_class ipg ON ipg.oid = x.indexrelid
           JOIN pg_stat_all_indexes psai ON x.indexrelid = psai.indexrelid )
    AS foo
    ON t.tablename = foo.ctablename
WHERE t.schemaname='public'
ORDER BY 1,2;

-- Insert only if not exists
create table foo(symbol varchar, event_date date, content varchar, primary key(symbol, event_date, content));

insert into foo(symbol, event_date, content)
    select 'bar', '2015-04-20', 'bar'
    where not exists(select 1 from foo where symbol='bar' and event_date='2015-04-20' and content='bar')

select * from foo;

drop table foo;


create table yahoo_company_events (
    event_date date not null,
    symbol varchar not null,
    event_type varchar,              -- Upcoming or Recent
    event_content varchar not null,  -- The content of the event
    primary key (event_date, symbol, event_content)
);


select count(1) from yahoo_company_events;


create table company_events (
    event_date date not null,
    symbol varchar not null,
    is_8k boolean,
    is_10k boolean,
    is_10q boolean,
    primary key (event_date, symbol));


truncate company_events;

insert into company_events(event_date, symbol, is_8k, is_10k, is_10q)
    select y.event_date, y.symbol,
      count(case when lower(event_content) like '%8-k%' then 1 end)::int::boolean as is_8k,
      count(case when lower(event_content) like '%10-k%' then 1 end)::int::boolean as is_10k,
      count(case when lower(event_content) like '%10-q%' then 1 end)::int::boolean as is_10q
    from yahoo_company_events as y left outer join company_events on y.event_date = company_events.event_date
      where company_events.event_date is null
      group by y.event_date, y.symbol
      having count(case when lower(event_content) like '%8-k%' then 1 end)::int::boolean = True or
             count(case when lower(event_content) like '%10-k%' then 1 end)::int::boolean = True OR
             count(case when lower(event_content) like '%10-q%' then 1 end)::int::boolean = True
;

insert into company_events(event_date, symbol, is_8k, is_10k, is_10q)
  select date_filed, edgar_sec_filings.symbol,
      count(case when lower(form_type) like '%8-k%' then 1 end)::int::boolean as is_8k,
      count(case when lower(form_type) like '%10-k%' then 1 end)::int::boolean as is_10k,
      count(case when lower(form_type) like '%10-q%' then 1 end)::int::boolean as is_10q
    from edgar_sec_filings left outer join company_events on edgar_sec_filings.date_filed = company_events.event_date
    where company_events.event_date is null
    group by date_filed, edgar_sec_filings.symbol
    having count(case when lower(form_type) like '%8-k%' then 1 end)::int::boolean = true or
           count(case when lower(form_type) like '%10-k%' then 1 end)::int::boolean = true or
           count(case when lower(form_type) like '%10-q%' then 1 end)::int::boolean = true
;

select count(1) from company_events;
delete from company_events where is_8k = False and is_10k = False and is_10q = False;

select * from company_events where lower(symbol) = 'aapl' order by event_date;
