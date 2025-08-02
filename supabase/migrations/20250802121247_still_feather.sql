-- NeuroRAG Database Initialization Script

-- Create database extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding VECTOR(384), -- For pgvector if available
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    query_id UUID,
    user_id VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    data_accessed TEXT[],
    compliance_status VARCHAR(50) DEFAULT 'compliant',
    details TEXT,
    query_text TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

-- Create full-text search index
CREATE INDEX IF NOT EXISTS idx_documents_content_fts ON documents USING GIN(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_documents_title_fts ON documents USING GIN(to_tsvector('english', title));

-- Insert sample data for testing
INSERT INTO documents (title, content, metadata) VALUES 
('Sample Financial Report', 'This is a sample financial report showing quarterly performance metrics and revenue analysis.', '{"classification": "confidential", "tags": ["financial", "report"], "source": "sample"}'),
('Company Policy Document', 'Employee handbook containing company policies, procedures, and compliance guidelines.', '{"classification": "public", "tags": ["policy", "compliance"], "source": "sample"}'),
('Technical Documentation', 'System architecture and API documentation for the NeuroRAG platform.', '{"classification": "confidential", "tags": ["technical", "documentation"], "source": "sample"}')
ON CONFLICT (id) DO NOTHING;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust as needed for your security requirements)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO neurorag;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO neurorag;