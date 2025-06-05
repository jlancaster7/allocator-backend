-- Snowflake Schema for Order Allocation System
-- Run this script in your Snowflake account to create the necessary database and tables

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS ALLOCATIONS_DB;
USE DATABASE ALLOCATIONS_DB;

-- Create schema
CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

-- Create allocations table
CREATE TABLE IF NOT EXISTS allocations (
    allocation_id VARCHAR(100) PRIMARY KEY,
    order_id VARCHAR(100),
    portfolio_group_id VARCHAR(50) NOT NULL,
    security_id VARCHAR(20) NOT NULL,
    allocation_method VARCHAR(50) NOT NULL,
    total_amount NUMBER(20, 2) NOT NULL,
    allocated_amount NUMBER(20, 2) NOT NULL,
    allocation_rate NUMBER(5, 4),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    status VARCHAR(20) DEFAULT 'PREVIEW',
    pre_trade_metrics VARIANT,
    post_trade_metrics VARIANT,
    parameters VARIANT,
    constraints VARIANT
);

-- Create allocation details table (line items per account)
CREATE TABLE IF NOT EXISTS allocation_details (
    allocation_detail_id VARCHAR(100) PRIMARY KEY,
    allocation_id VARCHAR(100) NOT NULL REFERENCES allocations(allocation_id),
    account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(200),
    allocated_quantity NUMBER(20, 2) NOT NULL,
    allocated_notional NUMBER(20, 2) NOT NULL,
    pre_trade_cash NUMBER(20, 2),
    post_trade_cash NUMBER(20, 2),
    pre_trade_metrics VARIANT,
    post_trade_metrics VARIANT,
    warnings VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    username VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    changes VARIANT,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Create user activity table
CREATE TABLE IF NOT EXISTS user_activity (
    activity_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    username VARCHAR(100),
    session_id VARCHAR(100),
    endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code NUMBER(3),
    response_time_ms NUMBER(10),
    request_body VARIANT,
    response_summary VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Create allocation history view for analytics
CREATE OR REPLACE VIEW allocation_history_view AS
SELECT 
    a.allocation_id,
    a.order_id,
    a.portfolio_group_id,
    a.security_id,
    a.allocation_method,
    a.total_amount,
    a.allocated_amount,
    a.allocation_rate,
    a.created_by,
    a.created_at,
    a.status,
    COUNT(ad.allocation_detail_id) as num_accounts,
    SUM(ad.allocated_quantity) as total_allocated_quantity,
    SUM(ad.allocated_notional) as total_allocated_notional
FROM allocations a
LEFT JOIN allocation_details ad ON a.allocation_id = ad.allocation_id
GROUP BY 1,2,3,4,5,6,7,8,9,10,11;


-- Grant permissions (adjust role names as needed)
GRANT USAGE ON DATABASE ALLOCATIONS_DB TO ROLE PUBLIC;
GRANT USAGE ON SCHEMA PUBLIC TO ROLE PUBLIC;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA PUBLIC TO ROLE PUBLIC;
GRANT SELECT ON ALL VIEWS IN SCHEMA PUBLIC TO ROLE PUBLIC;

-- Show created objects
SHOW TABLES;
SHOW VIEWS;