CREATE DATABASE tantalus;
CREATE USER simong WITH PASSWORD 'hello';
ALTER ROLE tantalus SET client_encoding TO 'utf8';
ALTER ROLE tantalus SET default_transaction_isolation TO 'read committed';
ALTER ROLE tantalus SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tantalus TO root;
\q