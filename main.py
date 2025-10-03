"""
Main entry point for the crypto signal generation system
Real-time multi-exchange futures analysis with TradingView integration
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.core.signal_engine import SignalEngine
from src.telegram.bot import TelegramBot
from src.data.data_manager import DataManager
from src.analysis.analyzer_manager import AnalyzerManager
from src.tradingview.tv_integration import TradingViewIntegration
from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crypto_signals.log")
    ]
)

logger = logging.getLogger(__name__)

class CryptoSignalSystem:
    """Main system orchestrator"""
    
    def __init__(self):
        self.data_manager = None
        self.analyzer_manager = None
        self.signal_engine = None
        self.telegram_bot = None
        self.tv_integration = None
        self.running = False
    
    async def initialize(self):
        """Initialize all system components"""
        logger.info("🚀 Initializing Crypto Signal System...")
        
        try:
            # Initialize data manager
            self.data_manager = DataManager()
            await self.data_manager.initialize()
            logger.info("✅ Data Manager initialized")
            
            # Initialize analyzer manager
            self.analyzer_manager = AnalyzerManager()
            await self.analyzer_manager.initialize()
            logger.info("✅ Analyzer Manager initialized")
            
            # Initialize TradingView integration
            self.tv_integration = TradingViewIntegration()
            await self.tv_integration.initialize()
            logger.info("✅ TradingView Integration initialized")
            
            # Initialize signal engine
            self.signal_engine = SignalEngine(
                data_manager=self.data_manager,
                analyzer_manager=self.analyzer_manager,
                tv_integration=self.tv_integration
            )
            await self.signal_engine.initialize()
            logger.info("✅ Signal Engine initialized")
            
            # Initialize Telegram bot
            self.telegram_bot = TelegramBot(signal_engine=self.signal_engine)
            await self.telegram_bot.initialize()
            logger.info("✅ Telegram Bot initialized")
            
            logger.info("🎉 System initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            raise
    
    async def start(self):
        """Start the system"""
        if not self.running:
            logger.info("🔄 Starting Crypto Signal System...")
            
            # Start all components
            tasks = []
            
            # Start data ingestion
            tasks.append(asyncio.create_task(self.data_manager.start_streaming()))
            
            # Start signal generation
            tasks.append(asyncio.create_task(self.signal_engine.start()))
            
            # Start Telegram bot
            tasks.append(asyncio.create_task(self.telegram_bot.start()))
            
            self.running = True
            logger.info("✅ System started successfully!")
            
            # Wait for all tasks
            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt:
                logger.info("🛑 Received shutdown signal")
                await self.stop()
            except Exception as e:
                logger.error(f"❌ System error: {e}")
                await self.stop()
                raise
    
    async def stop(self):
        """Stop the system gracefully"""
        if self.running:
            logger.info("🛑 Stopping Crypto Signal System...")
            
            # Stop all components
            if self.telegram_bot:
                await self.telegram_bot.stop()
            
            if self.signal_engine:
                await self.signal_engine.stop()
            
            if self.data_manager:
                await self.data_manager.stop()
            
            if self.tv_integration:
                await self.tv_integration.stop()
            
            self.running = False
            logger.info("✅ System stopped gracefully")

async def main():
    """Main entry point"""
    system = CryptoSignalSystem()
    
    try:
        await system.initialize()
        await system.start()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
    finally:
        await system.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"💥 Startup failed: {e}")
        sys.exit(1)