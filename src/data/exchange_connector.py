"""
Exchange connector for multiple exchanges (Binance, Bybit, OKX)
Handles real-time data streaming and historical data fetching
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import ccxt.pro as ccxt
import websockets
from abc import ABC, abstractmethod

from src.models import MarketData, TimeFrame
from config import settings

logger = logging.getLogger(__name__)

class ExchangeConnector(ABC):
    """Abstract base class for exchange connectors"""
    
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.exchange = None
        self.websockets = {}
        self.callbacks = {}
        self.running = False
    
    @abstractmethod
    async def initialize(self):
        """Initialize exchange connection"""
        pass
    
    @abstractmethod
    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """Subscribe to ticker updates"""
        pass
    
    @abstractmethod
    async def subscribe_orderbook(self, symbol: str, callback: Callable):
        """Subscribe to orderbook updates"""
        pass
    
    @abstractmethod
    async def subscribe_trades(self, symbol: str, callback: Callable):
        """Subscribe to trade updates"""
        pass
    
    @abstractmethod
    async def subscribe_klines(self, symbol: str, timeframe: str, callback: Callable):
        """Subscribe to kline/candlestick updates"""
        pass
    
    @abstractmethod
    async def get_historical_klines(self, symbol: str, timeframe: str, limit: int = 1000) -> List[Dict]:
        """Get historical klines"""
        pass
    
    async def start(self):
        """Start the connector"""
        self.running = True
        logger.info(f"Started {self.exchange_name} connector")
    
    async def stop(self):
        """Stop the connector"""
        self.running = False
        if self.exchange:
            await self.exchange.close()
        logger.info(f"Stopped {self.exchange_name} connector")

class BinanceConnector(ExchangeConnector):
    """Binance futures connector"""
    
    def __init__(self):
        super().__init__("binance")
        self.base_ws_url = "wss://fstream.binance.com/ws/"
    
    async def initialize(self):
        """Initialize Binance connection"""
        try:
            self.exchange = ccxt.binance({
                'apiKey': settings.exchanges.binance_api_key,
                'secret': settings.exchanges.binance_secret,
                'sandbox': False,
                'options': {
                    'defaultType': 'future',  # Use futures
                }
            })
            await self.exchange.load_markets()
            logger.info("✅ Binance connector initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Binance: {e}")
            raise
    
    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """Subscribe to ticker updates"""
        stream = f"{symbol.lower()}@ticker"
        await self._subscribe_stream(stream, callback, "ticker")
    
    async def subscribe_orderbook(self, symbol: str, callback: Callable):
        """Subscribe to orderbook updates"""
        stream = f"{symbol.lower()}@depth@100ms"
        await self._subscribe_stream(stream, callback, "orderbook")
    
    async def subscribe_trades(self, symbol: str, callback: Callable):
        """Subscribe to trade updates"""
        stream = f"{symbol.lower()}@aggTrade"
        await self._subscribe_stream(stream, callback, "trades")
    
    async def subscribe_klines(self, symbol: str, timeframe: str, callback: Callable):
        """Subscribe to kline updates"""
        stream = f"{symbol.lower()}@kline_{timeframe}"
        await self._subscribe_stream(stream, callback, "klines")
    
    async def _subscribe_stream(self, stream: str, callback: Callable, data_type: str):
        """Subscribe to a WebSocket stream"""
        if stream not in self.websockets:
            ws_url = f"{self.base_ws_url}{stream}"
            self.websockets[stream] = await websockets.connect(ws_url)
            self.callbacks[stream] = callback
            
            # Start listening task
            asyncio.create_task(self._listen_stream(stream, data_type))
    
    async def _listen_stream(self, stream: str, data_type: str):
        """Listen to WebSocket stream"""
        ws = self.websockets[stream]
        callback = self.callbacks[stream]
        
        try:
            async for message in ws:
                if not self.running:
                    break
                
                data = json.loads(message)
                processed_data = self._process_data(data, data_type)
                if processed_data:
                    await callback(processed_data)
        except Exception as e:
            logger.error(f"Error in stream {stream}: {e}")
        finally:
            if stream in self.websockets:
                del self.websockets[stream]
            if stream in self.callbacks:
                del self.callbacks[stream]
    
    def _process_data(self, data: Dict, data_type: str) -> Optional[Dict]:
        """Process raw WebSocket data"""
        try:
            if data_type == "ticker":
                return {
                    'symbol': data['s'],
                    'price': float(data['c']),
                    'volume': float(data['v']),
                    'change': float(data['P']),
                    'timestamp': datetime.fromtimestamp(data['E'] / 1000)
                }
            elif data_type == "klines":
                kline = data['k']
                return {
                    'symbol': kline['s'],
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v']),
                    'timestamp': datetime.fromtimestamp(kline['t'] / 1000),
                    'is_closed': kline['x']
                }
            elif data_type == "trades":
                return {
                    'symbol': data['s'],
                    'price': float(data['p']),
                    'quantity': float(data['q']),
                    'timestamp': datetime.fromtimestamp(data['T'] / 1000),
                    'is_buyer_maker': data['m']
                }
            elif data_type == "orderbook":
                return {
                    'symbol': data['s'],
                    'bids': [[float(bid[0]), float(bid[1])] for bid in data['b']],
                    'asks': [[float(ask[0]), float(ask[1])] for ask in data['a']],
                    'timestamp': datetime.fromtimestamp(data['E'] / 1000)
                }
        except Exception as e:
            logger.error(f"Error processing {data_type} data: {e}")
            return None
    
    async def get_historical_klines(self, symbol: str, timeframe: str, limit: int = 1000) -> List[Dict]:
        """Get historical klines from Binance"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [
                {
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                }
                for candle in ohlcv
            ]
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return []

