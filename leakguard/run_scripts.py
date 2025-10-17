#!/usr/bin/env python3
"""
Script runner for organized LeakGuard project
This script helps run various components from the organized project structure
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_telegram_scraper():
    """Run the integrated Telegram scraper"""
    print("🚀 Starting Telegram Scraper...")
    script_path = PROJECT_ROOT / "scripts" / "telegram" / "telegram_integrated_scraper.py"
    
    if script_path.exists():
        subprocess.run([sys.executable, str(script_path)])
    else:
        print(f"❌ Script not found: {script_path}")

def run_data_extractor():
    """Run the data extractor"""
    print("🔍 Starting Data Extractor...")
    script_path = PROJECT_ROOT / "scripts" / "data_processing" / "telegram_data_extractor.py"
    
    if script_path.exists():
        subprocess.run([sys.executable, str(script_path)])
    else:
        print(f"❌ Script not found: {script_path}")

def test_opensearch():
    """Test OpenSearch connection"""
    print("🔧 Testing OpenSearch Connection...")
    script_path = PROJECT_ROOT / "scripts" / "testing" / "test_opensearch_connection.py"
    
    if script_path.exists():
        subprocess.run([sys.executable, str(script_path)])
    else:
        print(f"❌ Script not found: {script_path}")

def run_django_command(command):
    """Run Django management command"""
    print(f"🐍 Running Django command: {command}")
    subprocess.run([sys.executable, "manage.py"] + command.split())

def show_menu():
    """Show the main menu"""
    print("\n" + "="*60)
    print("           LEAKGUARD PROJECT RUNNER")
    print("="*60)
    print("📁 Organized Project Structure")
    print("="*60)
    print("[1] Run Telegram Scraper (Interactive)")
    print("[2] Run Telegram Scraper (Command Line)")
    print("[3] Extract Telegram Data")
    print("[4] Detect Data Leaks")
    print("[5] Test OpenSearch Connection")
    print("[6] Show Project Statistics")
    print("[7] View Project Structure")
    print("[8] Django Management Commands")
    print("[Q] Quit")
    print("="*60)

def show_project_stats():
    """Show project statistics"""
    print("\n📊 Project Statistics")
    print("-" * 40)
    
    # Count files in each directory
    directories = {
        "Scripts": PROJECT_ROOT / "scripts",
        "Data": PROJECT_ROOT / "data",
        "Documentation": PROJECT_ROOT / "docs",
        "Configuration": PROJECT_ROOT / "config",
        "Logs": PROJECT_ROOT / "logs",
        "Media": PROJECT_ROOT / "media"
    }
    
    for name, path in directories.items():
        if path.exists():
            file_count = len(list(path.rglob("*"))) - len(list(path.rglob("*/")))
            print(f"{name:15}: {file_count:3} files")
        else:
            print(f"{name:15}: Directory not found")

def show_structure():
    """Show project structure"""
    print("\n📁 Project Structure")
    print("-" * 40)
    
    def print_tree(path, prefix="", max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return
            
        if path.is_dir():
            print(f"{prefix}📁 {path.name}/")
            try:
                items = sorted(path.iterdir())
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    new_prefix = prefix + ("└── " if is_last else "├── ")
                    if item.is_dir() and current_depth < max_depth - 1:
                        print_tree(item, new_prefix, max_depth, current_depth + 1)
                    else:
                        icon = "📁" if item.is_dir() else "📄"
                        print(f"{new_prefix}{icon} {item.name}")
            except PermissionError:
                print(f"{prefix}└── [Permission Denied]")
    
    print_tree(PROJECT_ROOT)

def django_commands_menu():
    """Show Django commands menu"""
    print("\n🐍 Django Management Commands")
    print("-" * 40)
    print("[1] Run Telegram Scraper (Interactive)")
    print("[2] Run Telegram Scraper (Add Channel)")
    print("[3] Extract Telegram Data")
    print("[4] Extract Data (with limit)")
    print("[5] Detect Data Leaks")
    print("[6] Export Data")
    print("[7] Show Statistics")
    print("[B] Back to main menu")
    
    choice = input("\nEnter your choice: ").lower().strip()
    
    if choice == '1':
        run_django_command("run_telegram_scraper --interactive")
    elif choice == '2':
        channel_id = input("Enter channel ID: ")
        channel_name = input("Enter channel name: ")
        run_django_command(f"run_telegram_scraper --add-channel {channel_id} {channel_name}")
    elif choice == '3':
        run_django_command("extract_telegram_data extract")
    elif choice == '4':
        limit = input("Enter limit (or press Enter for all): ")
        if limit:
            run_django_command(f"extract_telegram_data extract --limit {limit}")
        else:
            run_django_command("extract_telegram_data extract")
    elif choice == '5':
        run_django_command("extract_telegram_data leaks")
    elif choice == '6':
        filename = input("Enter output filename (or press Enter for default): ")
        if filename:
            run_django_command(f"extract_telegram_data export --output {filename}")
        else:
            run_django_command("extract_telegram_data export")
    elif choice == '7':
        run_django_command("extract_telegram_data stats")
    elif choice == 'b':
        return
    else:
        print("Invalid choice")

def main():
    """Main function"""
    while True:
        show_menu()
        choice = input("\nEnter your choice: ").lower().strip()
        
        if choice == '1':
            run_telegram_scraper()
        elif choice == '2':
            channel_ids = input("Enter channel IDs (space-separated, or press Enter for all): ")
            if channel_ids:
                run_django_command(f"run_telegram_scraper --channels {channel_ids}")
            else:
                run_django_command("run_telegram_scraper")
        elif choice == '3':
            run_data_extractor()
        elif choice == '4':
            run_django_command("extract_telegram_data leaks")
        elif choice == '5':
            test_opensearch()
        elif choice == '6':
            show_project_stats()
        elif choice == '7':
            show_structure()
        elif choice == '8':
            django_commands_menu()
        elif choice == 'q':
            print("\n👋 Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == '__main__':
    main()

