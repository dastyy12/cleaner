"""
Configuration settings for the crypto signal generation system
"""
import os
from typing import List, Dict, Any
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

load_dotenv()

class DatabaseConfig(BaseSettings):
    """Database configuration"""
    clickhouse_host: str = Field(default="localhost", env="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(default=9000, env="CLICKHOUSE_PORT")
    clickhouse_database: str = Field(default="crypto_signals", env="CLICKHOUSE_DB")
    
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="crypto_signals", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="", env="POSTGRES_PASSWORD")

class ExchangeConfig(BaseSettings):
    """Exchange API configuration"""
    binance_api_key: str = Field(default="", env="BINANCE_API_KEY")
    binance_secret: str = Field(default="", env="BINANCE_SECRET")
    
    bybit_api_key: str = Field(default="", env="BYBIT_API_KEY")
    bybit_secret: str = Field(default="", env="BYBIT_SECRET")
    
    okx_api_key: str = Field(default="", env="OKX_API_KEY")
    okx_secret: str = Field(default="", env="OKX_SECRET")
    okx_passphrase: str = Field(default="", env="OKX_PASSPHRASE")

class TradingViewConfig(BaseSettings):
    """TradingView integration configuration"""
    tv_username: str = Field(default="", env="TV_USERNAME")
    tv_password: str = Field(default="", env="TV_PASSWORD")
    tv_chart_url: str = Field(default="https://www.tradingview.com/chart/", env="TV_CHART_URL")
    screenshot_width: int = Field(default=1920, env="SCREENSHOT_WIDTH")
    screenshot_height: int = Field(default=1080, env="SCREENSHOT_HEIGHT")

class TelegramConfig(BaseSettings):
    """Telegram bot configuration"""
    bot_token: str = Field(env="BOT_TOKEN")
    admin_chat_id: int = Field(default=0, env="ADMIN_CHAT_ID")
    max_signals_per_hour: int = Field(default=10, env="MAX_SIGNALS_PER_HOUR")

class AnalysisConfig(BaseSettings):
    """Analysis and signal generation configuration"""
    # Timeframes to analyze
    timeframes: List[str] = ["1m", "5m", "15m", "1h", "4h", "1d"]
    
    # Minimum confidence threshold for signals
    min_confidence: float = 60.0
    
    # Risk management
    max_leverage: int = 10
    default_risk_per_trade: float = 1.0  # percentage
    
    # Technical analysis parameters
    ma_periods: List[int] = [9, 21, 50, 100, 200]
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Smart Money Concepts
    smc_swing_length: int = 5
    fvg_threshold: float = 0.001  # minimum gap size
    
    # Elliott Wave
    wave_min_swing_size: float = 0.005  # minimum swing size
    fib_levels: List[float] = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]
    
    # Harmonic patterns
    harmonic_tolerance: float = 0.05  # 5% tolerance for pattern ratios

class Settings:
    """Main settings class"""
    def __init__(self):
        self.database = DatabaseConfig()
        self.exchanges = ExchangeConfig()
        self.tradingview = TradingViewConfig()
        self.telegram = TelegramConfig()
        self.analysis = AnalysisConfig()
        
        # Supported symbols
        self.symbols = [
            "BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT",
            "LINKUSDT", "MATICUSDT", "AVAXUSDT", "ATOMUSDT", "NEARUSDT",
            "FTMUSDT", "SANDUSDT", "MANAUSDT", "GALAUSDT", "ENJUSDT"
        ]
        
        # Supported exchanges
        self.exchanges_list = ["binance", "bybit", "okx"]

# Global settings instance
settings = Settings()