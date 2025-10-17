#!/usr/bin/env python3
"""
Telegram Data Collection Scheduler
Runs the Telegram collection automation on a schedule
"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime
import subprocess

# Add Django project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramScheduler:
    """Scheduler for automated Telegram data collection"""
    
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.manage_py = os.path.join(self.project_dir, 'manage.py')
        
    def run_collection(self):
        """Run the Telegram collection command"""
        try:
            logger.info("Starting scheduled Telegram collection...")
            
            # Run the Django management command
            cmd = [
                sys.executable,
                self.manage_py,
                'telegram_collector',
                '--limit', '50'  # Collect 50 messages per channel
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info("Telegram collection completed successfully")
                logger.info(f"Output: {result.stdout}")
            else:
                logger.error(f"Telegram collection failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Telegram collection timed out after 1 hour")
        except Exception as e:
            logger.error(f"Error running Telegram collection: {e}")
    
    def run_channels_only(self):
        """Run collection to join new channels only"""
        try:
            logger.info("Starting scheduled channel joining...")
            
            cmd = [
                sys.executable,
                self.manage_py,
                'telegram_collector',
                '--channels-only'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("Channel joining completed successfully")
            else:
                logger.error(f"Channel joining failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error running channel joining: {e}")
    
    def start_scheduler(self):
        """Start the scheduler with predefined jobs"""
        logger.info("Starting Telegram collection scheduler...")
        
        # Schedule jobs
        schedule.every(6).hours.do(self.run_collection)  # Full collection every 6 hours
        schedule.every().day.at("02:00").do(self.run_channels_only)  # Join new channels daily at 2 AM
        schedule.every().hour.do(self.run_collection)  # Quick collection every hour
        
        logger.info("Scheduled jobs:")
        logger.info("- Full collection: every 6 hours")
        logger.info("- Channel joining: daily at 2:00 AM")
        logger.info("- Quick collection: every hour")
        
        # Run initial collection
        logger.info("Running initial collection...")
        self.run_collection()
        
        # Keep scheduler running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying

def main():
    """Main function"""
    scheduler = TelegramScheduler()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'run':
            scheduler.run_collection()
        elif command == 'channels':
            scheduler.run_channels_only()
        elif command == 'start':
            scheduler.start_scheduler()
        else:
            print("Usage: python telegram_scheduler.py [run|channels|start]")
    else:
        # Default: start the scheduler
        scheduler.start_scheduler()

if __name__ == "__main__":
    main()
