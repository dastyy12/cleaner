"""
Storage Manager - handles data persistence to ClickHouse, Redis, and PostgreSQL
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import json

# Database imports
import clickhouse_driver
import redis.asyncio as redis
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from config import settings

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages data storage across multiple databases"""
    
    def __init__(self):
        # ClickHouse for time-series data (ticks, klines, trades)
        self.clickhouse_client = None
        
        # Redis for caching and real-time features
        self.redis_client = None
        
        # PostgreSQL for configuration and user data
        self.postgres_engine = None
        
        # Connection status
        self.initialized = False
    
    async def initialize(self):
        """Initialize all database connections"""
        logger.info("🔄 Initializing storage connections...")
        
        try:
            # Initialize ClickHouse
            await self._init_clickhouse()
            
            # Initialize Redis
            await self._init_redis()
            
            # Initialize PostgreSQL
            await self._init_postgres()
            
            self.initialized = True
            logger.info("✅ Storage Manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Storage initialization failed: {e}")
            raise
    
    async def _init_clickhouse(self):
        """Initialize ClickHouse connection and create tables"""
        try:
            self.clickhouse_client = clickhouse_driver.Client(
                host=settings.database.clickhouse_host,
                port=settings.database.clickhouse_port,
                database=settings.database.clickhouse_database
            )
            
            # Test connection
            self.clickhouse_client.execute("SELECT 1")
            
            # Create tables if they don't exist
            await self._create_clickhouse_tables()
            
            logger.info("✅ ClickHouse connected")
            
        except Exception as e:
            logger.error(f"❌ ClickHouse connection failed: {e}")
            raise
    
    async def _create_clickhouse_tables(self):
        """Create ClickHouse tables for market data"""
        
        # Tickers table
        ticker_table = """
        CREATE TABLE IF NOT EXISTS tickers (
            timestamp DateTime64(3),
            exchange String,
            symbol String,
            price Float64,
            volume Float64,
            change Float64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (exchange, symbol, timestamp)
        """
        
        # Klines table
        klines_table = """
        CREATE TABLE IF NOT EXISTS klines (
            timestamp DateTime64(3),
            exchange String,
            symbol String,
            timeframe String,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume Float64
        ) ENGINE = MergeTree()
        PARTITION BY (exchange, toYYYYMM(timestamp))
        ORDER BY (exchange, symbol, timeframe, timestamp)
        """
        
        # Trades table
        trades_table = """
        CREATE TABLE IF NOT EXISTS trades (
            timestamp DateTime64(3),
            exchange String,
            symbol String,
            price Float64,
            quantity Float64,
            is_buyer_maker UInt8
        ) ENGINE = MergeTree()
        PARTITION BY (exchange, toYYYYMM(timestamp))
        ORDER BY (exchange, symbol, timestamp)
        """
        
        # Orderbook table
        orderbook_table = """
        CREATE TABLE IF NOT EXISTS orderbooks (
            timestamp DateTime64(3),
            exchange String,
            symbol String,
            bids Array(Array(Float64)),
            asks Array(Array(Float64))
        ) ENGINE = MergeTree()
        PARTITION BY (exchange, toYYYYMM(timestamp))
        ORDER BY (exchange, symbol, timestamp)
        TTL timestamp + INTERVAL 7 DAY
        """
        
        # Execute table creation
        tables = [ticker_table, klines_table, trades_table, orderbook_table]
        for table_sql in tables:
            self.clickhouse_client.execute(table_sql)
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=settings.database.redis_host,
                port=settings.database.redis_port,
                db=settings.database.redis_db,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            
            logger.info("✅ Redis connected")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    async def _init_postgres(self):
        """Initialize PostgreSQL connection"""
        try:
            connection_string = (
                f"postgresql+asyncpg://{settings.database.postgres_user}:"
                f"{settings.database.postgres_password}@"
                f"{settings.database.postgres_host}:"
                f"{settings.database.postgres_port}/"
                f"{settings.database.postgres_db}"
            )
            
            self.postgres_engine = create_async_engine(connection_string)
            
            # Test connection
            async with self.postgres_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            # Create tables
            await self._create_postgres_tables()
            
            logger.info("✅ PostgreSQL connected")
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise
    
    async def _create_postgres_tables(self):
        """Create PostgreSQL tables for configuration and signals"""
        
        # User preferences table
        user_prefs_table = """
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
        )
        """
        
        # Signals table
        signals_table = """
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
        )
        """
        
        # Signal performance tracking
        performance_table = """
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
        )
        """
        
        # Execute table creation
        tables = [user_prefs_table, signals_table, performance_table]
        
        async with self.postgres_engine.begin() as conn:
            for table_sql in tables:
                await conn.execute(text(table_sql))
    
    # ClickHouse storage methods
    async def store_ticker(self, exchange: str, symbol: str, data: Dict):
        """Store ticker data in ClickHouse"""
        try:
            self.clickhouse_client.execute(
                "INSERT INTO tickers (timestamp, exchange, symbol, price, volume, change) VALUES",
                [(
                    data['timestamp'],
                    exchange,
                    symbol,
                    data['price'],
                    data['volume'],
                    data['change']
                )]
            )
        except Exception as e:
            logger.error(f"Error storing ticker data: {e}")
    
    async def store_kline(self, exchange: str, symbol: str, timeframe: str, data: Dict):
        """Store kline data in ClickHouse"""
        try:
            self.clickhouse_client.execute(
                "INSERT INTO klines (timestamp, exchange, symbol, timeframe, open, high, low, close, volume) VALUES",
                [(
                    data['timestamp'],
                    exchange,
                    symbol,
                    timeframe,
                    data['open'],
                    data['high'],
                    data['low'],
                    data['close'],
                    data['volume']
                )]
            )
        except Exception as e:
            logger.error(f"Error storing kline data: {e}")
    
    async def store_trade(self, exchange: str, symbol: str, data: Dict):
        """Store trade data in ClickHouse"""
        try:
            self.clickhouse_client.execute(
                "INSERT INTO trades (timestamp, exchange, symbol, price, quantity, is_buyer_maker) VALUES",
                [(
                    data['timestamp'],
                    exchange,
                    symbol,
                    data['price'],
                    data['quantity'],
                    1 if data.get('is_buyer_maker', False) else 0
                )]
            )
        except Exception as e:
            logger.error(f"Error storing trade data: {e}")
    
    async def store_orderbook(self, exchange: str, symbol: str, data: Dict):
        """Store orderbook data in ClickHouse (sampled)"""
        try:
            # Only store every 10 seconds to avoid spam
            cache_key = f"orderbook_last_{exchange}_{symbol}"
            last_stored = await self.redis_client.get(cache_key)
            
            now = datetime.utcnow()
            if last_stored:
                last_time = datetime.fromisoformat(last_stored)
                if (now - last_time).total_seconds() < 10:
                    return
            
            self.clickhouse_client.execute(
                "INSERT INTO orderbooks (timestamp, exchange, symbol, bids, asks) VALUES",
                [(
                    data['timestamp'],
                    exchange,
                    symbol,
                    data['bids'][:20],  # Store top 20 levels
                    data['asks'][:20]
                )]
            )
            
            # Update cache
            await self.redis_client.set(cache_key, now.isoformat(), ex=60)
            
        except Exception as e:
            logger.error(f"Error storing orderbook data: {e}")
    
    async def get_historical_klines(self, 
                                    exchange: str, 
                                    symbol: str, 
                                    timeframe: str, 
                                    limit: int = 1000) -> pd.DataFrame:
        """Get historical klines from ClickHouse"""
        try:
            query = """
            SELECT timestamp, open, high, low, close, volume
            FROM klines
            WHERE exchange = %(exchange)s 
            AND symbol = %(symbol)s 
            AND timeframe = %(timeframe)s
            ORDER BY timestamp DESC
            LIMIT %(limit)s
            """
            
            result = self.clickhouse_client.execute(
                query,
                {
                    'exchange': exchange,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'limit': limit
                }
            )
            
            if result:
                df = pd.DataFrame(
                    result, 
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df.set_index('timestamp', inplace=True)
                return df.sort_index()
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting historical klines: {e}")
            return pd.DataFrame()
    
    # Redis cache methods
    async def cache_set(self, key: str, value: Any, expire: int = 3600):
        """Set value in Redis cache"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.redis_client.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            value = await self.redis_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Error getting cache: {e}")
            return None
    
    async def cache_delete(self, key: str):
        """Delete key from Redis cache"""
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting cache: {e}")
    
    # PostgreSQL methods
    async def store_signal(self, signal_data: Dict):
        """Store signal in PostgreSQL"""
        try:
            query = """
            INSERT INTO signals (
                id, symbol, exchange, direction, timeframe, entry_price,
                stop_loss, take_profits, confidence, expected_rr, 
                probability_success, reasons, status, expires_at
            ) VALUES (
                :id, :symbol, :exchange, :direction, :timeframe, :entry_price,
                :stop_loss, :take_profits, :confidence, :expected_rr,
                :probability_success, :reasons, :status, :expires_at
            )
            """
            
            async with self.postgres_engine.begin() as conn:
                await conn.execute(text(query), signal_data)
                
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
    
    async def get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user preferences from PostgreSQL"""
        try:
            query = "SELECT * FROM user_preferences WHERE user_id = :user_id"
            
            async with self.postgres_engine.begin() as conn:
                result = await conn.execute(text(query), {"user_id": user_id})
                row = result.fetchone()
                
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return None
    
    async def update_user_preferences(self, user_id: int, preferences: Dict):
        """Update user preferences in PostgreSQL"""
        try:
            # Build dynamic update query
            set_clauses = []
            params = {"user_id": user_id}
            
            for key, value in preferences.items():
                if key != 'user_id':
                    set_clauses.append(f"{key} = :{key}")
                    params[key] = value
            
            if set_clauses:
                query = f"""
                INSERT INTO user_preferences (user_id, {', '.join(preferences.keys())})
                VALUES (:user_id, {', '.join([f':{k}' for k in preferences.keys()])})
                ON CONFLICT (user_id) DO UPDATE SET
                {', '.join(set_clauses)}, updated_at = NOW()
                """
                
                async with self.postgres_engine.begin() as conn:
                    await conn.execute(text(query), params)
                    
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
    
    async def close(self):
        """Close all database connections"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            
            if self.postgres_engine:
                await self.postgres_engine.dispose()
            
            # ClickHouse client doesn't need explicit closing
            
            logger.info("✅ Storage connections closed")
            
        except Exception as e:
            logger.error(f"Error closing storage connections: {e}")