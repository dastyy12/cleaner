-- Initialize PostgreSQL database for crypto signals

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create user preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id BIGINT PRIMARY KEY,
    symbols TEXT[],
    exchanges TEXT[],
    timeframes TEXT[],
    min_confidence FLOAT DEFAULT 60.0,
    max_leverage INTEGER DEFAULT 10,
    enabled_methods TEXT[],
    max_risk_per_trade FLOAT DEFAULT 2.0,
    mute_until TIMESTAMP,
    daily_report BOOLEAN DEFAULT TRUE,
    weekly_report BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create signals table
CREATE TABLE IF NOT EXISTS signals (
    id VARCHAR(50) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    entry_price FLOAT NOT NULL,
    stop_loss FLOAT NOT NULL,
    take_profits FLOAT[],
    confidence FLOAT NOT NULL,
    expected_rr FLOAT NOT NULL,
    probability_success FLOAT,
    reasons JSONB,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    triggered_at TIMESTAMP,
    closed_at TIMESTAMP,
    pnl FLOAT
);

-- Create signal performance tracking table
CREATE TABLE IF NOT EXISTS signal_performance (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(50) REFERENCES signals(id),
    method VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    confidence FLOAT NOT NULL,
    success BOOLEAN,
    pnl_percent FLOAT,
    duration_hours FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_exchange ON signals(exchange);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signal_performance_symbol ON signal_performance(symbol);
CREATE INDEX IF NOT EXISTS idx_signal_performance_method ON signal_performance(method);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for user_preferences
CREATE TRIGGER update_user_preferences_updated_at 
    BEFORE UPDATE ON user_preferences 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default analysis methods
INSERT INTO user_preferences (user_id, enabled_methods) 
VALUES (0, ARRAY['technical_analysis', 'smart_money_concepts', 'elliott_wave', 'harmonic_patterns'])
ON CONFLICT (user_id) DO NOTHING;