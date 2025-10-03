"""
Harmonic Pattern Detection Implementation
XABCD patterns: Gartley, Bat, Butterfly, Crab, Cypher, Shark
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

class HarmonicPatternType(Enum):
    GARTLEY = "Gartley"
    BAT = "Bat"
    BUTTERFLY = "Butterfly"
    CRAB = "Crab"
    DEEP_CRAB = "Deep Crab"
    CYPHER = "Cypher"
    SHARK = "Shark"

class HarmonicAnalyzer:
    """Harmonic pattern detection and analysis"""
    
    def __init__(self):
        self.config = settings.analysis
        self.tolerance = self.config.harmonic_tolerance
        
        # Define harmonic pattern ratios
        self.pattern_ratios = {
            HarmonicPatternType.GARTLEY: {
                'XA_AB': (0.618, 0.618),  # AB = 0.618 of XA
                'AB_BC': (0.382, 0.886),  # BC = 0.382 to 0.886 of AB
                'XA_CD': (0.786, 0.786),  # CD = 0.786 of XA
                'BC_CD': (1.13, 1.618),   # CD = 1.13 to 1.618 of BC
                'XA_AD': (0.786, 0.786)   # AD = 0.786 of XA (PRZ)
            },
            HarmonicPatternType.BAT: {
                'XA_AB': (0.382, 0.5),    # AB = 0.382 to 0.5 of XA
                'AB_BC': (0.382, 0.886),  # BC = 0.382 to 0.886 of AB
                'XA_CD': (1.618, 2.618),  # CD = 1.618 to 2.618 of XA
                'BC_CD': (1.618, 2.618),  # CD = 1.618 to 2.618 of BC
                'XA_AD': (0.886, 0.886)   # AD = 0.886 of XA (PRZ)
            },
            HarmonicPatternType.BUTTERFLY: {
                'XA_AB': (0.786, 0.786),  # AB = 0.786 of XA
                'AB_BC': (0.382, 0.886),  # BC = 0.382 to 0.886 of AB
                'XA_CD': (1.618, 2.24),   # CD = 1.618 to 2.24 of XA
                'BC_CD': (1.618, 2.618),  # CD = 1.618 to 2.618 of BC
                'XA_AD': (1.27, 1.618)    # AD = 1.27 to 1.618 of XA (PRZ)
            },
            HarmonicPatternType.CRAB: {
                'XA_AB': (0.382, 0.618),  # AB = 0.382 to 0.618 of XA
                'AB_BC': (0.382, 0.886),  # BC = 0.382 to 0.886 of AB
                'XA_CD': (2.24, 3.618),   # CD = 2.24 to 3.618 of XA
                'BC_CD': (2.618, 3.618),  # CD = 2.618 to 3.618 of BC
                'XA_AD': (1.618, 1.618)   # AD = 1.618 of XA (PRZ)
            },
            HarmonicPatternType.DEEP_CRAB: {
                'XA_AB': (0.886, 0.886),  # AB = 0.886 of XA
                'AB_BC': (0.382, 0.886),  # BC = 0.382 to 0.886 of AB
                'XA_CD': (2.24, 3.618),   # CD = 2.24 to 3.618 of XA
                'BC_CD': (2.618, 3.618),  # CD = 2.618 to 3.618 of BC
                'XA_AD': (1.618, 1.618)   # AD = 1.618 of XA (PRZ)
            },
            HarmonicPatternType.CYPHER: {
                'XA_AB': (0.382, 0.618),  # AB = 0.382 to 0.618 of XA
                'AB_BC': (1.13, 1.414),   # BC = 1.13 to 1.414 of AB
                'XA_CD': (0.786, 0.786),  # CD = 0.786 of XA
                'BC_CD': (0.786, 0.786),  # CD = 0.786 of BC
                'XA_AD': (0.786, 0.786)   # AD = 0.786 of XA (PRZ)
            },
            HarmonicPatternType.SHARK: {
                'XA_AB': (0.382, 0.618),  # AB = 0.382 to 0.618 of XA
                'AB_BC': (1.13, 1.618),   # BC = 1.13 to 1.618 of AB
                'XA_CD': (0.886, 1.13),   # CD = 0.886 to 1.13 of XA
                'BC_CD': (1.618, 2.24),   # CD = 1.618 to 2.24 of BC
                'XA_AD': (0.886, 1.13)    # AD = 0.886 to 1.13 of XA (PRZ)
            }
        }
    
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> AnalysisResult:
        """Perform harmonic pattern analysis"""
        try:
            if len(df) < 50:  # Need enough data for pattern detection
                logger.warning(f"Insufficient data for harmonic analysis: {len(df)} bars")
                return AnalysisResult(
                    method=AnalysisMethod.HARMONIC_PATTERNS,
                    symbol=symbol,
                    timeframe=timeframe,
                    confidence=0.0
                )
            
            # Find swing points for pattern detection
            swing_points = self._find_swing_points(df)
            
            if len(swing_points) < 5:
                return AnalysisResult(
                    method=AnalysisMethod.HARMONIC_PATTERNS,
                    symbol=symbol,
                    timeframe=timeframe,
                    confidence=0.0,
                    data={'swing_points': swing_points}
                )
            
            # Detect harmonic patterns
            detected_patterns = self._detect_harmonic_patterns(swing_points, df)
            
            # Validate patterns
            validated_patterns = self._validate_patterns(detected_patterns)
            
            # Calculate Potential Reversal Zones (PRZ)
            prz_zones = self._calculate_prz_zones(validated_patterns)
            
            # Generate signals
            signals = self._generate_harmonic_signals(
                validated_patterns, prz_zones, df, symbol, timeframe
            )
            
            # Calculate confidence
            confidence = self._calculate_harmonic_confidence(
                validated_patterns, prz_zones, signals
            )
            
            harmonic_data = {
                'swing_points': swing_points,
                'detected_patterns': validated_patterns,
                'prz_zones': prz_zones,
                'pattern_completion_levels': self._get_completion_levels(validated_patterns)
            }
            
            return AnalysisResult(
                method=AnalysisMethod.HARMONIC_PATTERNS,
                symbol=symbol,
                timeframe=timeframe,
                confidence=confidence,
                data=harmonic_data,
                potential_signals=signals
            )
            
        except Exception as e:
            logger.error(f"Error in harmonic pattern analysis: {e}")
            return AnalysisResult(
                method=AnalysisMethod.HARMONIC_PATTERNS,
                symbol=symbol,
                timeframe=timeframe,
                confidence=0.0
            )
    
    def _find_swing_points(self, df: pd.DataFrame, lookback: int = 5) -> List[Dict]:
        """Find swing points for harmonic pattern detection"""
        try:
            swing_points = []
            
            highs = df['high'].values
            lows = df['low'].values
            
            # Find swing highs
            for i in range(lookback, len(df) - lookback):
                is_swing_high = True
                for j in range(i - lookback, i + lookback + 1):
                    if j != i and highs[j] >= highs[i]:
                        is_swing_high = False
                        break
                
                if is_swing_high:
                    swing_points.append({
                        'index': i,
                        'price': highs[i],
                        'type': 'high',
                        'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i
                    })
            
            # Find swing lows
            for i in range(lookback, len(df) - lookback):
                is_swing_low = True
                for j in range(i - lookback, i + lookback + 1):
                    if j != i and lows[j] <= lows[i]:
                        is_swing_low = False
                        break
                
                if is_swing_low:
                    swing_points.append({
                        'index': i,
                        'price': lows[i],
                        'type': 'low',
                        'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i
                    })
            
            # Sort by index
            swing_points.sort(key=lambda x: x['index'])
            
            return swing_points
            
        except Exception as e:
            logger.error(f"Error finding swing points: {e}")
            return []
    
    def _detect_harmonic_patterns(self, swing_points: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """Detect all types of harmonic patterns"""
        try:
            detected_patterns = []
            
            # Need at least 5 points for XABCD pattern
            if len(swing_points) < 5:
                return detected_patterns
            
            # Look for potential XABCD sequences
            for i in range(len(swing_points) - 4):
                xabcd_points = swing_points[i:i+5]
                
                # Check if points alternate between high and low
                if self._is_valid_xabcd_sequence(xabcd_points):
                    # Test against all harmonic pattern types
                    for pattern_type in HarmonicPatternType:
                        pattern_match = self._test_pattern_ratios(xabcd_points, pattern_type)
                        
                        if pattern_match['is_valid']:
                            detected_patterns.append({
                                'type': pattern_type,
                                'points': {
                                    'X': xabcd_points[0],
                                    'A': xabcd_points[1],
                                    'B': xabcd_points[2],
                                    'C': xabcd_points[3],
                                    'D': xabcd_points[4]
                                },
                                'ratios': pattern_match['ratios'],
                                'accuracy': pattern_match['accuracy'],
                                'direction': self._determine_pattern_direction(xabcd_points),
                                'completion_time': xabcd_points[4]['timestamp'],
                                'is_bullish': xabcd_points[0]['price'] > xabcd_points[4]['price']
                            })
            
            return detected_patterns
            
        except Exception as e:
            logger.error(f"Error detecting harmonic patterns: {e}")
            return []
    
    def _is_valid_xabcd_sequence(self, points: List[Dict]) -> bool:
        """Check if 5 points form a valid XABCD sequence"""
        try:
            if len(points) != 5:
                return False
            
            # Points should alternate between high and low
            types = [point['type'] for point in points]
            
            # Valid sequences: high-low-high-low-high or low-high-low-high-low
            valid_sequences = [
                ['high', 'low', 'high', 'low', 'high'],
                ['low', 'high', 'low', 'high', 'low']
            ]
            
            return types in valid_sequences
            
        except:
            return False
    
    def _test_pattern_ratios(self, points: List[Dict], pattern_type: HarmonicPatternType) -> Dict:
        """Test if XABCD points match a specific harmonic pattern"""
        try:
            if pattern_type not in self.pattern_ratios:
                return {'is_valid': False, 'ratios': {}, 'accuracy': 0.0}
            
            expected_ratios = self.pattern_ratios[pattern_type]
            
            # Extract prices
            X = points[0]['price']
            A = points[1]['price']
            B = points[2]['price']
            C = points[3]['price']
            D = points[4]['price']
            
            # Calculate actual ratios
            XA = abs(A - X)
            AB = abs(B - A)
            BC = abs(C - B)
            CD = abs(D - C)
            AD = abs(D - A)
            
            actual_ratios = {}
            ratio_accuracies = []
            
            # Test each ratio requirement
            if XA > 0:
                actual_ratios['XA_AB'] = AB / XA
                expected_min, expected_max = expected_ratios['XA_AB']
                accuracy = self._calculate_ratio_accuracy(actual_ratios['XA_AB'], expected_min, expected_max)
                ratio_accuracies.append(accuracy)
            
            if AB > 0:
                actual_ratios['AB_BC'] = BC / AB
                expected_min, expected_max = expected_ratios['AB_BC']
                accuracy = self._calculate_ratio_accuracy(actual_ratios['AB_BC'], expected_min, expected_max)
                ratio_accuracies.append(accuracy)
            
            if XA > 0:
                actual_ratios['XA_CD'] = CD / XA
                expected_min, expected_max = expected_ratios['XA_CD']
                accuracy = self._calculate_ratio_accuracy(actual_ratios['XA_CD'], expected_min, expected_max)
                ratio_accuracies.append(accuracy)
            
            if BC > 0:
                actual_ratios['BC_CD'] = CD / BC
                expected_min, expected_max = expected_ratios['BC_CD']
                accuracy = self._calculate_ratio_accuracy(actual_ratios['BC_CD'], expected_min, expected_max)
                ratio_accuracies.append(accuracy)
            
            if XA > 0:
                actual_ratios['XA_AD'] = AD / XA
                expected_min, expected_max = expected_ratios['XA_AD']
                accuracy = self._calculate_ratio_accuracy(actual_ratios['XA_AD'], expected_min, expected_max)
                ratio_accuracies.append(accuracy)
            
            # Pattern is valid if all ratios meet minimum accuracy threshold
            overall_accuracy = np.mean(ratio_accuracies) if ratio_accuracies else 0.0
            is_valid = overall_accuracy >= 0.7  # 70% accuracy threshold
            
            return {
                'is_valid': is_valid,
                'ratios': actual_ratios,
                'accuracy': overall_accuracy
            }
            
        except Exception as e:
            logger.error(f"Error testing pattern ratios: {e}")
            return {'is_valid': False, 'ratios': {}, 'accuracy': 0.0}
    
    def _calculate_ratio_accuracy(self, actual: float, expected_min: float, expected_max: float) -> float:
        """Calculate how accurately an actual ratio matches the expected range"""
        try:
            if expected_min == expected_max:
                # Single target ratio
                expected = expected_min
                deviation = abs(actual - expected) / expected
                accuracy = max(0.0, 1.0 - (deviation / self.tolerance))
            else:
                # Range of acceptable ratios
                if expected_min <= actual <= expected_max:
                    accuracy = 1.0
                else:
                    # Calculate distance from range
                    if actual < expected_min:
                        deviation = (expected_min - actual) / expected_min
                    else:
                        deviation = (actual - expected_max) / expected_max
                    
                    accuracy = max(0.0, 1.0 - (deviation / self.tolerance))
            
            return accuracy
            
        except:
            return 0.0
    
    def _determine_pattern_direction(self, points: List[Dict]) -> str:
        """Determine if pattern is bullish or bearish"""
        try:
            # Compare X and D points
            X_price = points[0]['price']
            D_price = points[4]['price']
            
            if points[0]['type'] == 'high' and points[4]['type'] == 'low':
                return 'bearish'  # High to Low pattern
            elif points[0]['type'] == 'low' and points[4]['type'] == 'high':
                return 'bullish'  # Low to High pattern
            else:
                return 'neutral'
                
        except:
            return 'neutral'
    
    def _validate_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """Validate and filter detected patterns"""
        try:
            validated = []
            
            for pattern in patterns:
                # Only keep patterns with high accuracy
                if pattern['accuracy'] >= 0.75:
                    validated.append(pattern)
            
            # Sort by accuracy
            validated.sort(key=lambda x: x['accuracy'], reverse=True)
            
            # Remove overlapping patterns (keep the most accurate)
            final_patterns = []
            used_points = set()
            
            for pattern in validated:
                points = pattern['points']
                point_indices = [p['index'] for p in points.values()]
                
                # Check if any points are already used
                if not any(idx in used_points for idx in point_indices):
                    final_patterns.append(pattern)
                    used_points.update(point_indices)
            
            return final_patterns[:5]  # Return top 5 patterns
            
        except:
            return patterns
    
    def _calculate_prz_zones(self, patterns: List[Dict]) -> List[Dict]:
        """Calculate Potential Reversal Zones for patterns"""
        try:
            prz_zones = []
            
            for pattern in patterns:
                points = pattern['points']
                pattern_type = pattern['type']
                
                # Get expected AD ratio for PRZ calculation
                if pattern_type in self.pattern_ratios:
                    expected_ad_ratio = self.pattern_ratios[pattern_type]['XA_AD']
                    
                    X_price = points['X']['price']
                    A_price = points['A']['price']
                    D_price = points['D']['price']
                    
                    XA_length = abs(A_price - X_price)
                    
                    # Calculate PRZ based on expected AD ratio
                    if isinstance(expected_ad_ratio, tuple):
                        min_ratio, max_ratio = expected_ad_ratio
                    else:
                        min_ratio = max_ratio = expected_ad_ratio
                    
                    if pattern['direction'] == 'bullish':
                        prz_min = A_price - (XA_length * max_ratio)
                        prz_max = A_price - (XA_length * min_ratio)
                    else:
                        prz_min = A_price + (XA_length * min_ratio)
                        prz_max = A_price + (XA_length * max_ratio)
                    
                    prz_zones.append({
                        'pattern_id': id(pattern),
                        'pattern_type': pattern_type,
                        'direction': pattern['direction'],
                        'prz_min': min(prz_min, prz_max),
                        'prz_max': max(prz_min, prz_max),
                        'prz_center': (prz_min + prz_max) / 2,
                        'D_point': D_price,
                        'strength': pattern['accuracy']
                    })
            
            return prz_zones
            
        except Exception as e:
            logger.error(f"Error calculating PRZ zones: {e}")
            return []
    
    def _generate_harmonic_signals(self, patterns: List[Dict], prz_zones: List[Dict],
                                  df: pd.DataFrame, symbol: str, timeframe: str) -> List[Dict]:
        """Generate trading signals based on harmonic patterns"""
        signals = []
        current_price = df['close'].iloc[-1]
        
        try:
            # Signals based on PRZ zone proximity
            for prz in prz_zones:
                distance_to_prz = min(
                    abs(current_price - prz['prz_min']),
                    abs(current_price - prz['prz_max'])
                ) / current_price
                
                # Signal when price is near PRZ
                if distance_to_prz < 0.01:  # Within 1% of PRZ
                    direction = SignalDirection.LONG if prz['direction'] == 'bullish' else SignalDirection.SHORT
                    confidence = min(85, int(prz['strength'] * 100))
                    
                    signals.append({
                        'type': 'harmonic_prz_entry',
                        'direction': direction,
                        'confidence': confidence,
                        'entry': current_price,
                        'reason': f'{prz["pattern_type"].value} pattern PRZ zone entry',
                        'pattern_type': prz['pattern_type'].value,
                        'prz_zone': [prz['prz_min'], prz['prz_max']]
                    })
            
            # Signals based on pattern completion
            for pattern in patterns:
                D_point = pattern['points']['D']
                
                # Check if pattern just completed (D point is recent)
                bars_since_completion = len(df) - 1 - D_point['index']
                
                if bars_since_completion <= 5:  # Pattern completed within last 5 bars
                    direction = SignalDirection.LONG if pattern['direction'] == 'bullish' else SignalDirection.SHORT
                    confidence = min(80, int(pattern['accuracy'] * 100))
                    
                    signals.append({
                        'type': 'harmonic_pattern_completion',
                        'direction': direction,
                        'confidence': confidence,
                        'entry': current_price,
                        'reason': f'{pattern["type"].value} pattern completed at D point',
                        'pattern_type': pattern['type'].value,
                        'completion_accuracy': pattern['accuracy']
                    })
            
            # Confluence signals (multiple patterns in same area)
            if len(prz_zones) > 1:
                # Check for PRZ confluence
                for i, prz1 in enumerate(prz_zones[:-1]):
                    for prz2 in prz_zones[i+1:]:
                        # Check if PRZ zones overlap
                        overlap = (min(prz1['prz_max'], prz2['prz_max']) - 
                                 max(prz1['prz_min'], prz2['prz_min']))
                        
                        if overlap > 0:
                            # PRZ confluence found
                            confluence_center = (
                                max(prz1['prz_min'], prz2['prz_min']) + 
                                min(prz1['prz_max'], prz2['prz_max'])
                            ) / 2
                            
                            distance_to_confluence = abs(current_price - confluence_center) / current_price
                            
                            if distance_to_confluence < 0.015:  # Within 1.5%
                                # Determine direction based on stronger pattern
                                stronger_prz = prz1 if prz1['strength'] > prz2['strength'] else prz2
                                direction = SignalDirection.LONG if stronger_prz['direction'] == 'bullish' else SignalDirection.SHORT
                                
                                signals.append({
                                    'type': 'harmonic_confluence',
                                    'direction': direction,
                                    'confidence': 90,
                                    'entry': current_price,
                                    'reason': f'PRZ confluence: {prz1["pattern_type"].value} + {prz2["pattern_type"].value}',
                                    'confluence_patterns': [prz1['pattern_type'].value, prz2['pattern_type'].value]
                                })
        
        except Exception as e:
            logger.error(f"Error generating harmonic signals: {e}")
        
        return signals
    
    def _get_completion_levels(self, patterns: List[Dict]) -> List[Dict]:
        """Get completion levels for active patterns"""
        try:
            completion_levels = []
            
            for pattern in patterns:
                points = pattern['points']
                pattern_type = pattern['type']
                
                # Calculate potential D completion levels based on C point
                C_price = points['C']['price']
                A_price = points['A']['price']
                B_price = points['B']['price']
                
                if pattern_type in self.pattern_ratios:
                    ratios = self.pattern_ratios[pattern_type]
                    
                    # Calculate D targets based on BC and XA relationships
                    BC_length = abs(C_price - B_price)
                    XA_length = abs(A_price - points['X']['price'])
                    
                    # D target based on BC ratio
                    bc_cd_min, bc_cd_max = ratios['BC_CD']
                    
                    if pattern['direction'] == 'bullish':
                        d_target_bc_min = C_price - (BC_length * bc_cd_max)
                        d_target_bc_max = C_price - (BC_length * bc_cd_min)
                    else:
                        d_target_bc_min = C_price + (BC_length * bc_cd_min)
                        d_target_bc_max = C_price + (BC_length * bc_cd_max)
                    
                    # D target based on XA ratio
                    xa_cd_min, xa_cd_max = ratios['XA_CD']
                    
                    if pattern['direction'] == 'bullish':
                        d_target_xa_min = A_price - (XA_length * xa_cd_max)
                        d_target_xa_max = A_price - (XA_length * xa_cd_min)
                    else:
                        d_target_xa_min = A_price + (XA_length * xa_cd_min)
                        d_target_xa_max = A_price + (XA_length * xa_cd_max)
                    
                    completion_levels.append({
                        'pattern_type': pattern_type.value,
                        'direction': pattern['direction'],
                        'd_target_bc_range': [d_target_bc_min, d_target_bc_max],
                        'd_target_xa_range': [d_target_xa_min, d_target_xa_max],
                        'optimal_d_level': (d_target_bc_min + d_target_bc_max + d_target_xa_min + d_target_xa_max) / 4
                    })
            
            return completion_levels
            
        except Exception as e:
            logger.error(f"Error calculating completion levels: {e}")
            return []
    
    def _calculate_harmonic_confidence(self, patterns: List[Dict], prz_zones: List[Dict],
                                     signals: List[Dict]) -> float:
        """Calculate overall confidence for harmonic pattern analysis"""
        if not patterns:
            return 0.0
        
        try:
            # Base confidence from pattern accuracy
            if patterns:
                avg_pattern_accuracy = sum(p['accuracy'] for p in patterns) / len(patterns)
                base_confidence = avg_pattern_accuracy * 80
            else:
                base_confidence = 0
            
            # Bonus for multiple patterns
            pattern_bonus = min(20, (len(patterns) - 1) * 5)
            
            # Bonus for PRZ confluence
            confluence_bonus = 0
            if len(prz_zones) > 1:
                confluence_bonus = 10
            
            # Signal quality bonus
            signal_bonus = 0
            if signals:
                avg_signal_confidence = sum(s['confidence'] for s in signals) / len(signals)
                signal_bonus = min(15, avg_signal_confidence * 0.15)
            
            total_confidence = base_confidence + pattern_bonus + confluence_bonus + signal_bonus
            
            return min(95.0, max(0.0, total_confidence))
            
        except:
            return 0.0