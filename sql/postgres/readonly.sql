-- Apply after migrations 001-004 using the local PostgreSQL owner/admin.
-- Set a private password out of band: \password foody_ai_readonly in psql.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'foody_ai_readonly') THEN
    CREATE ROLE foody_ai_readonly LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
  END IF;
END $$;
ALTER ROLE foody_ai_readonly NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
GRANT CONNECT ON DATABASE foody TO foody_ai_readonly;
CREATE SCHEMA IF NOT EXISTS ai_sales;
REVOKE ALL ON SCHEMA ai_sales FROM PUBLIC;
REVOKE ALL ON SCHEMA ai_sales FROM foody_ai_readonly;
GRANT USAGE ON SCHEMA ai_sales TO foody_ai_readonly;
CREATE OR REPLACE VIEW ai_sales.dim_sales_restaurant AS
  SELECT restaurant_id, restaurant_name FROM public.dim_sales_restaurant;
CREATE OR REPLACE VIEW ai_sales.restaurant_monthly_sales AS
  SELECT * FROM public.restaurant_monthly_sales;
CREATE OR REPLACE VIEW ai_sales.restaurant_weekly_sales AS
  SELECT * FROM public.restaurant_weekly_sales;
CREATE OR REPLACE VIEW ai_sales.restaurant_sales_summary AS
  SELECT * FROM public.restaurant_sales_summary;
REVOKE ALL ON ALL TABLES IN SCHEMA ai_sales FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA ai_sales FROM foody_ai_readonly;
GRANT SELECT ON ai_sales.dim_sales_restaurant,
  ai_sales.restaurant_monthly_sales,
  ai_sales.restaurant_weekly_sales,
  ai_sales.restaurant_sales_summary TO foody_ai_readonly;
ALTER ROLE foody_ai_readonly SET search_path = ai_sales;
