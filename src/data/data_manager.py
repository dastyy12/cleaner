"""
Data Manager - orchestrates data ingestion, storage, and retrieval
"""
import asyncio
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd

from src.data.exchange_connector import create_exchange_connector, ExchangeConnector
from src.data.storage import StorageManager
from src.models import MarketData, TimeFrame
from config import settings

logger = logging.getLogger(__name__)

class DataManager:
    """Manages data ingestion from multiple exchanges and storage"""
    
    def __init__(self):
        self.connectors: Dict[str, ExchangeConnector] = {}
        self.storage = StorageManager()
        self.running = False
        self.data_callbacks: Dict[str, List[Callable]] = {}
        
        # In-memory cache for latest data
        self.latest_tickers: Dict[str, Dict] = {}  # {exchange_symbol: ticker_data}
        self.latest_klines: Dict[str, Dict] = {}   # {exchange_symbol_tf: kline_data}
        self.latest_orderbooks: Dict[str, Dict] = {}  # {exchange_symbol: orderbook_data}
    
    async def initialize(self):
        """Initialize data manager"""
        logger.info("🔄 Initializing Data Manager...")
        
        try:
            # Initialize storage
            await self.storage.initialize()
            
            # Initialize exchange connectors
            for exchange_name in settings.exchanges_list:
                try:
                    connector = create_exchange_connector(exchange_name)
                    await connector.initialize()
                    self.connectors[exchange_name] = connector
                    logger.info(f"✅ {exchange_name} connector ready")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize {exchange_name}: {e}")
            
            if not self.connectors:
                raise Exception("No exchange connectors initialized")
            
            logger.info(f"✅ Data Manager initialized with {len(self.connectors)} exchanges")
            
        except Exception as e:
            logger.error(f"❌ Data Manager initialization failed: {e}")
            raise
    
    async def start_streaming(self):
        """Start streaming data from all exchanges"""
        if self.running:
            return
        
        logger.info("🚀 Starting data streaming...")
        self.running = True
        
        tasks = []
        
        # Start all exchange connectors
        for exchange_name, connector in self.connectors.items():
            tasks.append(asyncio.create_task(connector.start()))
            
            # Subscribe to data streams for all symbols
            for symbol in settings.symbols:
                # Subscribe to ticker updates
                await connector.subscribe_ticker(
                    symbol, 
                    self._create_ticker_callback(exchange_name, symbol)
                )
                
                # Subscribe to klines for all timeframes
                for timeframe in settings.analysis.timeframes:
                    await connector.subscribe_klines(
                        symbol, 
                        timeframe,
                        self._create_kline_callback(exchange_name, symbol, timeframe)
                    )
                
                # Subscribe to orderbook updates
                await connector.subscribe_orderbook(
                    symbol,
                    self._create_orderbook_callback(exchange_name, symbol)
                )
                
                # Subscribe to trades
                await connector.subscribe_trades(
                    symbol,
                    self._create_trades_callback(exchange_name, symbol)
                )
        
        logger.info(f"✅ Started streaming for {len(settings.symbols)} symbols on {len(self.connectors)} exchanges")
        
        # Wait for all connector tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def _create_ticker_callback(self, exchange: str, symbol: str):
        """Create ticker update callback"""
        async def callback(data: Dict):
            key = f"{exchange}_{symbol}"
            self.latest_tickers[key] = data
            
            # Store in database
            await self.storage.store_ticker(exchange, symbol, data)
            
            # Notify subscribers
            await self._notify_callbacks(f"ticker_{key}", data)
        
        return callback
    
    def _create_kline_callback(self, exchange: str, symbol: str, timeframe: str):
        """Create kline update callback"""
        async def callback(data: Dict):
            key = f"{exchange}_{symbol}_{timeframe}"
            
            # Only process closed candles for storage
            if data.get('is_closed', False):
                self.latest_klines[key] = data
                
                # Store in database
                await self.storage.store_kline(exchange, symbol, timeframe, data)
            
            # Always notify subscribers (for real-time updates)
            await self._notify_callbacks(f"kline_{key}", data)
        
        return callback
    
    def _create_orderbook_callback(self, exchange: str, symbol: str):
        """Create orderbook update callback"""
        async def callback(data: Dict):
            key = f"{exchange}_{symbol}"
            self.latest_orderbooks[key] = data
            
            # Store in database (sample every 10 seconds to avoid spam)
            await self.storage.store_orderbook(exchange, symbol, data)
            
            # Notify subscribers
            await self._notify_callbacks(f"orderbook_{key}", data)
        
        return callback
    
    def _create_trades_callback(self, exchange: str, symbol: str):
        """Create trades update callback"""
        async def callback(data: Dict):
            # Store in database
            await self.storage.store_trade(exchange, symbol, data)
            
            # Notify subscribers
            key = f"{exchange}_{symbol}"
            await self._notify_callbacks(f"trades_{key}", data)
        
        return callback
    
    async def _notify_callbacks(self, event_key: str, data: Dict):
        """Notify all registered callbacks for an event"""
        if event_key in self.data_callbacks:
            for callback in self.data_callbacks[event_key]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error in callback for {event_key}: {e}")
    
    def subscribe_to_data(self, event_key: str, callback: Callable):
        """Subscribe to data updates"""
        if event_key not in self.data_callbacks:
            self.data_callbacks[event_key] = []
        self.data_callbacks[event_key].append(callback)
    
    def unsubscribe_from_data(self, event_key: str, callback: Callable):
        """Unsubscribe from data updates"""
        if event_key in self.data_callbacks and callback in self.data_callbacks[event_key]:
            self.data_callbacks[event_key].remove(callback)
    
    async def get_historical_data(self, 
                                  exchange: str, 
                                  symbol: str, 
                                  timeframe: str, 
                                  limit: int = 1000) -> pd.DataFrame:
        """Get historical OHLCV data"""
        try:
            # Try to get from database first
            data = await self.storage.get_historical_klines(exchange, symbol, timeframe, limit)
            
            if len(data) < limit:
                # Fetch from exchange if not enough data in DB
                if exchange in self.connectors:
                    fresh_data = await self.connectors[exchange].get_historical_klines(
                        symbol, timeframe, limit
                    )
                    
                    # Store fresh data
                    for kline in fresh_data:
                        await self.storage.store_kline(exchange, symbol, timeframe, kline)
                    
                    # Convert to DataFrame
                    if fresh_data:
                        data = pd.DataFrame(fresh_data)
                        data.set_index('timestamp', inplace=True)
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    def get_latest_ticker(self, exchange: str, symbol: str) -> Optional[Dict]:
        """Get latest ticker data"""
        key = f"{exchange}_{symbol}"
        return self.latest_tickers.get(key)
    
    def get_latest_kline(self, exchange: str, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get latest kline data"""
        key = f"{exchange}_{symbol}_{timeframe}"
        return self.latest_klines.get(key)
    
    def get_latest_orderbook(self, exchange: str, symbol: str) -> Optional[Dict]:
        """Get latest orderbook data"""
        key = f"{exchange}_{symbol}"
        return self.latest_orderbooks.get(key)
    
    async def get_funding_rates(self, exchange: str, symbol: str) -> Dict:
        """Get funding rates for a symbol"""
        try:
            if exchange in self.connectors:
                # This would need to be implemented per exchange
                # For now, return empty dict
                return {}
        except Exception as e:
            logger.error(f"Error getting funding rates: {e}")
            return {}
    
    async def get_open_interest(self, exchange: str, symbol: str) -> Optional[float]:
        """Get open interest for a symbol"""
        try:
            if exchange in self.connectors:
                # This would need to be implemented per exchange
                # For now, return None
                return None
        except Exception as e:
            logger.error(f"Error getting open interest: {e}")
            return None
    
    async def stop(self):
        """Stop data manager"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping data streaming...")
        self.running = False
        
        # Stop all connectors
        for connector in self.connectors.values():
            await connector.stop()
        
        # Close storage connections
        await self.storage.close()
        
        logger.info("✅ Data Manager stopped")