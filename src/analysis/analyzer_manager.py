"""
Analyzer Manager - coordinates all analysis methods
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

from src.analysis.technical_analysis import TechnicalAnalyzer
from src.analysis.smart_money_concepts import SmartMoneyAnalyzer
from src.analysis.elliott_wave import ElliottWaveAnalyzer
from src.analysis.harmonic_patterns import HarmonicAnalyzer
from src.models import AnalysisResult, AnalysisMethod, TimeFrame
from config import settings

logger = logging.getLogger(__name__)

class AnalyzerManager:
    """Manages and coordinates all analysis methods"""
    
    def __init__(self):
        # Initialize all analyzers
        self.technical_analyzer = TechnicalAnalyzer()
        self.smc_analyzer = SmartMoneyAnalyzer()
        self.elliott_analyzer = ElliottWaveAnalyzer()
        self.harmonic_analyzer = HarmonicAnalyzer()
        
        # Analysis method mapping
        self.analyzers = {
            AnalysisMethod.TECHNICAL_ANALYSIS: self.technical_analyzer,
            AnalysisMethod.SMART_MONEY_CONCEPTS: self.smc_analyzer,
            AnalysisMethod.ELLIOTT_WAVE: self.elliott_analyzer,
            AnalysisMethod.HARMONIC_PATTERNS: self.harmonic_analyzer
        }
        
        self.initialized = False
    
    async def initialize(self):
        """Initialize the analyzer manager"""
        try:
            logger.info("🔄 Initializing Analyzer Manager...")
            
            # Any initialization logic for analyzers can go here
            # For now, analyzers are stateless and don't need async initialization
            
            self.initialized = True
            logger.info("✅ Analyzer Manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Analyzer Manager initialization failed: {e}")
            raise
    
    async def analyze_symbol(self, 
                           symbol: str, 
                           exchange: str,
                           timeframe: str,
                           data: pd.DataFrame,
                           enabled_methods: Optional[List[AnalysisMethod]] = None) -> Dict[AnalysisMethod, AnalysisResult]:
        """
        Perform comprehensive analysis on a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            exchange: Exchange name (e.g., 'binance')
            timeframe: Timeframe (e.g., '1h')
            data: OHLCV DataFrame
            enabled_methods: List of analysis methods to run (None = all)
        
        Returns:
            Dictionary mapping analysis methods to their results
        """
        try:
            if not self.initialized:
                raise Exception("Analyzer Manager not initialized")
            
            if data.empty or len(data) < 20:
                logger.warning(f"Insufficient data for analysis: {symbol} {timeframe}")
                return {}
            
            # Use all methods if none specified
            if enabled_methods is None:
                enabled_methods = list(AnalysisMethod)
            
            # Run analyses in parallel
            analysis_tasks = []
            
            for method in enabled_methods:
                if method in self.analyzers:
                    analyzer = self.analyzers[method]
                    task = asyncio.create_task(
                        self._run_analysis_safe(analyzer, data, symbol, timeframe, method)
                    )
                    analysis_tasks.append((method, task))
            
            # Wait for all analyses to complete
            results = {}
            for method, task in analysis_tasks:
                try:
                    result = await task
                    results[method] = result
                except Exception as e:
                    logger.error(f"Error in {method.value} analysis for {symbol}: {e}")
                    # Create empty result for failed analysis
                    results[method] = AnalysisResult(
                        method=method,
                        symbol=symbol,
                        timeframe=timeframe,
                        confidence=0.0
                    )
            
            logger.info(f"✅ Completed analysis for {symbol} {timeframe} on {exchange}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return {}
    
    async def _run_analysis_safe(self, 
                               analyzer: Any, 
                               data: pd.DataFrame, 
                               symbol: str, 
                               timeframe: str,
                               method: AnalysisMethod) -> AnalysisResult:
        """Safely run an individual analysis method"""
        try:
            # Run analysis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                analyzer.analyze, 
                data, 
                symbol, 
                timeframe
            )
            return result
            
        except Exception as e:
            logger.error(f"Error in {method.value} analysis: {e}")
            return AnalysisResult(
                method=method,
                symbol=symbol,
                timeframe=timeframe,
                confidence=0.0
            )
    
    async def get_multi_timeframe_analysis(self,
                                         symbol: str,
                                         exchange: str,
                                         data_dict: Dict[str, pd.DataFrame],
                                         enabled_methods: Optional[List[AnalysisMethod]] = None) -> Dict[str, Dict[AnalysisMethod, AnalysisResult]]:
        """
        Perform analysis across multiple timeframes
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            data_dict: Dictionary mapping timeframes to DataFrames
            enabled_methods: List of analysis methods to run
        
        Returns:
            Dictionary mapping timeframes to analysis results
        """
        try:
            multi_tf_results = {}
            
            # Analyze each timeframe
            for timeframe, data in data_dict.items():
                if not data.empty:
                    results = await self.analyze_symbol(
                        symbol=symbol,
                        exchange=exchange,
                        timeframe=timeframe,
                        data=data,
                        enabled_methods=enabled_methods
                    )
                    multi_tf_results[timeframe] = results
            
            return multi_tf_results
            
        except Exception as e:
            logger.error(f"Error in multi-timeframe analysis: {e}")
            return {}
    
    def get_consensus_analysis(self, 
                             results: Dict[AnalysisMethod, AnalysisResult]) -> Dict[str, Any]:
        """
        Generate consensus analysis from multiple methods
        
        Args:
            results: Dictionary of analysis results
        
        Returns:
            Consensus analysis summary
        """
        try:
            if not results:
                return {
                    'overall_confidence': 0.0,
                    'consensus_direction': 'neutral',
                    'method_agreement': 0.0,
                    'top_signals': []
                }
            
            # Calculate overall confidence (weighted average)
            total_confidence = 0.0
            total_weight = 0.0
            
            method_weights = {
                AnalysisMethod.TECHNICAL_ANALYSIS: 1.0,
                AnalysisMethod.SMART_MONEY_CONCEPTS: 1.2,
                AnalysisMethod.ELLIOTT_WAVE: 0.8,
                AnalysisMethod.HARMONIC_PATTERNS: 0.9
            }
            
            for method, result in results.items():
                weight = method_weights.get(method, 1.0)
                total_confidence += result.confidence * weight
                total_weight += weight
            
            overall_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
            
            # Collect all signals
            all_signals = []
            for method, result in results.items():
                for signal in result.potential_signals:
                    signal_copy = signal.copy()
                    signal_copy['source_method'] = method.value
                    all_signals.append(signal_copy)
            
            # Determine consensus direction
            long_signals = [s for s in all_signals if s.get('direction') == 'LONG']
            short_signals = [s for s in all_signals if s.get('direction') == 'SHORT']
            
            if len(long_signals) > len(short_signals):
                consensus_direction = 'bullish'
            elif len(short_signals) > len(long_signals):
                consensus_direction = 'bearish'
            else:
                consensus_direction = 'neutral'
            
            # Calculate method agreement
            method_directions = []
            for method, result in results.items():
                if result.potential_signals:
                    method_long = len([s for s in result.potential_signals if s.get('direction') == 'LONG'])
                    method_short = len([s for s in result.potential_signals if s.get('direction') == 'SHORT'])
                    
                    if method_long > method_short:
                        method_directions.append('bullish')
                    elif method_short > method_long:
                        method_directions.append('bearish')
                    else:
                        method_directions.append('neutral')
            
            # Calculate agreement percentage
            if method_directions:
                most_common = max(set(method_directions), key=method_directions.count)
                agreement = method_directions.count(most_common) / len(method_directions)
            else:
                agreement = 0.0
            
            # Get top signals (sorted by confidence)
            top_signals = sorted(all_signals, key=lambda x: x.get('confidence', 0), reverse=True)[:5]
            
            return {
                'overall_confidence': round(overall_confidence, 2),
                'consensus_direction': consensus_direction,
                'method_agreement': round(agreement * 100, 1),
                'total_signals': len(all_signals),
                'long_signals': len(long_signals),
                'short_signals': len(short_signals),
                'top_signals': top_signals,
                'method_results': {
                    method.value: {
                        'confidence': result.confidence,
                        'signal_count': len(result.potential_signals)
                    }
                    for method, result in results.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating consensus analysis: {e}")
            return {
                'overall_confidence': 0.0,
                'consensus_direction': 'neutral',
                'method_agreement': 0.0,
                'top_signals': []
            }
    
    def filter_signals_by_confidence(self, 
                                   results: Dict[AnalysisMethod, AnalysisResult],
                                   min_confidence: float = 60.0) -> List[Dict]:
        """Filter signals by minimum confidence threshold"""
        try:
            filtered_signals = []
            
            for method, result in results.items():
                for signal in result.potential_signals:
                    if signal.get('confidence', 0) >= min_confidence:
                        signal_copy = signal.copy()
                        signal_copy['source_method'] = method.value
                        signal_copy['method_confidence'] = result.confidence
                        filtered_signals.append(signal_copy)
            
            # Sort by confidence
            filtered_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error filtering signals: {e}")
            return []
    
    def get_method_summary(self, 
                          results: Dict[AnalysisMethod, AnalysisResult]) -> Dict[str, Dict]:
        """Get summary of each analysis method's findings"""
        try:
            summary = {}
            
            for method, result in results.items():
                method_name = method.value
                
                # Count signals by direction
                signals = result.potential_signals
                long_count = len([s for s in signals if s.get('direction') == 'LONG'])
                short_count = len([s for s in signals if s.get('direction') == 'SHORT'])
                
                # Get key data points
                key_data = {}
                if result.data:
                    if method == AnalysisMethod.TECHNICAL_ANALYSIS:
                        key_data = {
                            'rsi': result.data.get('rsi', [np.nan])[-1] if 'rsi' in result.data else None,
                            'macd_signal': 'bullish' if result.data.get('macd', {}).get('histogram', [0])[-1] > 0 else 'bearish'
                        }
                    elif method == AnalysisMethod.SMART_MONEY_CONCEPTS:
                        key_data = {
                            'market_structure': result.data.get('market_structure', {}).get('type', 'unknown'),
                            'bos_choch_count': len(result.data.get('bos_choch', [])),
                            'fvg_count': len(result.data.get('fair_value_gaps', []))
                        }
                    elif method == AnalysisMethod.ELLIOTT_WAVE:
                        key_data = {
                            'wave_count': result.data.get('current_wave_count', {}).get('primary_count', 'Unknown'),
                            'pattern_count': len(result.data.get('wave_patterns', []))
                        }
                    elif method == AnalysisMethod.HARMONIC_PATTERNS:
                        key_data = {
                            'pattern_count': len(result.data.get('detected_patterns', [])),
                            'prz_zones': len(result.data.get('prz_zones', []))
                        }
                
                summary[method_name] = {
                    'confidence': result.confidence,
                    'signal_count': len(signals),
                    'long_signals': long_count,
                    'short_signals': short_count,
                    'bias': 'bullish' if long_count > short_count else 'bearish' if short_count > long_count else 'neutral',
                    'key_data': key_data,
                    'analyzed_at': result.analyzed_at.isoformat() if hasattr(result, 'analyzed_at') else datetime.utcnow().isoformat()
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating method summary: {e}")
            return {}

# Import numpy for the summary method
import numpy as np