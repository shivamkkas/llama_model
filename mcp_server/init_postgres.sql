-- Initialize PostgreSQL Database for MCP Server

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS public;

-- Example Tables for Testing

-- Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending',
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Logs Table
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    report_type VARCHAR(50),
    generated_by VARCHAR(100),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Sample Data

-- Sample Customers
INSERT INTO customers (name, email, phone) VALUES
    ('John Doe', 'john.doe@example.com', '+1-555-0101'),
    ('Jane Smith', 'jane.smith@example.com', '+1-555-0102'),
    ('Bob Johnson', 'bob.johnson@example.com', '+1-555-0103')
ON CONFLICT (email) DO NOTHING;

-- Sample Transactions
INSERT INTO transactions (customer_id, amount, currency, status, description) VALUES
    (1, 99.99, 'USD', 'completed', 'Product purchase'),
    (1, 149.99, 'USD', 'completed', 'Subscription renewal'),
    (2, 299.99, 'USD', 'pending', 'Service order'),
    (3, 49.99, 'USD', 'completed', 'Digital download');

-- Sample Logs
INSERT INTO logs (level, message, source, metadata) VALUES
    ('INFO', 'System started successfully', 'system', '{"version": "1.0.0"}'),
    ('WARNING', 'High memory usage detected', 'monitoring', '{"memory_percent": 85}'),
    ('ERROR', 'Database connection timeout', 'database', '{"timeout_seconds": 30}');

-- Sample Reports
INSERT INTO reports (title, content, report_type, generated_by) VALUES
    ('Monthly Sales Report', 'Total sales for the month...', 'sales', 'system'),
    ('User Activity Report', 'Active users analysis...', 'analytics', 'admin');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);

-- Create a view for transaction summaries
CREATE OR REPLACE VIEW transaction_summary AS
SELECT 
    c.name AS customer_name,
    c.email,
    COUNT(t.id) AS total_transactions,
    SUM(t.amount) AS total_amount,
    AVG(t.amount) AS average_amount,
    MAX(t.transaction_date) AS last_transaction_date
FROM customers c
LEFT JOIN transactions t ON c.id = t.customer_id
GROUP BY c.id, c.name, c.email;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mcp_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mcp_user;
GRANT SELECT ON transaction_summary TO mcp_user;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL database initialized successfully for MCP Server';
END $$;