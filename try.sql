
CREATE SCHEMA IF NOT EXISTS loans;


select *
from read_csv('/Users/daria/Desktop/borrowings_tp.csv');

CREATE OR REPLACE VIEW loans.loan_raw AS
select *
from read_csv('/Users/daria/Desktop/borrowings_tp.csv');

