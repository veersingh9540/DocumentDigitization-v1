-- Create document_metadata table
CREATE TABLE IF NOT EXISTS document_metadata (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) NOT NULL UNIQUE,
    original_bucket VARCHAR(255) NOT NULL,
    original_key VARCHAR(255) NOT NULL,
    processed_bucket VARCHAR(255) NOT NULL,
    processed_key VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    page_count INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Create document_fields table
CREATE TABLE IF NOT EXISTS document_fields (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    field_value TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES document_metadata(document_id) ON DELETE CASCADE
);

-- Create indices for better query performance
CREATE INDEX IF NOT EXISTS idx_document_metadata_document_id ON document_metadata(document_id);
CREATE INDEX IF NOT EXISTS idx_document_metadata_document_type ON document_metadata(document_type);
CREATE INDEX IF NOT EXISTS idx_document_metadata_status ON document_metadata(status);
CREATE INDEX IF NOT EXISTS idx_document_metadata_created_at ON document_metadata(created_at);
CREATE INDEX IF NOT EXISTS idx_document_fields_document_id ON document_fields(document_id);
CREATE INDEX IF NOT EXISTS idx_document_fields_field_name ON document_fields(field_name);

-- Create view for document statistics
CREATE OR REPLACE VIEW document_statistics AS
SELECT
    COUNT(*) AS total_documents,
    document_type,
    COUNT(*) AS type_count,
    MIN(created_at) AS first_document_date,
    MAX(created_at) AS last_document_date
FROM
    document_metadata
GROUP BY
    document_type;

-- Create function to get document counts by day for the last N days
CREATE OR REPLACE FUNCTION get_document_counts_by_day(days_back INTEGER DEFAULT 7)
RETURNS TABLE (
    day DATE,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH date_range AS (
        SELECT generate_series(
            current_date - (days_back - 1)::INTEGER,
            current_date,
            '1 day'::INTERVAL
        )::DATE AS day
    )
    SELECT
        date_range.day,
        COUNT(dm.id)::BIGINT
    FROM
        date_range
    LEFT JOIN
        document_metadata dm ON DATE(dm.created_at) = date_range.day
    GROUP BY
        date_range.day
    ORDER BY
        date_range.day;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_document_metadata_modtime
BEFORE UPDATE ON document_metadata
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Add some sample document types for testing (optional)
INSERT INTO document_metadata (document_id, original_bucket, original_key, processed_bucket, processed_key, document_type, page_count, status)
VALUES
    ('sample-invoice-001', 'test-bucket', 'uploads/sample-invoice.pdf', 'test-bucket', 'processed/sample-invoice-001.json', 'invoice', 1, 'processed'),
    ('sample-report-001', 'test-bucket', 'uploads/sample-report.pdf', 'test-bucket', 'processed/sample-report-001.json', 'report', 3, 'processed'),
    ('sample-contract-001', 'test-bucket', 'uploads/sample-contract.pdf', 'test-bucket', 'processed/sample-contract-001.json', 'contract', 5, 'processed')
ON CONFLICT (document_id) DO NOTHING;

-- Add sample fields for the documents (optional)
INSERT INTO document_fields (document_id, field_name, field_value)
VALUES
    ('sample-invoice-001', 'invoice_number', 'INV-12345'),
    ('sample-invoice-001', 'date', '2023-06-15'),
    ('sample-invoice-001', 'total_amount', '1250.00'),
    ('sample-invoice-001', 'vendor', 'ACME Corporation'),
    ('sample-report-001', 'report_name', 'Annual Financial Report'),
    ('sample-report-001', 'year', '2023'),
    ('sample-contract-001', 'contract_id', 'C-987654'),
    ('sample-contract-001', 'start_date', '2023-01-01'),
    ('sample-contract-001', 'end_date', '2023-12-31')
ON CONFLICT DO NOTHING;
