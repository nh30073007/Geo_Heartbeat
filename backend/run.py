#!/usr/bin/env python3
"""
Geo AI - Strategic Nexus Realtime Fixed
FastAPI Entry Point
"""
import uvicorn
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Ensure data directories exist
    Path("data/cache").mkdir(parents=True, exist_ok=True)
    Path("data/reports").mkdir(parents=True, exist_ok=True)
    Path("data/results").mkdir(parents=True, exist_ok=True)
    Path("data/exports").mkdir(parents=True, exist_ok=True)
    
    logger.info("🚀 Starting Geo AI Strategic Nexus...")
    logger.info("📂 Data directories created")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )