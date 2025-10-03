"""
Classical Technical Analysis Implementation
Includes trend, momentum, volatility, and level indicators
"""
import numpy as np
import pandas as pd
import talib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

from src.models import AnalysisResult, AnalysisMethod, SignalDirection
from config import settings

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """Classical technical analysis implementation"""
    
    def __init__(self):
        self.config = settings.analysis
    
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> AnalysisResult:
        """Perform comprehensive technical analysis"""
        try:
            if len(df) < 200:  # Need enough data for analysis
                logger.warning(f"Insufficient data for TA analysis: {len(df)} bars")
                return AnalysisResult(
                    method=AnalysisMethod.TECHNICAL_ANALYSIS,
                    symbol=symbol,
                    timeframe=timeframe,
                    confidence=0.0
                )
            
            # Calculate all indicators
            indicators = self._calculate_indicators(df)
            
            # Generate signals
            signals = self._generate_signals(df, indicators, symbol, timeframe)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(indicators, signals)
            
            return AnalysisResult(
                method=AnalysisMethod.TECHNICAL_ANALYSIS,
                symbol=symbol,
                timeframe=timeframe,
                confidence=confidence,
                data=indicators,
                potential_signals=signals
            )
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return AnalysisResult(
                method=AnalysisMethod.TECHNICAL_ANALYSIS,
                symbol=symbol,
                timeframe=timeframe,
                confidence=0.0
            )
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators"""
        indicators = {}
        
        # Price data
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        volume = df['volume'].values
        
        # Moving Averages
        indicators['ma'] = {}
        for period in self.config.ma_periods:
            if len(close) >= period:
                indicators['ma'][f'ma_{period}'] = talib.SMA(close, timeperiod=period)
                indicators['ma'][f'ema_{period}'] = talib.EMA(close, timeperiod=period)
        
        # Hull Moving Average
        if len(close) >= 21:
            indicators['hma_21'] = self._hull_ma(close, 21)
        
        # Momentum Indicators
        if len(close) >= self.config.rsi_period:
            indicators['rsi'] = talib.RSI(close, timeperiod=self.config.rsi_period)
        
        if len(close) >= max(self.config.macd_fast, self.config.macd_slow):
            macd, macd_signal, macd_hist = talib.MACD(
                close, 
                fastperiod=self.config.macd_fast,
                slowperiod=self.config.macd_slow,
                signalperiod=self.config.macd_signal
            )
            indicators['macd'] = {
                'macd': macd,
                'signal': macd_signal,
                'histogram': macd_hist
            }
        
        if len(close) >= 14:
            indicators['stoch'] = {}
            slowk, slowd = talib.STOCH(high, low, close)
            indicators['stoch']['k'] = slowk
            indicators['stoch']['d'] = slowd
        
        if len(close) >= 14:
            indicators['cci'] = talib.CCI(high, low, close, timeperiod=14)
        
        if len(close) >= 14:
            indicators['adx'] = talib.ADX(high, low, close, timeperiod=14)
            indicators['plus_di'] = talib.PLUS_DI(high, low, close, timeperiod=14)
            indicators['minus_di'] = talib.MINUS_DI(high, low, close, timeperiod=14)
        
        # Volatility Indicators
        if len(close) >= 20:
            indicators['atr'] = talib.ATR(high, low, close, timeperiod=14)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20)
            indicators['bollinger'] = {
                'upper': bb_upper,
                'middle': bb_middle,
                'lower': bb_lower
            }
            
            # Keltner Channels
            indicators['keltner'] = self._keltner_channels(df)
        
        if len(close) >= 20:
            # Donchian Channels
            indicators['donchian'] = {
                'upper': talib.MAX(high, timeperiod=20),
                'lower': talib.MIN(low, timeperiod=20)
            }
        
        # Volume Indicators
        if len(volume) >= 10:
            indicators['volume_sma'] = talib.SMA(volume, timeperiod=10)
            indicators['volume_ratio'] = volume / indicators['volume_sma']
        
        # VWAP (Volume Weighted Average Price)
        if len(df) >= 1:
            indicators['vwap'] = self._calculate_vwap(df)
        
        # Support/Resistance Levels
        indicators['pivot_levels'] = self._calculate_pivot_levels(df)
        
        # Fibonacci Levels
        indicators['fib_levels'] = self._calculate_fibonacci_levels(df)
        
        return indicators
    
    def _hull_ma(self, close: np.ndarray, period: int) -> np.ndarray:
        """Calculate Hull Moving Average"""
        try:
            half_period = int(period / 2)
            sqrt_period = int(np.sqrt(period))
            
            wma_half = talib.WMA(close, timeperiod=half_period)
            wma_full = talib.WMA(close, timeperiod=period)
            
            raw_hma = 2 * wma_half - wma_full
            hma = talib.WMA(raw_hma, timeperiod=sqrt_period)
            
            return hma
        except:
            return np.full(len(close), np.nan)
    
    def _keltner_channels(self, df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> Dict:
        """Calculate Keltner Channels"""
        try:
            ema = talib.EMA(df['close'].values, timeperiod=period)
            atr = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=period)
            
            upper = ema + (multiplier * atr)
            lower = ema - (multiplier * atr)
            
            return {
                'upper': upper,
                'middle': ema,
                'lower': lower
            }
        except:
            return {'upper': np.array([]), 'middle': np.array([]), 'lower': np.array([])}
    
    def _calculate_vwap(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate Volume Weighted Average Price"""
        try:
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
            return vwap.values
        except:
            return np.full(len(df), np.nan)
    
    def _calculate_pivot_levels(self, df: pd.DataFrame) -> Dict:
        """Calculate pivot point levels"""
        try:
            # Use last complete day's data
            last_high = df['high'].iloc[-1]
            last_low = df['low'].iloc[-1]
            last_close = df['close'].iloc[-1]
            
            pivot = (last_high + last_low + last_close) / 3
            
            # Support and resistance levels
            r1 = 2 * pivot - last_low
            s1 = 2 * pivot - last_high
            r2 = pivot + (last_high - last_low)
            s2 = pivot - (last_high - last_low)
            r3 = last_high + 2 * (pivot - last_low)
            s3 = last_low - 2 * (last_high - pivot)
            
            return {
                'pivot': pivot,
                'r1': r1, 'r2': r2, 'r3': r3,
                's1': s1, 's2': s2, 's3': s3
            }
        except:
            return {}
    
    def _calculate_fibonacci_levels(self, df: pd.DataFrame, lookback: int = 50) -> Dict:
        """Calculate Fibonacci retracement levels"""
        try:
            recent_data = df.tail(lookback)
            high_price = recent_data['high'].max()
            low_price = recent_data['low'].min()
            
            diff = high_price - low_price
            
            levels = {}
            fib_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
            
            for ratio in fib_ratios:
                levels[f'fib_{ratio}'] = high_price - (diff * ratio)
            
            return levels
        except:
            return {}
    
    def _generate_signals(self, df: pd.DataFrame, indicators: Dict, symbol: str, timeframe: str) -> List[Dict]:
        """Generate trading signals based on technical analysis"""
        signals = []
        current_price = df['close'].iloc[-1]
        
        try:
            # Trend Analysis
            trend_signals = self._analyze_trend(indicators, current_price)
            signals.extend(trend_signals)
            
            # Momentum Analysis
            momentum_signals = self._analyze_momentum(indicators, current_price)
            signals.extend(momentum_signals)
            
            # Mean Reversion Analysis
            mean_reversion_signals = self._analyze_mean_reversion(indicators, current_price)
            signals.extend(mean_reversion_signals)
            
            # Breakout Analysis
            breakout_signals = self._analyze_breakouts(indicators, df, current_price)
            signals.extend(breakout_signals)
            
        except Exception as e:
            logger.error(f"Error generating TA signals: {e}")
        
        return signals
    
    def _analyze_trend(self, indicators: Dict, current_price: float) -> List[Dict]:
        """Analyze trend-following signals"""
        signals = []
        
        try:
            # Moving Average Crossovers
            if 'ma' in indicators:
                ma_data = indicators['ma']
                
                # Golden Cross (50 > 200)
                if 'ma_50' in ma_data and 'ma_200' in ma_data:
                    ma50 = ma_data['ma_50']
                    ma200 = ma_data['ma_200']
                    
                    if (len(ma50) > 1 and len(ma200) > 1 and 
                        not np.isnan(ma50[-1]) and not np.isnan(ma200[-1]) and
                        not np.isnan(ma50[-2]) and not np.isnan(ma200[-2])):
                        
                        if ma50[-2] <= ma200[-2] and ma50[-1] > ma200[-1]:
                            signals.append({
                                'type': 'golden_cross',
                                'direction': SignalDirection.LONG,
                                'confidence': 75,
                                'entry': current_price,
                                'reason': 'MA50 crossed above MA200 (Golden Cross)'
                            })
                        elif ma50[-2] >= ma200[-2] and ma50[-1] < ma200[-1]:
                            signals.append({
                                'type': 'death_cross',
                                'direction': SignalDirection.SHORT,
                                'confidence': 75,
                                'entry': current_price,
                                'reason': 'MA50 crossed below MA200 (Death Cross)'
                            })
            
            # ADX Trend Strength
            if 'adx' in indicators:
                adx = indicators['adx']
                plus_di = indicators.get('plus_di')
                minus_di = indicators.get('minus_di')
                
                if (len(adx) > 0 and not np.isnan(adx[-1]) and adx[-1] > 25 and
                    plus_di is not None and minus_di is not None and
                    len(plus_di) > 0 and len(minus_di) > 0):
                    
                    if plus_di[-1] > minus_di[-1] and adx[-1] > 30:
                        signals.append({
                            'type': 'adx_trend_long',
                            'direction': SignalDirection.LONG,
                            'confidence': min(80, 50 + adx[-1]),
                            'entry': current_price,
                            'reason': f'Strong uptrend confirmed by ADX ({adx[-1]:.1f})'
                        })
                    elif minus_di[-1] > plus_di[-1] and adx[-1] > 30:
                        signals.append({
                            'type': 'adx_trend_short',
                            'direction': SignalDirection.SHORT,
                            'confidence': min(80, 50 + adx[-1]),
                            'entry': current_price,
                            'reason': f'Strong downtrend confirmed by ADX ({adx[-1]:.1f})'
                        })
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
        
        return signals
    
    def _analyze_momentum(self, indicators: Dict, current_price: float) -> List[Dict]:
        """Analyze momentum-based signals"""
        signals = []
        
        try:
            # RSI Signals
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                if len(rsi) > 1 and not np.isnan(rsi[-1]):
                    # RSI Oversold/Overbought
                    if rsi[-1] < 30 and rsi[-2] >= 30:
                        signals.append({
                            'type': 'rsi_oversold',
                            'direction': SignalDirection.LONG,
                            'confidence': 60,
                            'entry': current_price,
                            'reason': f'RSI oversold bounce ({rsi[-1]:.1f})'
                        })
                    elif rsi[-1] > 70 and rsi[-2] <= 70:
                        signals.append({
                            'type': 'rsi_overbought',
                            'direction': SignalDirection.SHORT,
                            'confidence': 60,
                            'entry': current_price,
                            'reason': f'RSI overbought reversal ({rsi[-1]:.1f})'
                        })
                    
                    # RSI Divergence (simplified)
                    if len(rsi) > 5:
                        if rsi[-1] > 50 and rsi[-5] < rsi[-1]:  # Bullish momentum
                            signals.append({
                                'type': 'rsi_bullish_momentum',
                                'direction': SignalDirection.LONG,
                                'confidence': 55,
                                'entry': current_price,
                                'reason': 'RSI showing bullish momentum'
                            })
            
            # MACD Signals
            if 'macd' in indicators:
                macd_data = indicators['macd']
                macd_line = macd_data['macd']
                signal_line = macd_data['signal']
                histogram = macd_data['histogram']
                
                if (len(macd_line) > 1 and len(signal_line) > 1 and
                    not np.isnan(macd_line[-1]) and not np.isnan(signal_line[-1])):
                    
                    # MACD Crossover
                    if (macd_line[-2] <= signal_line[-2] and 
                        macd_line[-1] > signal_line[-1]):
                        signals.append({
                            'type': 'macd_bullish_cross',
                            'direction': SignalDirection.LONG,
                            'confidence': 65,
                            'entry': current_price,
                            'reason': 'MACD bullish crossover'
                        })
                    elif (macd_line[-2] >= signal_line[-2] and 
                          macd_line[-1] < signal_line[-1]):
                        signals.append({
                            'type': 'macd_bearish_cross',
                            'direction': SignalDirection.SHORT,
                            'confidence': 65,
                            'entry': current_price,
                            'reason': 'MACD bearish crossover'
                        })
            
        except Exception as e:
            logger.error(f"Error in momentum analysis: {e}")
        
        return signals
    
    def _analyze_mean_reversion(self, indicators: Dict, current_price: float) -> List[Dict]:
        """Analyze mean reversion signals"""
        signals = []
        
        try:
            # Bollinger Bands
            if 'bollinger' in indicators:
                bb = indicators['bollinger']
                upper = bb['upper']
                lower = bb['lower']
                middle = bb['middle']
                
                if (len(upper) > 0 and len(lower) > 0 and len(middle) > 0 and
                    not np.isnan(upper[-1]) and not np.isnan(lower[-1])):
                    
                    # Price touching bands
                    if current_price <= lower[-1]:
                        signals.append({
                            'type': 'bb_oversold',
                            'direction': SignalDirection.LONG,
                            'confidence': 55,
                            'entry': current_price,
                            'reason': 'Price at Bollinger Band lower bound'
                        })
                    elif current_price >= upper[-1]:
                        signals.append({
                            'type': 'bb_overbought',
                            'direction': SignalDirection.SHORT,
                            'confidence': 55,
                            'entry': current_price,
                            'reason': 'Price at Bollinger Band upper bound'
                        })
            
            # VWAP Mean Reversion
            if 'vwap' in indicators:
                vwap = indicators['vwap']
                if len(vwap) > 0 and not np.isnan(vwap[-1]):
                    deviation = abs(current_price - vwap[-1]) / vwap[-1]
                    
                    if deviation > 0.02:  # 2% deviation
                        if current_price < vwap[-1]:
                            signals.append({
                                'type': 'vwap_reversion_long',
                                'direction': SignalDirection.LONG,
                                'confidence': 50,
                                'entry': current_price,
                                'reason': f'Price {deviation*100:.1f}% below VWAP'
                            })
                        else:
                            signals.append({
                                'type': 'vwap_reversion_short',
                                'direction': SignalDirection.SHORT,
                                'confidence': 50,
                                'entry': current_price,
                                'reason': f'Price {deviation*100:.1f}% above VWAP'
                            })
            
        except Exception as e:
            logger.error(f"Error in mean reversion analysis: {e}")
        
        return signals
    
    def _analyze_breakouts(self, indicators: Dict, df: pd.DataFrame, current_price: float) -> List[Dict]:
        """Analyze breakout signals"""
        signals = []
        
        try:
            # Donchian Channel Breakouts
            if 'donchian' in indicators:
                upper = indicators['donchian']['upper']
                lower = indicators['donchian']['lower']
                
                if len(upper) > 1 and len(lower) > 1:
                    prev_high = df['high'].iloc[-2]
                    prev_low = df['low'].iloc[-2]
                    
                    # Breakout above channel
                    if (prev_high <= upper[-2] and current_price > upper[-1]):
                        signals.append({
                            'type': 'donchian_breakout_long',
                            'direction': SignalDirection.LONG,
                            'confidence': 70,
                            'entry': current_price,
                            'reason': 'Breakout above Donchian Channel'
                        })
                    # Breakdown below channel
                    elif (prev_low >= lower[-2] and current_price < lower[-1]):
                        signals.append({
                            'type': 'donchian_breakout_short',
                            'direction': SignalDirection.SHORT,
                            'confidence': 70,
                            'entry': current_price,
                            'reason': 'Breakdown below Donchian Channel'
                        })
            
            # Volume Breakouts
            if 'volume_ratio' in indicators:
                vol_ratio = indicators['volume_ratio']
                if len(vol_ratio) > 0 and not np.isnan(vol_ratio[-1]) and vol_ratio[-1] > 2.0:
                    # High volume suggests strong move
                    recent_change = (current_price - df['close'].iloc[-2]) / df['close'].iloc[-2]
                    
                    if recent_change > 0.01:  # 1% up with high volume
                        signals.append({
                            'type': 'volume_breakout_long',
                            'direction': SignalDirection.LONG,
                            'confidence': 60,
                            'entry': current_price,
                            'reason': f'High volume breakout ({vol_ratio[-1]:.1f}x avg volume)'
                        })
                    elif recent_change < -0.01:  # 1% down with high volume
                        signals.append({
                            'type': 'volume_breakout_short',
                            'direction': SignalDirection.SHORT,
                            'confidence': 60,
                            'entry': current_price,
                            'reason': f'High volume breakdown ({vol_ratio[-1]:.1f}x avg volume)'
                        })
            
        except Exception as e:
            logger.error(f"Error in breakout analysis: {e}")
        
        return signals
    
    def _calculate_confidence(self, indicators: Dict, signals: List[Dict]) -> float:
        """Calculate overall confidence for technical analysis"""
        if not signals:
            return 0.0
        
        try:
            # Weight signals by their individual confidence
            total_confidence = sum(signal['confidence'] for signal in signals)
            avg_confidence = total_confidence / len(signals)
            
            # Adjust based on signal consensus
            long_signals = [s for s in signals if s['direction'] == SignalDirection.LONG]
            short_signals = [s for s in signals if s['direction'] == SignalDirection.SHORT]
            
            if len(long_signals) > 0 and len(short_signals) > 0:
                # Mixed signals reduce confidence
                avg_confidence *= 0.7
            elif len(long_signals) > 2 or len(short_signals) > 2:
                # Multiple confirming signals increase confidence
                avg_confidence *= 1.2
            
            return min(95.0, max(0.0, avg_confidence))
            
        except:
            return 0.0