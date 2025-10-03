"""
Elliott Wave Analysis Implementation
Auto-detection of wave patterns with Fibonacci relationships
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
from enum import Enum

from src.models import AnalysisResult, AnalysisMethod, SignalDirection
from config import settings

logger = logging.getLogger(__name__)

class WaveType(Enum):
    IMPULSE = "impulse"
    CORRECTIVE = "corrective"
    
class WaveLabel(Enum):
    # Impulse waves
    WAVE_1 = "1"
    WAVE_2 = "2"
    WAVE_3 = "3"
    WAVE_4 = "4"
    WAVE_5 = "5"
    
    # Corrective waves
    WAVE_A = "A"
    WAVE_B = "B"
    WAVE_C = "C"
    WAVE_W = "W"
    WAVE_X = "X"
    WAVE_Y = "Y"
    WAVE_Z = "Z"

class ElliottWaveAnalyzer:
    """Elliott Wave analysis implementation"""
    
    def __init__(self):
        self.config = settings.analysis
        self.min_swing_size = self.config.wave_min_swing_size
        self.fib_levels = self.config.fib_levels
        
        # Wave validation tolerances
        self.fib_tolerance = 0.05  # 5% tolerance for Fibonacci ratios
        
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> AnalysisResult:
        """Perform Elliott Wave analysis"""
        try:
            if len(df) < 100:  # Need enough data for wave analysis
                logger.warning(f"Insufficient data for Elliott Wave analysis: {len(df)} bars")
                return AnalysisResult(
                    method=AnalysisMethod.ELLIOTT_WAVE,
                    symbol=symbol,
                    timeframe=timeframe,
                    confidence=0.0
                )
            
            # Find significant swing points
            swing_points = self._find_significant_swings(df)
            
            if len(swing_points) < 5:
                return AnalysisResult(
                    method=AnalysisMethod.ELLIOTT_WAVE,
                    symbol=symbol,
                    timeframe=timeframe,
                    confidence=0.0,
                    data={'swing_points': swing_points}
                )
            
            # Detect wave patterns
            wave_patterns = self._detect_wave_patterns(swing_points, df)
            
            # Validate wave relationships
            validated_patterns = self._validate_wave_patterns(wave_patterns)
            
            # Calculate Fibonacci relationships
            fib_analysis = self._analyze_fibonacci_relationships(validated_patterns)
            
            # Generate wave projections
            projections = self._generate_wave_projections(validated_patterns, df)
            
            # Generate signals
            signals = self._generate_wave_signals(
                validated_patterns, projections, df, symbol, timeframe
            )
            
            # Calculate confidence
            confidence = self._calculate_wave_confidence(
                validated_patterns, fib_analysis, signals
            )
            
            wave_data = {
                'swing_points': swing_points,
                'wave_patterns': validated_patterns,
                'fibonacci_analysis': fib_analysis,
                'projections': projections,
                'current_wave_count': self._get_current_wave_count(validated_patterns)
            }
            
            return AnalysisResult(
                method=AnalysisMethod.ELLIOTT_WAVE,
                symbol=symbol,
                timeframe=timeframe,
                confidence=confidence,
                data=wave_data,
                potential_signals=signals
            )
            
        except Exception as e:
            logger.error(f"Error in Elliott Wave analysis: {e}")
            return AnalysisResult(
                method=AnalysisMethod.ELLIOTT_WAVE,
                symbol=symbol,
                timeframe=timeframe,
                confidence=0.0
            )
    
    def _find_significant_swings(self, df: pd.DataFrame) -> List[Dict]:
        """Find significant swing points for wave analysis"""
        try:
            swing_points = []
            
            # Use ZigZag approach to find significant swings
            highs = df['high'].values
            lows = df['low'].values
            closes = df['close'].values
            
            # Calculate minimum swing size based on recent volatility
            recent_atr = self._calculate_atr(df, 14)
            min_swing = recent_atr * 2  # Minimum swing is 2x ATR
            
            # Find swing highs and lows
            last_swing_high = None
            last_swing_low = None
            
            for i in range(5, len(df) - 5):
                current_high = highs[i]
                current_low = lows[i]
                
                # Check for swing high
                is_swing_high = True
                for j in range(i - 5, i + 6):
                    if j != i and highs[j] >= current_high:
                        is_swing_high = False
                        break
                
                if is_swing_high:
                    # Validate swing size
                    if (last_swing_low is None or 
                        current_high - last_swing_low['price'] >= min_swing):
                        
                        swing_point = {
                            'index': i,
                            'price': current_high,
                            'type': 'high',
                            'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i
                        }
                        swing_points.append(swing_point)
                        last_swing_high = swing_point
                
                # Check for swing low
                is_swing_low = True
                for j in range(i - 5, i + 6):
                    if j != i and lows[j] <= current_low:
                        is_swing_low = False
                        break
                
                if is_swing_low:
                    # Validate swing size
                    if (last_swing_high is None or 
                        last_swing_high['price'] - current_low >= min_swing):
                        
                        swing_point = {
                            'index': i,
                            'price': current_low,
                            'type': 'low',
                            'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i
                        }
                        swing_points.append(swing_point)
                        last_swing_low = swing_point
            
            # Sort by index
            swing_points.sort(key=lambda x: x['index'])
            
            return swing_points
            
        except Exception as e:
            logger.error(f"Error finding significant swings: {e}")
            return []
    
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
                return np.mean(tr_list[-period:])
            else:
                return np.mean(tr_list) if tr_list else 0.01
                
        except:
            return 0.01
    
    def _detect_wave_patterns(self, swing_points: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """Detect Elliott Wave patterns in swing points"""
        try:
            patterns = []
            
            # Look for 5-wave impulse patterns
            impulse_patterns = self._find_impulse_patterns(swing_points)
            patterns.extend(impulse_patterns)
            
            # Look for 3-wave corrective patterns
            corrective_patterns = self._find_corrective_patterns(swing_points)
            patterns.extend(corrective_patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting wave patterns: {e}")
            return []
    
    def _find_impulse_patterns(self, swing_points: List[Dict]) -> List[Dict]:
        """Find 5-wave impulse patterns"""
        try:
            impulse_patterns = []
            
            # Need at least 6 points for a 5-wave pattern (start + 5 waves)
            if len(swing_points) < 6:
                return impulse_patterns
            
            # Look for potential 5-wave sequences
            for start_idx in range(len(swing_points) - 5):
                wave_points = swing_points[start_idx:start_idx + 6]
                
                # Check if this could be a 5-wave pattern
                if self._is_valid_impulse_sequence(wave_points):
                    pattern = {
                        'type': WaveType.IMPULSE,
                        'waves': self._label_impulse_waves(wave_points),
                        'start_point': wave_points[0],
                        'end_point': wave_points[-1],
                        'direction': 'bullish' if wave_points[-1]['price'] > wave_points[0]['price'] else 'bearish',
                        'confidence': self._calculate_pattern_confidence(wave_points, WaveType.IMPULSE)
                    }
                    impulse_patterns.append(pattern)
            
            return impulse_patterns
            
        except Exception as e:
            logger.error(f"Error finding impulse patterns: {e}")
            return []
    
    def _find_corrective_patterns(self, swing_points: List[Dict]) -> List[Dict]:
        """Find 3-wave corrective patterns (ABC)"""
        try:
            corrective_patterns = []
            
            # Need at least 4 points for a 3-wave pattern
            if len(swing_points) < 4:
                return corrective_patterns
            
            # Look for potential ABC sequences
            for start_idx in range(len(swing_points) - 3):
                wave_points = swing_points[start_idx:start_idx + 4]
                
                # Check if this could be an ABC pattern
                if self._is_valid_corrective_sequence(wave_points):
                    pattern = {
                        'type': WaveType.CORRECTIVE,
                        'waves': self._label_corrective_waves(wave_points),
                        'start_point': wave_points[0],
                        'end_point': wave_points[-1],
                        'direction': 'bullish' if wave_points[-1]['price'] > wave_points[0]['price'] else 'bearish',
                        'confidence': self._calculate_pattern_confidence(wave_points, WaveType.CORRECTIVE)
                    }
                    corrective_patterns.append(pattern)
            
            return corrective_patterns
            
        except Exception as e:
            logger.error(f"Error finding corrective patterns: {e}")
            return []
    
    def _is_valid_impulse_sequence(self, wave_points: List[Dict]) -> bool:
        """Check if swing points form a valid 5-wave impulse"""
        try:
            if len(wave_points) != 6:
                return False
            
            # Basic Elliott Wave rules for impulse:
            # 1. Wave 2 cannot retrace more than 100% of wave 1
            # 2. Wave 3 cannot be the shortest wave
            # 3. Wave 4 cannot overlap with wave 1 (except in leading diagonal)
            
            prices = [point['price'] for point in wave_points]
            
            # Calculate wave lengths
            wave1 = abs(prices[1] - prices[0])
            wave2 = abs(prices[2] - prices[1])
            wave3 = abs(prices[3] - prices[2])
            wave4 = abs(prices[4] - prices[3])
            wave5 = abs(prices[5] - prices[4])
            
            # Rule 1: Wave 2 retracement
            if wave2 >= wave1:
                return False
            
            # Rule 2: Wave 3 is not the shortest
            if wave3 < wave1 and wave3 < wave5:
                return False
            
            # Rule 3: Wave 4 doesn't overlap with wave 1 (simplified check)
            if wave_points[0]['type'] == 'low':  # Bullish impulse
                if prices[4] <= prices[1]:  # Wave 4 low overlaps wave 1 high
                    return False
            else:  # Bearish impulse
                if prices[4] >= prices[1]:  # Wave 4 high overlaps wave 1 low
                    return False
            
            return True
            
        except:
            return False
    
    def _is_valid_corrective_sequence(self, wave_points: List[Dict]) -> bool:
        """Check if swing points form a valid ABC corrective pattern"""
        try:
            if len(wave_points) != 4:
                return False
            
            # Basic validation for ABC pattern
            # Wave C should be roughly equal to wave A (common relationship)
            prices = [point['price'] for point in wave_points]
            
            wave_a = abs(prices[1] - prices[0])
            wave_c = abs(prices[3] - prices[2])
            
            # Allow for some variation in wave relationships
            ratio = wave_c / wave_a if wave_a > 0 else 0
            
            # Common Fibonacci relationships for wave C
            valid_ratios = [0.618, 1.0, 1.618]
            
            for valid_ratio in valid_ratios:
                if abs(ratio - valid_ratio) / valid_ratio < self.fib_tolerance * 2:
                    return True
            
            return False
            
        except:
            return False
    
    def _label_impulse_waves(self, wave_points: List[Dict]) -> List[Dict]:
        """Label waves in an impulse pattern"""
        try:
            labeled_waves = []
            labels = [WaveLabel.WAVE_1, WaveLabel.WAVE_2, WaveLabel.WAVE_3, 
                     WaveLabel.WAVE_4, WaveLabel.WAVE_5]
            
            for i in range(5):
                wave = {
                    'label': labels[i],
                    'start_point': wave_points[i],
                    'end_point': wave_points[i + 1],
                    'length': abs(wave_points[i + 1]['price'] - wave_points[i]['price']),
                    'direction': 'up' if wave_points[i + 1]['price'] > wave_points[i]['price'] else 'down'
                }
                labeled_waves.append(wave)
            
            return labeled_waves
            
        except:
            return []
    
    def _label_corrective_waves(self, wave_points: List[Dict]) -> List[Dict]:
        """Label waves in a corrective pattern"""
        try:
            labeled_waves = []
            labels = [WaveLabel.WAVE_A, WaveLabel.WAVE_B, WaveLabel.WAVE_C]
            
            for i in range(3):
                wave = {
                    'label': labels[i],
                    'start_point': wave_points[i],
                    'end_point': wave_points[i + 1],
                    'length': abs(wave_points[i + 1]['price'] - wave_points[i]['price']),
                    'direction': 'up' if wave_points[i + 1]['price'] > wave_points[i]['price'] else 'down'
                }
                labeled_waves.append(wave)
            
            return labeled_waves
            
        except:
            return []
    
    def _calculate_pattern_confidence(self, wave_points: List[Dict], wave_type: WaveType) -> float:
        """Calculate confidence score for a wave pattern"""
        try:
            confidence = 50.0  # Base confidence
            
            if wave_type == WaveType.IMPULSE:
                # Check Fibonacci relationships for impulse waves
                prices = [point['price'] for point in wave_points]
                
                # Wave 3 extension (common: 1.618 of wave 1)
                wave1 = abs(prices[1] - prices[0])
                wave3 = abs(prices[3] - prices[2])
                
                if wave1 > 0:
                    ratio_3_to_1 = wave3 / wave1
                    if abs(ratio_3_to_1 - 1.618) / 1.618 < self.fib_tolerance:
                        confidence += 15
                    elif abs(ratio_3_to_1 - 2.618) / 2.618 < self.fib_tolerance:
                        confidence += 10
                
                # Wave 5 relationship to wave 1
                wave5 = abs(prices[5] - prices[4])
                if wave1 > 0:
                    ratio_5_to_1 = wave5 / wave1
                    if abs(ratio_5_to_1 - 1.0) < self.fib_tolerance:
                        confidence += 10
                    elif abs(ratio_5_to_1 - 0.618) / 0.618 < self.fib_tolerance:
                        confidence += 8
            
            elif wave_type == WaveType.CORRECTIVE:
                # Check ABC relationships
                prices = [point['price'] for point in wave_points]
                wave_a = abs(prices[1] - prices[0])
                wave_c = abs(prices[3] - prices[2])
                
                if wave_a > 0:
                    ratio_c_to_a = wave_c / wave_a
                    if abs(ratio_c_to_a - 1.0) < self.fib_tolerance:
                        confidence += 15
                    elif abs(ratio_c_to_a - 0.618) / 0.618 < self.fib_tolerance:
                        confidence += 12
                    elif abs(ratio_c_to_a - 1.618) / 1.618 < self.fib_tolerance:
                        confidence += 10
            
            return min(95.0, confidence)
            
        except:
            return 50.0
    
    def _validate_wave_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """Validate and filter wave patterns"""
        try:
            validated = []
            
            for pattern in patterns:
                # Only keep patterns with reasonable confidence
                if pattern['confidence'] >= 60:
                    validated.append(pattern)
            
            # Sort by confidence
            validated.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Return top patterns
            return validated[:5]
            
        except:
            return patterns
    
    def _analyze_fibonacci_relationships(self, patterns: List[Dict]) -> Dict:
        """Analyze Fibonacci relationships in wave patterns"""
        try:
            fib_analysis = {
                'retracements': [],
                'extensions': [],
                'projections': []
            }
            
            for pattern in patterns:
                if pattern['type'] == WaveType.IMPULSE:
                    waves = pattern['waves']
                    
                    # Analyze retracements (waves 2 and 4)
                    if len(waves) >= 2:
                        wave1_length = waves[0]['length']
                        wave2_length = waves[1]['length']
                        
                        if wave1_length > 0:
                            retracement_ratio = wave2_length / wave1_length
                            fib_analysis['retracements'].append({
                                'wave': 'Wave 2',
                                'ratio': retracement_ratio,
                                'fib_level': self._find_closest_fib_level(retracement_ratio)
                            })
                    
                    if len(waves) >= 4:
                        wave3_length = waves[2]['length']
                        wave4_length = waves[3]['length']
                        
                        if wave3_length > 0:
                            retracement_ratio = wave4_length / wave3_length
                            fib_analysis['retracements'].append({
                                'wave': 'Wave 4',
                                'ratio': retracement_ratio,
                                'fib_level': self._find_closest_fib_level(retracement_ratio)
                            })
                    
                    # Analyze extensions (waves 3 and 5)
                    if len(waves) >= 3:
                        wave1_length = waves[0]['length']
                        wave3_length = waves[2]['length']
                        
                        if wave1_length > 0:
                            extension_ratio = wave3_length / wave1_length
                            fib_analysis['extensions'].append({
                                'wave': 'Wave 3',
                                'ratio': extension_ratio,
                                'fib_level': self._find_closest_fib_level(extension_ratio)
                            })
            
            return fib_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing Fibonacci relationships: {e}")
            return {'retracements': [], 'extensions': [], 'projections': []}
    
    def _find_closest_fib_level(self, ratio: float) -> float:
        """Find the closest Fibonacci level to a given ratio"""
        try:
            common_fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.618]
            
            closest_level = min(common_fib_levels, key=lambda x: abs(x - ratio))
            return closest_level
            
        except:
            return 0.618  # Default to golden ratio
    
    def _generate_wave_projections(self, patterns: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """Generate wave projections for potential future moves"""
        try:
            projections = []
            current_price = df['close'].iloc[-1]
            
            for pattern in patterns:
                if pattern['confidence'] < 70:
                    continue
                
                waves = pattern['waves']
                
                if pattern['type'] == WaveType.IMPULSE and len(waves) >= 4:
                    # Project wave 5 if we're in wave 4
                    last_wave = waves[-1]
                    
                    if last_wave['label'] == WaveLabel.WAVE_4:
                        # Project wave 5 based on wave 1 relationship
                        wave1_length = waves[0]['length']
                        wave4_end = last_wave['end_point']['price']
                        
                        # Common wave 5 projections
                        projections.append({
                            'type': 'wave_5_equal_to_1',
                            'target': wave4_end + (wave1_length if pattern['direction'] == 'bullish' else -wave1_length),
                            'probability': 0.6,
                            'description': 'Wave 5 = Wave 1'
                        })
                        
                        projections.append({
                            'type': 'wave_5_618_of_1',
                            'target': wave4_end + (wave1_length * 0.618 if pattern['direction'] == 'bullish' else -wave1_length * 0.618),
                            'probability': 0.4,
                            'description': 'Wave 5 = 0.618 * Wave 1'
                        })
                
                elif pattern['type'] == WaveType.CORRECTIVE and len(waves) >= 2:
                    # Project wave C if we're in wave B
                    last_wave = waves[-1]
                    
                    if last_wave['label'] == WaveLabel.WAVE_B:
                        wave_a_length = waves[0]['length']
                        wave_b_end = last_wave['end_point']['price']
                        
                        # Common wave C projections
                        projections.append({
                            'type': 'wave_c_equal_to_a',
                            'target': wave_b_end + (wave_a_length if waves[0]['direction'] == 'down' else -wave_a_length),
                            'probability': 0.5,
                            'description': 'Wave C = Wave A'
                        })
                        
                        projections.append({
                            'type': 'wave_c_618_of_a',
                            'target': wave_b_end + (wave_a_length * 1.618 if waves[0]['direction'] == 'down' else -wave_a_length * 1.618),
                            'probability': 0.3,
                            'description': 'Wave C = 1.618 * Wave A'
                        })
            
            return projections
            
        except Exception as e:
            logger.error(f"Error generating wave projections: {e}")
            return []
    
    def _generate_wave_signals(self, patterns: List[Dict], projections: List[Dict],
                              df: pd.DataFrame, symbol: str, timeframe: str) -> List[Dict]:
        """Generate trading signals based on Elliott Wave analysis"""
        signals = []
        current_price = df['close'].iloc[-1]
        
        try:
            # Signals based on wave completion
            for pattern in patterns:
                if pattern['confidence'] < 65:
                    continue
                
                waves = pattern['waves']
                
                if pattern['type'] == WaveType.IMPULSE:
                    # Check if we're at the end of wave 5 (reversal signal)
                    if len(waves) >= 5 and waves[-1]['label'] == WaveLabel.WAVE_5:
                        # Price near wave 5 target suggests reversal
                        wave5_target = waves[-1]['end_point']['price']
                        distance_to_target = abs(current_price - wave5_target) / current_price
                        
                        if distance_to_target < 0.02:  # Within 2%
                            direction = SignalDirection.SHORT if pattern['direction'] == 'bullish' else SignalDirection.LONG
                            signals.append({
                                'type': 'elliott_wave_5_completion',
                                'direction': direction,
                                'confidence': min(80, pattern['confidence']),
                                'entry': current_price,
                                'reason': f'Wave 5 completion in {pattern["direction"]} impulse'
                            })
                    
                    # Check if we're in wave 4 (continuation signal)
                    elif len(waves) >= 4 and waves[-1]['label'] == WaveLabel.WAVE_4:
                        # Wave 4 completion suggests wave 5 continuation
                        direction = SignalDirection.LONG if pattern['direction'] == 'bullish' else SignalDirection.SHORT
                        signals.append({
                            'type': 'elliott_wave_4_completion',
                            'direction': direction,
                            'confidence': min(75, pattern['confidence']),
                            'entry': current_price,
                            'reason': f'Wave 4 completion, expecting wave 5 in {pattern["direction"]} direction'
                        })
                
                elif pattern['type'] == WaveType.CORRECTIVE:
                    # Check if we're at the end of wave C (reversal signal)
                    if len(waves) >= 3 and waves[-1]['label'] == WaveLabel.WAVE_C:
                        # Wave C completion suggests trend reversal
                        direction = SignalDirection.LONG if pattern['direction'] == 'bearish' else SignalDirection.SHORT
                        signals.append({
                            'type': 'elliott_abc_completion',
                            'direction': direction,
                            'confidence': min(70, pattern['confidence']),
                            'entry': current_price,
                            'reason': f'ABC correction completion, expecting reversal'
                        })
            
            # Signals based on projections
            for projection in projections:
                distance_to_target = abs(current_price - projection['target']) / current_price
                
                if distance_to_target < 0.01:  # Within 1% of projection target
                    # Determine signal direction based on projection type
                    if 'wave_5' in projection['type']:
                        # Near wave 5 target - expect reversal
                        signals.append({
                            'type': 'elliott_projection_target',
                            'direction': SignalDirection.SHORT,  # Assuming bullish wave 5
                            'confidence': int(projection['probability'] * 80),
                            'entry': current_price,
                            'reason': f'Price near {projection["description"]} target'
                        })
                    elif 'wave_c' in projection['type']:
                        # Near wave C target - expect reversal
                        signals.append({
                            'type': 'elliott_projection_target',
                            'direction': SignalDirection.LONG,  # Assuming bearish wave C
                            'confidence': int(projection['probability'] * 75),
                            'entry': current_price,
                            'reason': f'Price near {projection["description"]} target'
                        })
            
        except Exception as e:
            logger.error(f"Error generating Elliott Wave signals: {e}")
        
        return signals
    
    def _get_current_wave_count(self, patterns: List[Dict]) -> Dict:
        """Determine the most likely current wave count"""
        try:
            if not patterns:
                return {'primary_count': 'Unknown', 'alternate_count': 'Unknown'}
            
            # Get the highest confidence pattern
            primary_pattern = patterns[0]
            
            current_count = {
                'primary_count': 'Unknown',
                'alternate_count': 'Unknown',
                'confidence': primary_pattern['confidence']
            }
            
            if primary_pattern['type'] == WaveType.IMPULSE:
                waves = primary_pattern['waves']
                if waves:
                    last_wave = waves[-1]['label'].value
                    current_count['primary_count'] = f"Wave {last_wave} of impulse"
            
            elif primary_pattern['type'] == WaveType.CORRECTIVE:
                waves = primary_pattern['waves']
                if waves:
                    last_wave = waves[-1]['label'].value
                    current_count['primary_count'] = f"Wave {last_wave} of correction"
            
            # Add alternate count if available
            if len(patterns) > 1:
                alternate_pattern = patterns[1]
                if alternate_pattern['type'] == WaveType.IMPULSE:
                    waves = alternate_pattern['waves']
                    if waves:
                        last_wave = waves[-1]['label'].value
                        current_count['alternate_count'] = f"Wave {last_wave} of impulse"
                elif alternate_pattern['type'] == WaveType.CORRECTIVE:
                    waves = alternate_pattern['waves']
                    if waves:
                        last_wave = waves[-1]['label'].value
                        current_count['alternate_count'] = f"Wave {last_wave} of correction"
            
            return current_count
            
        except:
            return {'primary_count': 'Unknown', 'alternate_count': 'Unknown'}
    
    def _calculate_wave_confidence(self, patterns: List[Dict], fib_analysis: Dict,
                                  signals: List[Dict]) -> float:
        """Calculate overall confidence for Elliott Wave analysis"""
        if not patterns:
            return 0.0
        
        try:
            # Base confidence from best pattern
            base_confidence = patterns[0]['confidence'] if patterns else 0
            
            # Bonus for Fibonacci confirmations
            fib_confirmations = 0
            for retracement in fib_analysis.get('retracements', []):
                if abs(retracement['ratio'] - retracement['fib_level']) / retracement['fib_level'] < self.fib_tolerance:
                    fib_confirmations += 1
            
            for extension in fib_analysis.get('extensions', []):
                if abs(extension['ratio'] - extension['fib_level']) / extension['fib_level'] < self.fib_tolerance:
                    fib_confirmations += 1
            
            fib_bonus = min(20, fib_confirmations * 5)
            
            # Signal quality bonus
            signal_bonus = 0
            if signals:
                avg_signal_confidence = sum(s['confidence'] for s in signals) / len(signals)
                signal_bonus = min(15, avg_signal_confidence * 0.2)
            
            total_confidence = base_confidence + fib_bonus + signal_bonus
            
            return min(95.0, max(0.0, total_confidence))
            
        except:
            return 0.0