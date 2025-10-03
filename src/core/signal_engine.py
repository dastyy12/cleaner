"""
Signal Engine - Core signal generation and management system
"""
import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd

from src.data.data_manager import DataManager
from src.analysis.analyzer_manager import AnalyzerManager
from src.tradingview.tv_integration import TradingViewIntegration
from src.models import (
    Signal, SignalDirection, SignalStatus, TimeFrame, AnalysisMethod,
    PriceLevel, RiskManagement, SignalReason, AnalysisResult
)
from config import settings

logger = logging.getLogger(__name__)

class SignalEngine:
    """Core signal generation and management engine"""
    
    def __init__(self, 
                 data_manager: DataManager,
                 analyzer_manager: AnalyzerManager,
                 tv_integration: TradingViewIntegration):
        self.data_manager = data_manager
        self.analyzer_manager = analyzer_manager
        self.tv_integration = tv_integration
        
        # Active signals storage
        self.active_signals: Dict[str, Signal] = {}
        
        # Signal generation settings
        self.min_confidence = settings.analysis.min_confidence
        self.max_signals_per_symbol = 3
        
        # Processing control
        self.running = False
        self.processing_lock = asyncio.Lock()
        
        # Performance tracking
        self.signal_stats = {
            'total_generated': 0,
            'total_triggered': 0,
            'total_stopped': 0,
            'win_rate': 0.0
        }
    
    async def initialize(self):
        """Initialize the signal engine"""
        try:
            logger.info("🔄 Initializing Signal Engine...")
            
            # Subscribe to data updates for signal generation
            await self._setup_data_subscriptions()
            
            # Load any existing active signals from database
            await self._load_active_signals()
            
            logger.info("✅ Signal Engine initialized")
            
        except Exception as e:
            logger.error(f"❌ Signal Engine initialization failed: {e}")
            raise
    
    async def _setup_data_subscriptions(self):
        """Setup subscriptions to data manager for real-time signal generation"""
        try:
            # Subscribe to kline updates for each symbol and timeframe
            for symbol in settings.symbols:
                for exchange in settings.exchanges_list:
                    for timeframe in settings.analysis.timeframes:
                        event_key = f"kline_{exchange}_{symbol}_{timeframe}"
                        self.data_manager.subscribe_to_data(
                            event_key, 
                            self._create_signal_callback(exchange, symbol, timeframe)
                        )
            
            logger.info(f"✅ Subscribed to data updates for {len(settings.symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error setting up data subscriptions: {e}")
            raise
    
    def _create_signal_callback(self, exchange: str, symbol: str, timeframe: str):
        """Create callback for processing new data"""
        async def callback(data: Dict):
            # Only process closed candles
            if data.get('is_closed', False):
                await self._process_symbol_update(exchange, symbol, timeframe)
        
        return callback
    
    async def _process_symbol_update(self, exchange: str, symbol: str, timeframe: str):
        """Process symbol update for signal generation"""
        try:
            async with self.processing_lock:
                # Get historical data for analysis
                df = await self.data_manager.get_historical_data(
                    exchange, symbol, timeframe, limit=200
                )
                
                if df.empty or len(df) < 50:
                    return
                
                # Run analysis
                analysis_results = await self.analyzer_manager.analyze_symbol(
                    symbol=symbol,
                    exchange=exchange,
                    timeframe=timeframe,
                    data=df
                )
                
                if not analysis_results:
                    return
                
                # Generate signals from analysis
                await self._generate_signals_from_analysis(
                    exchange, symbol, timeframe, df, analysis_results
                )
                
        except Exception as e:
            logger.error(f"Error processing {symbol} update: {e}")
    
    async def _generate_signals_from_analysis(self,
                                            exchange: str,
                                            symbol: str,
                                            timeframe: str,
                                            df: pd.DataFrame,
                                            analysis_results: Dict[AnalysisMethod, AnalysisResult]):
        """Generate trading signals from analysis results"""
        try:
            # Get consensus analysis
            consensus = self.analyzer_manager.get_consensus_analysis(analysis_results)
            
            # Only generate signals if consensus confidence is high enough
            if consensus['overall_confidence'] < self.min_confidence:
                return
            
            # Check if we already have too many signals for this symbol
            symbol_signals = [s for s in self.active_signals.values() 
                            if s.symbol == symbol and s.exchange == exchange]
            
            if len(symbol_signals) >= self.max_signals_per_symbol:
                return
            
            # Get top signals from consensus
            top_signals = consensus.get('top_signals', [])
            
            for signal_data in top_signals[:2]:  # Max 2 signals per update
                if signal_data.get('confidence', 0) >= self.min_confidence:
                    signal = await self._create_signal_from_data(
                        exchange, symbol, timeframe, df, signal_data, analysis_results
                    )
                    
                    if signal:
                        await self._add_signal(signal)
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
    
    async def _create_signal_from_data(self,
                                     exchange: str,
                                     symbol: str,
                                     timeframe: str,
                                     df: pd.DataFrame,
                                     signal_data: Dict,
                                     analysis_results: Dict) -> Optional[Signal]:
        """Create a Signal object from analysis data"""
        try:
            current_price = df['close'].iloc[-1]
            atr = self._calculate_atr(df)
            
            # Determine signal direction
            direction = SignalDirection.LONG if signal_data.get('direction') == 'LONG' else SignalDirection.SHORT
            
            # Calculate entry price (use current price or specific entry from signal)
            entry_price = signal_data.get('entry', current_price)
            
            # Calculate stop loss and take profits
            risk_mgmt = self._calculate_risk_management(
                entry_price, direction, atr, current_price
            )
            
            # Create signal reasons
            reasons = []
            source_method = signal_data.get('source_method', 'unknown')
            
            if source_method in ['technical_analysis', 'ta']:
                method = AnalysisMethod.TECHNICAL_ANALYSIS
            elif source_method in ['smart_money_concepts', 'smc']:
                method = AnalysisMethod.SMART_MONEY_CONCEPTS
            elif source_method in ['elliott_wave', 'wave']:
                method = AnalysisMethod.ELLIOTT_WAVE
            elif source_method in ['harmonic_patterns', 'harmonic']:
                method = AnalysisMethod.HARMONIC_PATTERNS
            else:
                method = AnalysisMethod.TECHNICAL_ANALYSIS
            
            reasons.append(SignalReason(
                method=method,
                description=signal_data.get('reason', 'Signal generated from analysis'),
                confidence=signal_data.get('confidence', 60),
                details=signal_data
            ))
            
            # Calculate expected RR
            stop_distance = abs(entry_price - risk_mgmt.stop_loss.price)
            tp_distance = abs(risk_mgmt.take_profits[0].price - entry_price) if risk_mgmt.take_profits else stop_distance
            expected_rr = tp_distance / stop_distance if stop_distance > 0 else 1.0
            
            # Create signal
            signal = Signal(
                id=str(uuid.uuid4()),
                symbol=symbol,
                exchange=exchange,
                direction=direction,
                timeframe=TimeFrame(timeframe),
                entry_price=PriceLevel(price=entry_price),
                risk_management=risk_mgmt,
                confidence=signal_data.get('confidence', 60),
                expected_rr=expected_rr,
                reasons=reasons,
                ttl=timedelta(hours=24),
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            
            # Generate screenshots if TradingView is available
            if self.tv_integration.initialized:
                try:
                    screenshots = await self.tv_integration.generate_chart_screenshot(
                        symbol=symbol,
                        exchange=exchange,
                        timeframe=timeframe,
                        analysis_data={method.value: result for method, result in analysis_results.items()},
                        signal_data={
                            'entry_price': entry_price,
                            'stop_loss': risk_mgmt.stop_loss.price,
                            'take_profits': [tp.price for tp in risk_mgmt.take_profits]
                        }
                    )
                    signal.screenshot_urls = screenshots
                except Exception as e:
                    logger.warning(f"Failed to generate screenshots for signal: {e}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error creating signal: {e}")
            return None
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            tr_list = []
            for i in range(1, len(df)):
                tr1 = high[i] - low[i]
                tr2 = abs(high[i] - close[i-1])
                tr3 = abs(low[i] - close[i-1])
                tr_list.append(max(tr1, tr2, tr3))
            
            if len(tr_list) >= period:
                return sum(tr_list[-period:]) / period
            else:
                return sum(tr_list) / len(tr_list) if tr_list else 0.01
                
        except:
            return 0.01
    
    def _calculate_risk_management(self,
                                 entry_price: float,
                                 direction: SignalDirection,
                                 atr: float,
                                 current_price: float) -> RiskManagement:
        """Calculate risk management parameters"""
        try:
            # Stop loss calculation (2x ATR)
            stop_multiplier = 2.0
            
            if direction == SignalDirection.LONG:
                stop_loss_price = entry_price - (atr * stop_multiplier)
                # Take profits at 1.5x and 3x risk
                tp1_price = entry_price + (atr * stop_multiplier * 1.5)
                tp2_price = entry_price + (atr * stop_multiplier * 3.0)
            else:
                stop_loss_price = entry_price + (atr * stop_multiplier)
                tp1_price = entry_price - (atr * stop_multiplier * 1.5)
                tp2_price = entry_price - (atr * stop_multiplier * 3.0)
            
            # Calculate recommended leverage based on volatility
            volatility = atr / current_price
            recommended_leverage = min(settings.analysis.max_leverage, 
                                     max(1, int(0.02 / volatility)))  # Target 2% move
            
            return RiskManagement(
                stop_loss=PriceLevel(
                    price=stop_loss_price,
                    description=f"Stop loss at {stop_multiplier}x ATR"
                ),
                take_profits=[
                    PriceLevel(
                        price=tp1_price,
                        description="First take profit (1.5R)"
                    ),
                    PriceLevel(
                        price=tp2_price,
                        description="Second take profit (3R)"
                    )
                ],
                trailing_stop=1.5,  # 1.5x ATR trailing stop
                recommended_leverage=recommended_leverage,
                risk_per_trade=settings.analysis.default_risk_per_trade
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk management: {e}")
            # Return conservative defaults
            return RiskManagement(
                stop_loss=PriceLevel(price=entry_price * 0.98),
                take_profits=[PriceLevel(price=entry_price * 1.03)],
                recommended_leverage=1,
                risk_per_trade=1.0
            )
    
    async def _add_signal(self, signal: Signal):
        """Add a new signal to active signals"""
        try:
            # Store signal
            self.active_signals[signal.id] = signal
            
            # Store in database
            await self._store_signal_in_db(signal)
            
            # Update statistics
            self.signal_stats['total_generated'] += 1
            
            logger.info(f"✅ New signal generated: {signal.symbol} {signal.direction.value} "
                       f"@ {signal.entry_price.price:.4f} (Confidence: {signal.confidence}%)")
            
        except Exception as e:
            logger.error(f"Error adding signal: {e}")
    
    async def _store_signal_in_db(self, signal: Signal):
        """Store signal in database"""
        try:
            signal_data = {
                'id': signal.id,
                'symbol': signal.symbol,
                'exchange': signal.exchange,
                'direction': signal.direction.value,
                'timeframe': signal.timeframe.value,
                'entry_price': signal.entry_price.price,
                'stop_loss': signal.risk_management.stop_loss.price,
                'take_profits': [tp.price for tp in signal.risk_management.take_profits],
                'confidence': signal.confidence,
                'expected_rr': signal.expected_rr,
                'probability_success': signal.probability_success,
                'reasons': [reason.dict() for reason in signal.reasons],
                'status': signal.status.value,
                'expires_at': signal.expires_at
            }
            
            await self.data_manager.storage.store_signal(signal_data)
            
        except Exception as e:
            logger.error(f"Error storing signal in database: {e}")
    
    async def _load_active_signals(self):
        """Load active signals from database"""
        try:
            # This would load active signals from the database
            # For now, we'll start with an empty set
            logger.info("📊 Loaded active signals from database")
            
        except Exception as e:
            logger.error(f"Error loading active signals: {e}")
    
    async def start(self):
        """Start the signal engine"""
        if self.running:
            return
        
        logger.info("🚀 Starting Signal Engine...")
        self.running = True
        
        # Start signal monitoring task
        asyncio.create_task(self._signal_monitoring_loop())
        
        logger.info("✅ Signal Engine started")
    
    async def _signal_monitoring_loop(self):
        """Monitor active signals for updates"""
        while self.running:
            try:
                await self._update_active_signals()
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in signal monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _update_active_signals(self):
        """Update status of active signals"""
        try:
            current_time = datetime.utcnow()
            signals_to_remove = []
            
            for signal_id, signal in self.active_signals.items():
                # Check if signal has expired
                if current_time > signal.expires_at:
                    signal.status = SignalStatus.EXPIRED
                    signals_to_remove.append(signal_id)
                    continue
                
                # Check if signal has been triggered or stopped
                current_price = self._get_current_price(signal.exchange, signal.symbol)
                if current_price:
                    await self._check_signal_triggers(signal, current_price)
            
            # Remove expired/completed signals
            for signal_id in signals_to_remove:
                del self.active_signals[signal_id]
                
        except Exception as e:
            logger.error(f"Error updating active signals: {e}")
    
    def _get_current_price(self, exchange: str, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            ticker = self.data_manager.get_latest_ticker(exchange, symbol)
            return ticker['price'] if ticker else None
            
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None
    
    async def _check_signal_triggers(self, signal: Signal, current_price: float):
        """Check if signal has been triggered or stopped"""
        try:
            entry_price = signal.entry_price.price
            stop_loss = signal.risk_management.stop_loss.price
            
            if signal.direction == SignalDirection.LONG:
                # Check stop loss
                if current_price <= stop_loss:
                    signal.status = SignalStatus.STOPPED
                    signal.closed_at = datetime.utcnow()
                    signal.pnl = (current_price - entry_price) / entry_price * 100
                    self.signal_stats['total_stopped'] += 1
                    
                # Check take profits
                elif signal.status == SignalStatus.ACTIVE:
                    for tp in signal.risk_management.take_profits:
                        if current_price >= tp.price:
                            signal.status = SignalStatus.TRIGGERED
                            signal.triggered_at = datetime.utcnow()
                            signal.pnl = (current_price - entry_price) / entry_price * 100
                            self.signal_stats['total_triggered'] += 1
                            break
            
            else:  # SHORT
                # Check stop loss
                if current_price >= stop_loss:
                    signal.status = SignalStatus.STOPPED
                    signal.closed_at = datetime.utcnow()
                    signal.pnl = (entry_price - current_price) / entry_price * 100
                    self.signal_stats['total_stopped'] += 1
                    
                # Check take profits
                elif signal.status == SignalStatus.ACTIVE:
                    for tp in signal.risk_management.take_profits:
                        if current_price <= tp.price:
                            signal.status = SignalStatus.TRIGGERED
                            signal.triggered_at = datetime.utcnow()
                            signal.pnl = (entry_price - current_price) / entry_price * 100
                            self.signal_stats['total_triggered'] += 1
                            break
            
            # Update win rate
            if self.signal_stats['total_triggered'] + self.signal_stats['total_stopped'] > 0:
                self.signal_stats['win_rate'] = (
                    self.signal_stats['total_triggered'] / 
                    (self.signal_stats['total_triggered'] + self.signal_stats['total_stopped'])
                ) * 100
                
        except Exception as e:
            logger.error(f"Error checking signal triggers: {e}")
    
    def get_active_signals(self, 
                          symbol: Optional[str] = None,
                          exchange: Optional[str] = None,
                          min_confidence: Optional[float] = None) -> List[Signal]:
        """Get active signals with optional filtering"""
        try:
            signals = list(self.active_signals.values())
            
            # Apply filters
            if symbol:
                signals = [s for s in signals if s.symbol == symbol]
            
            if exchange:
                signals = [s for s in signals if s.exchange == exchange]
            
            if min_confidence:
                signals = [s for s in signals if s.confidence >= min_confidence]
            
            # Sort by confidence
            signals.sort(key=lambda x: x.confidence, reverse=True)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    def get_signal_stats(self) -> Dict[str, Any]:
        """Get signal generation statistics"""
        return {
            **self.signal_stats,
            'active_signals': len(self.active_signals),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    async def _save_active_signals(self):
        """Save active signals state to database"""
        try:
            for signal in self.active_signals.values():
                await self._store_signal_in_db(signal)
            logger.info("💾 Active signals saved to database")
        except Exception as e:
            logger.error(f"Error saving active signals: {e}")
    
    async def stop(self):
        """Stop the signal engine"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping Signal Engine...")
        self.running = False
        
        # Save active signals state
        await self._save_active_signals()
        
        logger.info("✅ Signal Engine stopped")