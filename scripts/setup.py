#!/usr/bin/env python3
"""
Setup script for Crypto Signal System
Handles initial configuration and database setup
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.storage import StorageManager
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_databases():
    """Setup and initialize databases"""
    try:
        logger.info("🔄 Setting up databases...")
        
        storage = StorageManager()
        await storage.initialize()
        
        logger.info("✅ Databases initialized successfully")
        await storage.close()
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        raise

def create_directories():
    """Create necessary directories"""
    try:
        directories = [
            "screenshots",
            "logs",
            "data",
            "backups"
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
            logger.info(f"📁 Created directory: {directory}")
        
        logger.info("✅ Directories created")
        
    except Exception as e:
        logger.error(f"❌ Directory creation failed: {e}")
        raise

def check_environment():
    """Check environment configuration"""
    try:
        logger.info("🔍 Checking environment configuration...")
        
        required_vars = ["BOT_TOKEN"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            logger.info("💡 Please check your .env file")
            return False
        
        # Optional variables with warnings
        optional_vars = {
            "BINANCE_API_KEY": "Binance API access",
            "TV_USERNAME": "TradingView screenshots",
            "ADMIN_CHAT_ID": "Admin notifications"
        }
        
        for var, description in optional_vars.items():
            if not os.getenv(var):
                logger.warning(f"⚠️ Optional variable {var} not set - {description} disabled")
        
        logger.info("✅ Environment configuration checked")
        return True
        
    except Exception as e:
        logger.error(f"❌ Environment check failed: {e}")
        return False

def generate_sample_config():
    """Generate sample configuration files"""
    try:
        # Generate .env if it doesn't exist
        if not Path(".env").exists():
            logger.info("📝 Generating .env file from template...")
            
            with open(".env.example", "r") as template:
                content = template.read()
            
            with open(".env", "w") as env_file:
                env_file.write(content)
            
            logger.info("✅ .env file created - please configure it")
        
        logger.info("✅ Configuration files ready")
        
    except Exception as e:
        logger.error(f"❌ Configuration generation failed: {e}")
        raise

async def main():
    """Main setup function"""
    try:
        logger.info("🚀 Starting Crypto Signal System Setup...")
        
        # Step 1: Generate configuration
        generate_sample_config()
        
        # Step 2: Check environment
        if not check_environment():
            logger.error("❌ Setup failed - please fix environment configuration")
            return False
        
        # Step 3: Create directories
        create_directories()
        
        # Step 4: Setup databases (if available)
        try:
            await setup_databases()
        except Exception as e:
            logger.warning(f"⚠️ Database setup skipped: {e}")
            logger.info("💡 Databases will be initialized on first run")
        
        logger.info("🎉 Setup completed successfully!")
        logger.info("📋 Next steps:")
        logger.info("  1. Configure your .env file with API keys")
        logger.info("  2. Run: python main.py")
        logger.info("  3. Or use Docker: docker-compose up -d")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)