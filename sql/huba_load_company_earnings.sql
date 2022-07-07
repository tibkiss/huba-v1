-- Queries to populate company_earnings table from yahoo_company_events and edgar_sec_filings tables

begin;

truncate company_earnings;

insert into company_earnings(event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming)
  select date_filed, upper(edgar_sec_filings.symbol), 'EDGAR',
    count(case when lower(form_type) like '%8-k%' then 1 end)::int::boolean as is_8k,
    count(case when lower(form_type) like '%10-k%' then 1 end)::int::boolean as is_10k,
    count(case when lower(form_type) like '%10-q%' then 1 end)::int::boolean as is_10q,
    false as is_upcoming
  from edgar_sec_filings
  where lower(form_type) not like '%k/a%' and lower(form_type) not like '%q/a%' and
        (lower(form_type) like '%8-k%' or
         lower(form_type) like '%10-k%' or
         lower(form_type) like '%10-q%')
  group by date_filed, edgar_sec_filings.symbol
;

insert into company_earnings(event_date, symbol, source, is_8k, is_10k, is_10q, is_upcoming)
  select event_date, upper(symbol), 'Yahoo',
    count(case when lower(event_content) like '%8-k%' then 1 end)::int::boolean as is_8k,
    count(case when lower(event_content) like '%10-k%' then 1 end)::int::boolean as is_10k,
    count(case when lower(event_content) like '%10-q%' then 1 end)::int::boolean as is_10q,
    count(case when lower(event_content) like '%earnings announcement%' then 1 end)::int::boolean as is_upcoming
  from yahoo_company_events
  where lower(event_content) not like '%k/a%' and lower(event_content) not like '%q/a%' and
        (lower(event_content) like '%8-k%' or
         lower(event_content) like '%10-k%' or
         lower(event_content) like '%10-q%' or
         lower(event_content) like '%earnings announcement%')
  group by event_date, symbol
;

commit;