class BybitConnector(ExchangeConnector):
    """Bybit futures connector"""
    
    def __init__(self):
        super().__init__("bybit")
        self.base_ws_url = "wss://stream.bybit.com/v5/public/linear"
    
    async def initialize(self):
        """Initialize Bybit connection"""
        try:
            self.exchange = ccxt.bybit({
                'apiKey': settings.exchanges.bybit_api_key,
                'secret': settings.exchanges.bybit_secret,
                'sandbox': False,
                'options': {
                    'defaultType': 'linear',  # Linear futures
                }
            })
            await self.exchange.load_markets()
            logger.info("✅ Bybit connector initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bybit: {e}")
            raise
    
    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """Subscribe to ticker updates"""
        await self._subscribe_v5("tickers", [symbol], callback, "ticker")
    
    async def subscribe_orderbook(self, symbol: str, callback: Callable):
        """Subscribe to orderbook updates"""
        await self._subscribe_v5("orderbook", [symbol], callback, "orderbook")
    
    async def subscribe_trades(self, symbol: str, callback: Callable):
        """Subscribe to trade updates"""
        await self._subscribe_v5("publicTrade", [symbol], callback, "trades")
    
    async def subscribe_klines(self, symbol: str, timeframe: str, callback: Callable):
        """Subscribe to kline updates"""
        await self._subscribe_v5("kline", [f"{timeframe}.{symbol}"], callback, "klines")
    
    async def _subscribe_v5(self, topic: str, symbols: List[str], callback: Callable, data_type: str):
        """Subscribe to Bybit V5 WebSocket"""
        stream_key = f"{topic}_{'-'.join(symbols)}"
        
        if stream_key not in self.websockets:
            try:
                ws = await websockets.connect(self.base_ws_url)
                
                # Send subscription message
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [f"{topic}.{symbol}" for symbol in symbols]
                }
                await ws.send(json.dumps(subscribe_msg))
                
                self.websockets[stream_key] = ws
                self.callbacks[stream_key] = callback
                
                # Start listening task
                asyncio.create_task(self._listen_v5_stream(stream_key, data_type))
                
            except Exception as e:
                logger.error(f"Failed to subscribe to {topic}: {e}")
    
    async def _listen_v5_stream(self, stream_key: str, data_type: str):
        """Listen to Bybit V5 WebSocket stream"""
        ws = self.websockets[stream_key]
        callback = self.callbacks[stream_key]
        
        try:
            async for message in ws:
                if not self.running:
                    break
                
                data = json.loads(message)
                if 'data' in data:
                    processed_data = self._process_v5_data(data['data'], data_type)
                    if processed_data:
                        await callback(processed_data)
        except Exception as e:
            logger.error(f"Error in Bybit stream {stream_key}: {e}")
        finally:
            if stream_key in self.websockets:
                del self.websockets[stream_key]
            if stream_key in self.callbacks:
                del self.callbacks[stream_key]
    
    def _process_v5_data(self, data: Dict, data_type: str) -> Optional[Dict]:
        """Process Bybit V5 WebSocket data"""
        try:
            if data_type == "ticker":
                return {
                    'symbol': data['symbol'],
                    'price': float(data['lastPrice']),
                    'volume': float(data['volume24h']),
                    'change': float(data['price24hPcnt']),
                    'timestamp': datetime.fromtimestamp(int(data['ts']) / 1000)
                }
            elif data_type == "klines":
                return {
                    'symbol': data['symbol'],
                    'open': float(data['open']),
                    'high': float(data['high']),
                    'low': float(data['low']),
                    'close': float(data['close']),
                    'volume': float(data['volume']),
                    'timestamp': datetime.fromtimestamp(int(data['start']) / 1000),
                    'is_closed': data['confirm']
                }
            # Add more data types as needed
        except Exception as e:
            logger.error(f"Error processing Bybit {data_type} data: {e}")
            return None
    
    async def get_historical_klines(self, symbol: str, timeframe: str, limit: int = 1000) -> List[Dict]:
        """Get historical klines from Bybit"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [
                {
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                }
                for candle in ohlcv
            ]
        except Exception as e:
            logger.error(f"Error fetching Bybit historical data: {e}")
            return []

class OKXConnector(ExchangeConnector):
    """OKX futures connector"""
    
    def __init__(self):
        super().__init__("okx")
        self.base_ws_url = "wss://ws.okx.com:8443/ws/v5/public"
    
    async def initialize(self):
        """Initialize OKX connection"""
        try:
            self.exchange = ccxt.okx({
                'apiKey': settings.exchanges.okx_api_key,
                'secret': settings.exchanges.okx_secret,
                'password': settings.exchanges.okx_passphrase,
                'sandbox': False,
            })
            await self.exchange.load_markets()
            logger.info("✅ OKX connector initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OKX: {e}")
            raise
    
    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """Subscribe to ticker updates"""
        await self._subscribe_okx("tickers", [{"instId": symbol}], callback, "ticker")
    
    async def subscribe_orderbook(self, symbol: str, callback: Callable):
        """Subscribe to orderbook updates"""
        await self._subscribe_okx("books", [{"instId": symbol}], callback, "orderbook")
    
    async def subscribe_trades(self, symbol: str, callback: Callable):
        """Subscribe to trade updates"""
        await self._subscribe_okx("trades", [{"instId": symbol}], callback, "trades")
    
    async def subscribe_klines(self, symbol: str, timeframe: str, callback: Callable):
        """Subscribe to kline updates"""
        await self._subscribe_okx("candle1m", [{"instId": symbol}], callback, "klines")
    
    async def _subscribe_okx(self, channel: str, args: List[Dict], callback: Callable, data_type: str):
        """Subscribe to OKX WebSocket"""
        stream_key = f"{channel}_{args[0]['instId']}"
        
        if stream_key not in self.websockets:
            try:
                ws = await websockets.connect(self.base_ws_url)
                
                # Send subscription message
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [{"channel": channel, **arg} for arg in args]
                }
                await ws.send(json.dumps(subscribe_msg))
                
                self.websockets[stream_key] = ws
                self.callbacks[stream_key] = callback
                
                # Start listening task
                asyncio.create_task(self._listen_okx_stream(stream_key, data_type))
                
            except Exception as e:
                logger.error(f"Failed to subscribe to OKX {channel}: {e}")
    
    async def _listen_okx_stream(self, stream_key: str, data_type: str):
        """Listen to OKX WebSocket stream"""
        ws = self.websockets[stream_key]
        callback = self.callbacks[stream_key]
        
        try:
            async for message in ws:
                if not self.running:
                    break
                
                data = json.loads(message)
                if 'data' in data:
                    for item in data['data']:
                        processed_data = self._process_okx_data(item, data_type)
                        if processed_data:
                            await callback(processed_data)
        except Exception as e:
            logger.error(f"Error in OKX stream {stream_key}: {e}")
        finally:
            if stream_key in self.websockets:
                del self.websockets[stream_key]
            if stream_key in self.callbacks:
                del self.callbacks[stream_key]
    
    def _process_okx_data(self, data: Dict, data_type: str) -> Optional[Dict]:
        """Process OKX WebSocket data"""
        try:
            if data_type == "ticker":
                return {
                    'symbol': data['instId'],
                    'price': float(data['last']),
                    'volume': float(data['vol24h']),
                    'change': float(data['chgUtc8']),
                    'timestamp': datetime.fromtimestamp(int(data['ts']) / 1000)
                }
            elif data_type == "klines":
                return {
                    'symbol': data['instId'],
                    'open': float(data['o']),
                    'high': float(data['h']),
                    'low': float(data['l']),
                    'close': float(data['c']),
                    'volume': float(data['vol']),
                    'timestamp': datetime.fromtimestamp(int(data['ts']) / 1000),
                    'is_closed': True  # OKX sends completed candles
                }
            # Add more data types as needed
        except Exception as e:
            logger.error(f"Error processing OKX {data_type} data: {e}")
            return None
    
    async def get_historical_klines(self, symbol: str, timeframe: str, limit: int = 1000) -> List[Dict]:
        """Get historical klines from OKX"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [
                {
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                }
                for candle in ohlcv
            ]
        except Exception as e:
            logger.error(f"Error fetching OKX historical data: {e}")
            return []

# Factory function to create exchange connectors
def create_exchange_connector(exchange_name: str) -> ExchangeConnector:
    """Create exchange connector by name"""
    connectors = {
        'binance': BinanceConnector,
        'bybit': BybitConnector,
        'okx': OKXConnector
    }
    
    if exchange_name not in connectors:
        raise ValueError(f"Unsupported exchange: {exchange_name}")
    
    return connectors[exchange_name]()