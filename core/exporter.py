"""
Exporter module for saving data to various formats.
"""
import json
import csv
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger
import pandas as pd


class Exporter:
    """Handles exporting data to CSV, JSON, and SQLite."""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize exporter with output directory.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def export_to_csv(self, listings: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Export listings to CSV file.
        
        Args:
            listings: List of listing dictionaries
            filename: Custom filename (optional)
            
        Returns:
            Path to created CSV file
        """
        if not listings:
            logger.warning("No listings to export to CSV")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"listings_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        try:
            # Use pandas for easier CSV export
            df = pd.DataFrame(listings)
            
            # Reorder columns to put important ones first
            preferred_order = [
                'title', 'price', 'location', 'bedrooms', 'bathrooms',
                'property_type', 'listing_url', 'description', 'agent_name',
                'agent_phone', 'listing_id', 'date_posted'
            ]
            
            # Only include columns that exist
            columns = [col for col in preferred_order if col in df.columns]
            # Add any remaining columns
            columns.extend([col for col in df.columns if col not in columns])
            
            df = df[columns]
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            logger.info(f"Exported {len(listings)} listings to CSV: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise
    
    def export_to_json(self, listings: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Export listings to JSON file.
        
        Args:
            listings: List of listing dictionaries
            filename: Custom filename (optional)
            
        Returns:
            Path to created JSON file
        """
        if not listings:
            logger.warning("No listings to export to JSON")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"listings_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(listings, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(listings)} listings to JSON: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise
    
    def export_to_sqlite(self, listings: List[Dict[str, Any]], 
                        db_name: str = "listings.db",
                        table_name: str = "listings") -> str:
        """
        Export listings to SQLite database.
        
        Args:
            listings: List of listing dictionaries
            db_name: Database filename
            table_name: Table name
            
        Returns:
            Path to database file
        """
        if not listings:
            logger.warning("No listings to export to SQLite")
            return None
        
        db_path = self.output_dir / db_name
        
        try:
            # Use pandas for easier SQLite export
            df = pd.DataFrame(listings)
            
            # Create connection
            conn = sqlite3.connect(db_path)
            
            # Write to database (replace if exists)
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            conn.close()
            
            logger.info(f"Exported {len(listings)} listings to SQLite: {db_path}")
            return str(db_path)
            
        except Exception as e:
            logger.error(f"Failed to export to SQLite: {e}")
            raise
    
    def export_all(self, listings: List[Dict[str, Any]], 
                   base_filename: str = None) -> Dict[str, str]:
        """
        Export to all formats (CSV, JSON, SQLite).
        
        Args:
            listings: List of listing dictionaries
            base_filename: Base filename (timestamp added automatically)
            
        Returns:
            Dictionary with paths to all created files
        """
        if not listings:
            logger.warning("No listings to export")
            return {}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if base_filename:
            csv_name = f"{base_filename}_{timestamp}.csv"
            json_name = f"{base_filename}_{timestamp}.json"
        else:
            csv_name = f"listings_{timestamp}.csv"
            json_name = f"listings_{timestamp}.json"
        
        results = {
            'csv': self.export_to_csv(listings, csv_name),
            'json': self.export_to_json(listings, json_name),
            'sqlite': self.export_to_sqlite(listings)
        }
        
        logger.info(f"Exported to all formats: {results}")
        return results
