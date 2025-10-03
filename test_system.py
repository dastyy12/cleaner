#!/usr/bin/env python3
"""
System Test - Verify crypto signal system functionality
"""
import asyncio
import logging
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.analysis.technical_analysis import TechnicalAnalyzer
from src.analysis.smart_money_concepts import SmartMoneyAnalyzer
from src.analysis.elliott_wave import ElliottWaveAnalyzer
from src.analysis.harmonic_patterns import HarmonicAnalyzer
from src.analysis.analyzer_manager import AnalyzerManager
from src.models import AnalysisMethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_test_data(length: int = 200) -> pd.DataFrame:
    """Generate realistic test OHLCV data"""
    try:
        # Generate base price trend
        base_price = 45000  # Starting price (like BTC)
        trend = np.cumsum(np.random.randn(length) * 0.02)  # 2% daily volatility
        
        # Generate OHLCV data
        data = []
        for i in range(length):
            price = base_price * (1 + trend[i])
            
            # Generate realistic OHLC
            daily_range = price * 0.03  # 3% daily range
            open_price = price + np.random.randn() * daily_range * 0.3
            close_price = price + np.random.randn() * daily_range * 0.3
            
            high_price = max(open_price, close_price) + abs(np.random.randn()) * daily_range * 0.2
            low_price = min(open_price, close_price) - abs(np.random.randn()) * daily_range * 0.2
            
            volume = 1000000 + abs(np.random.randn()) * 500000
            
            data.append({
                'timestamp': datetime.utcnow() - timedelta(hours=length-i),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Error generating test data: {e}")
        raise

async def test_technical_analysis():
    """Test Technical Analysis module"""
    try:
        logger.info("🔍 Testing Technical Analysis...")
        
        analyzer = TechnicalAnalyzer()
        test_data = generate_test_data()
        
        result = analyzer.analyze(test_data, "BTCUSDT", "1h")
        
        assert result.method == AnalysisMethod.TECHNICAL_ANALYSIS
        assert result.symbol == "BTCUSDT"
        assert result.timeframe == "1h"
        assert 0 <= result.confidence <= 100
        
        logger.info(f"✅ TA Analysis: {result.confidence:.1f}% confidence, {len(result.potential_signals)} signals")
        return True
        
    except Exception as e:
        logger.error(f"❌ Technical Analysis test failed: {e}")
        return False

async def test_smart_money_concepts():
    """Test Smart Money Concepts module"""
    try:
        logger.info("🔍 Testing Smart Money Concepts...")
        
        analyzer = SmartMoneyAnalyzer()
        test_data = generate_test_data()
        
        result = analyzer.analyze(test_data, "ETHUSDT", "4h")
        
        assert result.method == AnalysisMethod.SMART_MONEY_CONCEPTS
        assert result.symbol == "ETHUSDT"
        assert result.timeframe == "4h"
        assert 0 <= result.confidence <= 100
        
        logger.info(f"✅ SMC Analysis: {result.confidence:.1f}% confidence, {len(result.potential_signals)} signals")
        return True
        
    except Exception as e:
        logger.error(f"❌ Smart Money Concepts test failed: {e}")
        return False

async def test_elliott_wave():
    """Test Elliott Wave module"""
    try:
        logger.info("🔍 Testing Elliott Wave...")
        
        analyzer = ElliottWaveAnalyzer()
        test_data = generate_test_data(300)  # Need more data for waves
        
        result = analyzer.analyze(test_data, "ADAUSDT", "1h")
        
        assert result.method == AnalysisMethod.ELLIOTT_WAVE
        assert result.symbol == "ADAUSDT"
        assert result.timeframe == "1h"
        assert 0 <= result.confidence <= 100
        
        logger.info(f"✅ Elliott Wave: {result.confidence:.1f}% confidence, {len(result.potential_signals)} signals")
        return True
        
    except Exception as e:
        logger.error(f"❌ Elliott Wave test failed: {e}")
        return False

async def test_harmonic_patterns():
    """Test Harmonic Patterns module"""
    try:
        logger.info("🔍 Testing Harmonic Patterns...")
        
        analyzer = HarmonicAnalyzer()
        test_data = generate_test_data(150)
        
        result = analyzer.analyze(test_data, "SOLUSDT", "1h")
        
        assert result.method == AnalysisMethod.HARMONIC_PATTERNS
        assert result.symbol == "SOLUSDT"
        assert result.timeframe == "1h"
        assert 0 <= result.confidence <= 100
        
        logger.info(f"✅ Harmonic Patterns: {result.confidence:.1f}% confidence, {len(result.potential_signals)} signals")
        return True
        
    except Exception as e:
        logger.error(f"❌ Harmonic Patterns test failed: {e}")
        return False

async def test_analyzer_manager():
    """Test Analyzer Manager coordination"""
    try:
        logger.info("🔍 Testing Analyzer Manager...")
        
        manager = AnalyzerManager()
        await manager.initialize()
        
        test_data = generate_test_data()
        
        # Test single symbol analysis
        results = await manager.analyze_symbol(
            symbol="BTCUSDT",
            exchange="binance",
            timeframe="1h",
            data=test_data
        )
        
        assert len(results) > 0
        assert AnalysisMethod.TECHNICAL_ANALYSIS in results
        
        # Test consensus analysis
        consensus = manager.get_consensus_analysis(results)
        
        assert 'overall_confidence' in consensus
        assert 'consensus_direction' in consensus
        assert 'method_agreement' in consensus
        
        logger.info(f"✅ Analyzer Manager: {consensus['overall_confidence']:.1f}% consensus, {consensus['total_signals']} total signals")
        return True
        
    except Exception as e:
        logger.error(f"❌ Analyzer Manager test failed: {e}")
        return False

async def test_risk_management():
    """Test Risk Management utilities"""
    try:
        logger.info("🔍 Testing Risk Management...")
        
        from src.utils.risk_management import RiskManager
        from src.models import Signal, SignalDirection, TimeFrame, PriceLevel, RiskManagement
        
        risk_manager = RiskManager()
        
        # Create test signal
        signal = Signal(
            id="test_signal",
            symbol="BTCUSDT",
            exchange="binance",
            direction=SignalDirection.LONG,
            timeframe=TimeFrame.H1,
            entry_price=PriceLevel(price=45000.0),
            risk_management=RiskManagement(
                stop_loss=PriceLevel(price=44000.0),
                take_profits=[PriceLevel(price=46500.0), PriceLevel(price=48000.0)],
                recommended_leverage=3,
                risk_per_trade=2.0
            ),
            confidence=75.0,
            expected_rr=2.5,
            reasons=[]
        )
        
        # Test position sizing
        position_info = risk_manager.calculate_optimal_position_size(
            account_balance=10000.0,
            signal=signal
        )
        
        assert 'position_size_usd' in position_info
        assert 'optimal_leverage' in position_info
        assert 'risk_percentage' in position_info
        
        logger.info(f"✅ Risk Management: ${position_info['position_size_usd']:.2f} position, {position_info['optimal_leverage']}x leverage")
        return True
        
    except Exception as e:
        logger.error(f"❌ Risk Management test failed: {e}")
        return False

async def test_utilities():
    """Test utility functions"""
    try:
        logger.info("🔍 Testing Utilities...")
        
        from src.utils.helpers import (
            format_price, calculate_fibonacci_levels, 
            validate_signal_data, calculate_risk_reward_ratio
        )
        
        # Test price formatting
        assert format_price(45123.456) == "45,123.46"
        assert format_price(0.00123456) == "0.00123456"
        
        # Test Fibonacci levels
        fib_levels = calculate_fibonacci_levels(50000, 40000)
        assert '61.8' in fib_levels
        assert fib_levels['61.8'] == 43820.0
        
        # Test signal validation
        valid_signal = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 45000.0,
            'stop_loss': 44000.0,
            'confidence': 75.0
        }
        
        validated = validate_signal_data(valid_signal)
        assert validated['symbol'] == 'BTCUSDT'
        
        # Test R/R calculation
        rr = calculate_risk_reward_ratio(45000, 44000, 47000)
        assert rr == 2.0
        
        logger.info("✅ Utilities: All helper functions working")
        return True
        
    except Exception as e:
        logger.error(f"❌ Utilities test failed: {e}")
        return False

async def run_system_test():
    """Run comprehensive system test"""
    try:
        logger.info("🚀 Starting Crypto Signal System Test...")
        
        tests = [
            ("Technical Analysis", test_technical_analysis),
            ("Smart Money Concepts", test_smart_money_concepts),
            ("Elliott Wave", test_elliott_wave),
            ("Harmonic Patterns", test_harmonic_patterns),
            ("Analyzer Manager", test_analyzer_manager),
            ("Risk Management", test_risk_management),
            ("Utilities", test_utilities)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"Running: {test_name}")
                logger.info(f"{'='*50}")
                
                success = await test_func()
                if success:
                    passed += 1
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    failed += 1
                    logger.error(f"❌ {test_name} FAILED")
                    
            except Exception as e:
                failed += 1
                logger.error(f"❌ {test_name} FAILED with exception: {e}")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info(f"TEST SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! System is ready to run.")
            return True
        else:
            logger.error("⚠️ Some tests failed. Please check the errors above.")
            return False
            
    except Exception as e:
        logger.error(f"❌ System test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_system_test())
    sys.exit(0 if success else 1)