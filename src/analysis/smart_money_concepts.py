"""
Smart Money Concepts (SMC) Analysis Implementation
Includes BOS/CHOCH, FVG, Order Blocks, Liquidity zones, Premium/Discount areas
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

from src.models import AnalysisResult, AnalysisMethod, SignalDirection
from config import settings

logger = logging.getLogger(__name__)

class SmartMoneyAnalyzer:
    """Smart Money Concepts analysis implementation"""
    
    def __init__(self):
        self.config = settings.analysis
        self.swing_length = self.config.smc_swing_length
        self.fvg_threshold = self.config.fvg_threshold
    
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> AnalysisResult:
        """Perform Smart Money Concepts analysis"""
        try:
            if len(df) < 50:  # Need enough data for SMC analysis
                logger.warning(f"Insufficient data for SMC analysis: {len(df)} bars")
                return AnalysisResult(
                    method=AnalysisMethod.SMART_MONEY_CONCEPTS,
                    symbol=symbol,
                    timeframe=timeframe,
                    confidence=0.0
                )
            
            # Detect market structure
            structure = self._detect_market_structure(df)
            
            # Find swing points
            swing_highs, swing_lows = self._find_swing_points(df)
            
            # Detect BOS/CHOCH
            bos_choch = self._detect_bos_choch(df, swing_highs, swing_lows, structure)
            
            # Find Fair Value Gaps
            fvg_zones = self._find_fair_value_gaps(df)
            
            # Identify Order Blocks
            order_blocks = self._find_order_blocks(df, swing_highs, swing_lows)
            
            # Find liquidity zones
            liquidity_zones = self._find_liquidity_zones(df, swing_highs, swing_lows)
            
            # Determine premium/discount zones
            premium_discount = self._calculate_premium_discount_zones(df, swing_highs, swing_lows)
            
            # Generate signals
            signals = self._generate_smc_signals(
                df, structure, bos_choch, fvg_zones, order_blocks, 
                liquidity_zones, premium_discount, symbol, timeframe
            )
            
            # Calculate confidence
            confidence = self._calculate_smc_confidence(
                structure, bos_choch, fvg_zones, order_blocks, signals
            )
            
            smc_data = {
                'market_structure': structure,
                'swing_highs': swing_highs,
                'swing_lows': swing_lows,
                'bos_choch': bos_choch,
                'fair_value_gaps': fvg_zones,
                'order_blocks': order_blocks,
                'liquidity_zones': liquidity_zones,
                'premium_discount': premium_discount
            }
            
            return AnalysisResult(
                method=AnalysisMethod.SMART_MONEY_CONCEPTS,
                symbol=symbol,
                timeframe=timeframe,
                confidence=confidence,
                data=smc_data,
                potential_signals=signals
            )
            
        except Exception as e:
            logger.error(f"Error in SMC analysis: {e}")
            return AnalysisResult(
                method=AnalysisMethod.SMART_MONEY_CONCEPTS,
                symbol=symbol,
                timeframe=timeframe,
                confidence=0.0
            )
    
    def _detect_market_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect overall market structure (uptrend/downtrend/sideways)"""
        try:
            # Use recent price action to determine structure
            recent_bars = min(50, len(df))
            recent_data = df.tail(recent_bars)
            
            # Calculate structure based on higher highs/lower lows
            highs = recent_data['high'].values
            lows = recent_data['low'].values
            
            # Find significant highs and lows
            high_peaks = []
            low_valleys = []
            
            for i in range(2, len(highs) - 2):
                if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                    highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                    high_peaks.append((i, highs[i]))
                
                if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                    lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                    low_valleys.append((i, lows[i]))
            
            structure_type = "sideways"
            trend_strength = 0
            
            if len(high_peaks) >= 2 and len(low_valleys) >= 2:
                # Check for higher highs and higher lows (uptrend)
                recent_highs = [h[1] for h in high_peaks[-2:]]
                recent_lows = [l[1] for l in low_valleys[-2:]]
                
                if len(recent_highs) == 2 and len(recent_lows) == 2:
                    if recent_highs[1] > recent_highs[0] and recent_lows[1] > recent_lows[0]:
                        structure_type = "uptrend"
                        trend_strength = min(100, abs((recent_highs[1] - recent_highs[0]) / recent_highs[0]) * 1000)
                    elif recent_highs[1] < recent_highs[0] and recent_lows[1] < recent_lows[0]:
                        structure_type = "downtrend"
                        trend_strength = min(100, abs((recent_highs[0] - recent_highs[1]) / recent_highs[0]) * 1000)
            
            return {
                'type': structure_type,
                'strength': trend_strength,
                'high_peaks': high_peaks,
                'low_valleys': low_valleys,
                'last_update': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error detecting market structure: {e}")
            return {'type': 'unknown', 'strength': 0}
    
    def _find_swing_points(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """Find swing high and low points"""
        try:
            swing_highs = []
            swing_lows = []
            
            highs = df['high'].values
            lows = df['low'].values
            
            for i in range(self.swing_length, len(df) - self.swing_length):
                # Check for swing high
                is_swing_high = True
                for j in range(i - self.swing_length, i + self.swing_length + 1):
                    if j != i and highs[j] >= highs[i]:
                        is_swing_high = False
                        break
                
                if is_swing_high:
                    swing_highs.append({
                        'index': i,
                        'price': highs[i],
                        'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i
                    })
                
                # Check for swing low
                is_swing_low = True
                for j in range(i - self.swing_length, i + self.swing_length + 1):
                    if j != i and lows[j] <= lows[i]:
                        is_swing_low = False
                        break
                
                if is_swing_low:
                    swing_lows.append({
                        'index': i,
                        'price': lows[i],
                        'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i
                    })
            
            return swing_highs, swing_lows
            
        except Exception as e:
            logger.error(f"Error finding swing points: {e}")
            return [], []
    
    def _detect_bos_choch(self, df: pd.DataFrame, swing_highs: List[Dict], 
                         swing_lows: List[Dict], structure: Dict) -> List[Dict]:
        """Detect Break of Structure (BOS) and Change of Character (CHOCH)"""
        try:
            bos_choch_events = []
            current_price = df['close'].iloc[-1]
            
            # Recent swing points for analysis
            recent_highs = [h for h in swing_highs if h['index'] >= len(df) - 30]
            recent_lows = [l for l in swing_lows if l['index'] >= len(df) - 30]
            
            if not recent_highs and not recent_lows:
                return bos_choch_events
            
            # Check for BOS (Break of Structure)
            if structure['type'] == 'uptrend':
                # Look for break below recent swing low
                for swing_low in recent_lows[-2:]:  # Last 2 swing lows
                    if current_price < swing_low['price'] * 0.999:  # Small buffer
                        bos_choch_events.append({
                            'type': 'BOS',
                            'direction': 'bearish',
                            'level': swing_low['price'],
                            'current_price': current_price,
                            'strength': abs(current_price - swing_low['price']) / swing_low['price'] * 100,
                            'timestamp': datetime.utcnow()
                        })
            
            elif structure['type'] == 'downtrend':
                # Look for break above recent swing high
                for swing_high in recent_highs[-2:]:  # Last 2 swing highs
                    if current_price > swing_high['price'] * 1.001:  # Small buffer
                        bos_choch_events.append({
                            'type': 'BOS',
                            'direction': 'bullish',
                            'level': swing_high['price'],
                            'current_price': current_price,
                            'strength': abs(current_price - swing_high['price']) / swing_high['price'] * 100,
                            'timestamp': datetime.utcnow()
                        })
            
            # Check for CHOCH (Change of Character)
            # CHOCH occurs when price breaks structure but then quickly reverses
            if len(df) > 10:
                recent_range = df.tail(10)
                price_volatility = recent_range['high'].max() - recent_range['low'].min()
                avg_price = recent_range['close'].mean()
                volatility_ratio = price_volatility / avg_price
                
                if volatility_ratio > 0.02:  # High volatility suggests CHOCH
                    bos_choch_events.append({
                        'type': 'CHOCH',
                        'direction': 'neutral',
                        'volatility': volatility_ratio,
                        'description': 'High volatility suggests change of character',
                        'timestamp': datetime.utcnow()
                    })
            
            return bos_choch_events
            
        except Exception as e:
            logger.error(f"Error detecting BOS/CHOCH: {e}")
            return []
    
    def _find_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Find Fair Value Gaps (FVG) - imbalances in price action"""
        try:
            fvg_zones = []
            
            for i in range(2, len(df)):
                # Bullish FVG: gap between candle[i-2].low and candle[i].high
                # where candle[i-1] doesn't fill the gap
                prev2_low = df['low'].iloc[i-2]
                prev1_high = df['high'].iloc[i-1]
                prev1_low = df['low'].iloc[i-1]
                current_high = df['high'].iloc[i]
                
                # Bullish FVG
                if (prev2_low > current_high and 
                    prev1_high < prev2_low and prev1_low > current_high):
                    
                    gap_size = (prev2_low - current_high) / current_high
                    if gap_size > self.fvg_threshold:
                        fvg_zones.append({
                            'type': 'bullish_fvg',
                            'top': prev2_low,
                            'bottom': current_high,
                            'index': i,
                            'size': gap_size,
                            'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i,
                            'filled': False
                        })
                
                # Bearish FVG: gap between candle[i-2].high and candle[i].low
                prev2_high = df['high'].iloc[i-2]
                current_low = df['low'].iloc[i]
                
                if (prev2_high < current_low and 
                    prev1_low > prev2_high and prev1_high < current_low):
                    
                    gap_size = (current_low - prev2_high) / prev2_high
                    if gap_size > self.fvg_threshold:
                        fvg_zones.append({
                            'type': 'bearish_fvg',
                            'top': current_low,
                            'bottom': prev2_high,
                            'index': i,
                            'size': gap_size,
                            'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i,
                            'filled': False
                        })
            
            # Check if recent price action has filled any gaps
            current_price = df['close'].iloc[-1]
            for fvg in fvg_zones:
                if (current_price >= fvg['bottom'] and current_price <= fvg['top']):
                    fvg['filled'] = True
            
            # Return only unfilled gaps from recent periods
            recent_fvgs = [fvg for fvg in fvg_zones if not fvg['filled'] and 
                          fvg['index'] >= len(df) - 50]
            
            return recent_fvgs
            
        except Exception as e:
            logger.error(f"Error finding FVG zones: {e}")
            return []
    
    def _find_order_blocks(self, df: pd.DataFrame, swing_highs: List[Dict], 
                          swing_lows: List[Dict]) -> List[Dict]:
        """Find Order Blocks - areas where smart money placed large orders"""
        try:
            order_blocks = []
            
            # Bullish Order Blocks: candles before swing lows with strong rejection
            for swing_low in swing_lows[-10:]:  # Recent swing lows
                swing_idx = swing_low['index']
                
                # Look for the last bearish candle before the swing low
                for i in range(max(0, swing_idx - 5), swing_idx):
                    candle_open = df['open'].iloc[i]
                    candle_close = df['close'].iloc[i]
                    candle_high = df['high'].iloc[i]
                    candle_low = df['low'].iloc[i]
                    
                    # Bearish candle with strong volume (if available)
                    if candle_close < candle_open:
                        # This could be a bullish order block
                        order_blocks.append({
                            'type': 'bullish_ob',
                            'top': candle_high,
                            'bottom': candle_low,
                            'index': i,
                            'swing_reference': swing_low,
                            'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i,
                            'tested': False
                        })
                        break  # Take the last bearish candle
            
            # Bearish Order Blocks: candles before swing highs with strong rejection
            for swing_high in swing_highs[-10:]:  # Recent swing highs
                swing_idx = swing_high['index']
                
                # Look for the last bullish candle before the swing high
                for i in range(max(0, swing_idx - 5), swing_idx):
                    candle_open = df['open'].iloc[i]
                    candle_close = df['close'].iloc[i]
                    candle_high = df['high'].iloc[i]
                    candle_low = df['low'].iloc[i]
                    
                    # Bullish candle
                    if candle_close > candle_open:
                        # This could be a bearish order block
                        order_blocks.append({
                            'type': 'bearish_ob',
                            'top': candle_high,
                            'bottom': candle_low,
                            'index': i,
                            'swing_reference': swing_high,
                            'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i,
                            'tested': False
                        })
                        break  # Take the last bullish candle
            
            # Check if order blocks have been tested
            current_price = df['close'].iloc[-1]
            for ob in order_blocks:
                if (current_price >= ob['bottom'] and current_price <= ob['top']):
                    ob['tested'] = True
            
            # Remove duplicates and sort by recency
            unique_obs = []
            seen_levels = set()
            
            for ob in sorted(order_blocks, key=lambda x: x['index'], reverse=True):
                level_key = f"{ob['type']}_{ob['top']:.6f}_{ob['bottom']:.6f}"
                if level_key not in seen_levels:
                    unique_obs.append(ob)
                    seen_levels.add(level_key)
            
            return unique_obs[:10]  # Return top 10 most recent
            
        except Exception as e:
            logger.error(f"Error finding order blocks: {e}")
            return []
    
    def _find_liquidity_zones(self, df: pd.DataFrame, swing_highs: List[Dict], 
                             swing_lows: List[Dict]) -> List[Dict]:
        """Find liquidity zones - areas where stops are likely placed"""
        try:
            liquidity_zones = []
            
            # Equal Highs (EQH) - multiple swing highs at similar levels
            if len(swing_highs) >= 2:
                for i, high1 in enumerate(swing_highs[:-1]):
                    for high2 in swing_highs[i+1:]:
                        price_diff = abs(high1['price'] - high2['price']) / high1['price']
                        if price_diff < 0.005:  # Within 0.5%
                            liquidity_zones.append({
                                'type': 'EQH',
                                'level': (high1['price'] + high2['price']) / 2,
                                'strength': 2,  # Number of touches
                                'direction': 'resistance',
                                'last_test': max(high1['timestamp'], high2['timestamp'])
                            })
            
            # Equal Lows (EQL) - multiple swing lows at similar levels
            if len(swing_lows) >= 2:
                for i, low1 in enumerate(swing_lows[:-1]):
                    for low2 in swing_lows[i+1:]:
                        price_diff = abs(low1['price'] - low2['price']) / low1['price']
                        if price_diff < 0.005:  # Within 0.5%
                            liquidity_zones.append({
                                'type': 'EQL',
                                'level': (low1['price'] + low2['price']) / 2,
                                'strength': 2,  # Number of touches
                                'direction': 'support',
                                'last_test': max(low1['timestamp'], low2['timestamp'])
                            })
            
            # Remove duplicates
            unique_zones = []
            seen_levels = set()
            
            for zone in liquidity_zones:
                level_key = f"{zone['type']}_{zone['level']:.6f}"
                if level_key not in seen_levels:
                    unique_zones.append(zone)
                    seen_levels.add(level_key)
            
            return unique_zones
            
        except Exception as e:
            logger.error(f"Error finding liquidity zones: {e}")
            return []
    
    def _calculate_premium_discount_zones(self, df: pd.DataFrame, 
                                        swing_highs: List[Dict], 
                                        swing_lows: List[Dict]) -> Dict:
        """Calculate premium and discount zones based on recent range"""
        try:
            if not swing_highs or not swing_lows:
                return {}
            
            # Get recent high and low
            recent_high = max([h['price'] for h in swing_highs[-3:]] if len(swing_highs) >= 3 else [h['price'] for h in swing_highs])
            recent_low = min([l['price'] for l in swing_lows[-3:]] if len(swing_lows) >= 3 else [l['price'] for l in swing_lows])
            
            range_size = recent_high - recent_low
            
            # Define zones
            premium_zone = {
                'start': recent_low + (range_size * 0.618),  # 61.8% of range
                'end': recent_high,
                'type': 'premium'
            }
            
            discount_zone = {
                'start': recent_low,
                'end': recent_low + (range_size * 0.382),  # 38.2% of range
                'type': 'discount'
            }
            
            equilibrium = recent_low + (range_size * 0.5)
            
            current_price = df['close'].iloc[-1]
            
            # Determine current zone
            current_zone = 'equilibrium'
            if current_price >= premium_zone['start']:
                current_zone = 'premium'
            elif current_price <= discount_zone['end']:
                current_zone = 'discount'
            
            return {
                'premium_zone': premium_zone,
                'discount_zone': discount_zone,
                'equilibrium': equilibrium,
                'current_zone': current_zone,
                'range_high': recent_high,
                'range_low': recent_low
            }
            
        except Exception as e:
            logger.error(f"Error calculating premium/discount zones: {e}")
            return {}
    
    def _generate_smc_signals(self, df: pd.DataFrame, structure: Dict, 
                             bos_choch: List[Dict], fvg_zones: List[Dict],
                             order_blocks: List[Dict], liquidity_zones: List[Dict],
                             premium_discount: Dict, symbol: str, timeframe: str) -> List[Dict]:
        """Generate trading signals based on SMC analysis"""
        signals = []
        current_price = df['close'].iloc[-1]
        
        try:
            # BOS/CHOCH Signals
            for event in bos_choch:
                if event['type'] == 'BOS':
                    confidence = min(80, 50 + event['strength'])
                    signals.append({
                        'type': 'smc_bos',
                        'direction': SignalDirection.LONG if event['direction'] == 'bullish' else SignalDirection.SHORT,
                        'confidence': confidence,
                        'entry': current_price,
                        'reason': f"Break of Structure ({event['direction']}) at {event['level']:.4f}"
                    })
            
            # Fair Value Gap Signals
            for fvg in fvg_zones:
                if not fvg['filled']:
                    # Price approaching FVG
                    distance_to_fvg = min(
                        abs(current_price - fvg['top']),
                        abs(current_price - fvg['bottom'])
                    ) / current_price
                    
                    if distance_to_fvg < 0.01:  # Within 1% of FVG
                        direction = SignalDirection.LONG if fvg['type'] == 'bullish_fvg' else SignalDirection.SHORT
                        signals.append({
                            'type': 'smc_fvg',
                            'direction': direction,
                            'confidence': 65,
                            'entry': current_price,
                            'reason': f"Price approaching {fvg['type']} FVG zone"
                        })
            
            # Order Block Signals
            for ob in order_blocks:
                if not ob['tested']:
                    # Price approaching untested order block
                    if (current_price >= ob['bottom'] * 0.995 and 
                        current_price <= ob['top'] * 1.005):
                        
                        direction = SignalDirection.LONG if ob['type'] == 'bullish_ob' else SignalDirection.SHORT
                        signals.append({
                            'type': 'smc_order_block',
                            'direction': direction,
                            'confidence': 70,
                            'entry': current_price,
                            'reason': f"Price testing {ob['type']} order block"
                        })
            
            # Premium/Discount Zone Signals
            if premium_discount:
                current_zone = premium_discount['current_zone']
                
                if current_zone == 'discount' and structure['type'] == 'uptrend':
                    signals.append({
                        'type': 'smc_discount_buy',
                        'direction': SignalDirection.LONG,
                        'confidence': 60,
                        'entry': current_price,
                        'reason': 'Price in discount zone during uptrend'
                    })
                elif current_zone == 'premium' and structure['type'] == 'downtrend':
                    signals.append({
                        'type': 'smc_premium_sell',
                        'direction': SignalDirection.SHORT,
                        'confidence': 60,
                        'entry': current_price,
                        'reason': 'Price in premium zone during downtrend'
                    })
            
            # Liquidity Hunt Signals
            for liq_zone in liquidity_zones:
                distance_to_liquidity = abs(current_price - liq_zone['level']) / current_price
                
                if distance_to_liquidity < 0.005:  # Within 0.5%
                    # Expect liquidity grab and reversal
                    direction = (SignalDirection.SHORT if liq_zone['direction'] == 'resistance' 
                               else SignalDirection.LONG)
                    
                    signals.append({
                        'type': 'smc_liquidity_hunt',
                        'direction': direction,
                        'confidence': 55,
                        'entry': current_price,
                        'reason': f'Price approaching {liq_zone["type"]} liquidity zone'
                    })
            
        except Exception as e:
            logger.error(f"Error generating SMC signals: {e}")
        
        return signals
    
    def _calculate_smc_confidence(self, structure: Dict, bos_choch: List[Dict],
                                 fvg_zones: List[Dict], order_blocks: List[Dict],
                                 signals: List[Dict]) -> float:
        """Calculate overall confidence for SMC analysis"""
        if not signals:
            return 0.0
        
        try:
            base_confidence = 0.0
            
            # Structure clarity adds confidence
            if structure['type'] != 'sideways':
                base_confidence += 20 + (structure['strength'] * 0.3)
            
            # BOS/CHOCH events add confidence
            if bos_choch:
                base_confidence += len(bos_choch) * 15
            
            # Unfilled FVGs add confidence
            unfilled_fvgs = [fvg for fvg in fvg_zones if not fvg['filled']]
            if unfilled_fvgs:
                base_confidence += len(unfilled_fvgs) * 10
            
            # Untested order blocks add confidence
            untested_obs = [ob for ob in order_blocks if not ob['tested']]
            if untested_obs:
                base_confidence += len(untested_obs) * 12
            
            # Signal consensus
            if signals:
                signal_confidence = sum(signal['confidence'] for signal in signals) / len(signals)
                base_confidence = (base_confidence + signal_confidence) / 2
            
            return min(95.0, max(0.0, base_confidence))
            
        except:
            return 0.0