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
        self.db_name = "listings.db"
        self.init_jobs_table()
    
    def export_to_csv(self, listings: List[Dict[str, Any]], filename: str = None, append: bool = False) -> str:
        """
        Export listings to CSV file.
        
        Args:
            listings: List of listing dictionaries
            filename: Custom filename (optional)
            append: Whether to append to existing file
            
        Returns:
            Path to created CSV file
        """
        if not listings:
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
            
            # Write mode: 'a' for append, 'w' for write
            write_mode = 'a' if append else 'w'
            header = not append or not filepath.exists()
            
            df.to_csv(filepath, index=False, mode=write_mode, header=header, encoding='utf-8')
            
            logger.debug(f"Exported {len(listings)} listings to CSV (append={append}): {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise
    
    def export_to_jsonl(self, listings: List[Dict[str, Any]], filename: str) -> str:
        """
        Export listings to JSON Lines file (streaming-friendly).
        
        Args:
            listings: List of listing dictionaries
            filename: Output filename
            
        Returns:
            Path to JSONL file
        """
        if not listings:
            return None
        
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                for item in listings:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            logger.debug(f"Appended {len(listings)} listings to JSONL: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to export to JSONL: {e}")
            raise

    def finalize_json_from_jsonl(self, jsonl_filename: str, json_filename: str) -> str:
        """
        Read a JSONL file and convert it to a standard formatted JSON array,
        then delete the JSONL file.
        """
        jsonl_path = self.output_dir / jsonl_filename
        json_path = self.output_dir / json_filename
        
        if not jsonl_path.exists():
            logger.warning(f"JSONL file not found for finalization: {jsonl_path}")
            return None
            
        try:
            items = []
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        items.append(json.loads(line))
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            
            # Delete intermediate JSONL file
            jsonl_path.unlink()
            logger.info(f"Finalized JSON export and cleaned up JSONL: {json_path}")
            return str(json_path)
        except Exception as e:
            logger.error(f"Failed to finalize JSON: {e}")
            raise

    def export_to_json(self, listings: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Export listings to standard JSON file (full write).
        """
        if not listings:
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"listings_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(listings, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Exported {len(listings)} listings to JSON: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise
    
    def init_jobs_table(self):
        """Initialize the scrape_jobs table for tracking scraper runs."""
        db_path = self.output_dir / self.db_name
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrape_jobs (
                    job_id TEXT PRIMARY KEY,
                    site TEXT NOT NULL,
                    status TEXT NOT NULL,
                    config TEXT,
                    items_scraped INTEGER DEFAULT 0,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                )
            """)

            # Ensure newer schema columns exist on older databases.
            cursor.execute(
                "PRAGMA table_info(scrape_jobs)"
            )
            existing_cols = {row[1] for row in cursor.fetchall()}

            if "terminated_at" not in existing_cols:
                cursor.execute(
                    "ALTER TABLE scrape_jobs ADD COLUMN terminated_at TEXT"
                )

            conn.commit()
            conn.close()
            logger.debug("Exporter: jobs table initialized")
        except Exception as e:
            logger.error(f"Failed to initialize jobs table: {e}")

    def create_job(self, job_id: str, site: str, config: Dict[str, Any] = None) -> bool:
        """Create a new job entry in the database."""
        db_path = self.output_dir / self.db_name
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            started_at = datetime.now().isoformat()
            config_json = json.dumps(config) if config else None
            
            cursor.execute(
                "INSERT INTO scrape_jobs (job_id, site, status, config, started_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, site, "RUNNING", config_json, started_at)
            )
            conn.commit()
            conn.close()
            logger.info(f"Exporter: Created job {job_id} for site {site}")
            return True
        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {e}")
            return False

    def update_job_status(
        self,
        job_id: str,
        status: str,
        items_scraped: int = None,
        ended_at: bool = False,
        terminated_at: bool = False,
    ) -> bool:
        """Update the status and progress of an existing job."""
        if not job_id:
            return False
            
        db_path = self.output_dir / self.db_name
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            updates = ["status = ?"]
            params = [status]
            
            if items_scraped is not None:
                updates.append("items_scraped = ?")
                params.append(items_scraped)
            
            if ended_at:
                updates.append("ended_at = ?")
                params.append(datetime.now().isoformat())

            if terminated_at:
                updates.append("terminated_at = ?")
                params.append(datetime.now().isoformat())
            
            params.append(job_id)
            query = f"UPDATE scrape_jobs SET {', '.join(updates)} WHERE job_id = ?"
            
            cursor.execute(query, tuple(params))
            conn.commit()
            conn.close()
            logger.debug(f"Exporter: Updated job {job_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            return False

    def export_to_sqlite(self, listings: List[Dict[str, Any]], 
                        db_name: str = None,
                        table_name: str = "listings",
                        append: bool = True) -> str:
        """
        Export listings to SQLite database.
        
        Args:
            listings: List of listing dictionaries
            db_name: Database filename (defaults to self.db_name)
            table_name: Table name
            append: Whether to append or replace
            
        Returns:
            Path to database file
        """
        if not listings:
            return None
        
        db_name = db_name or self.db_name
        db_path = self.output_dir / db_name
        
        try:
            df = pd.DataFrame(listings)
            
            conn = sqlite3.connect(db_path)
            
            if not append:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            else:
                # Check whether the table already exists
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                table_exists = cursor.fetchone() is not None

                if table_exists:
                    # Detect any new columns in the incoming data that the table doesn't have
                    cursor.execute(f'PRAGMA table_info("{table_name}")')
                    existing_cols = {row[1] for row in cursor.fetchall()}
                    new_cols = [c for c in df.columns if c not in existing_cols]
                    
                    for col in new_cols:
                        # Infer SQLite type from pandas dtype
                        dtype = df[col].dtype
                        if pd.api.types.is_integer_dtype(dtype):
                            sql_type = 'INTEGER'
                        elif pd.api.types.is_float_dtype(dtype):
                            sql_type = 'REAL'
                        elif pd.api.types.is_bool_dtype(dtype):
                            sql_type = 'INTEGER'  # SQLite uses 0/1 for booleans
                        else:
                            sql_type = 'TEXT'
                            
                        logger.info(f"Exporter: Adding missing column '{col}' ({sql_type}) to SQLite table '{table_name}'")
                        # Note: SQLite ALTER TABLE ADD COLUMN allows adding columns to existing tables
                        cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" {sql_type}')
                    
                    conn.commit()

                df.to_sql(table_name, conn, if_exists='append', index=False)
            
            conn.close()
            
            logger.debug(f"Exported {len(listings)} listings to SQLite (append={append}): {db_path}")
            return str(db_path)
            
        except Exception as e:
            logger.error(f"Failed to export to SQLite: {e}")
            raise
    
    def export_all(self, listings: List[Dict[str, Any]], 
                   base_filename: str = None) -> Dict[str, str]:
        """
        Standard non-incremental export to all formats.
        """
        if not listings:
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
            'sqlite': self.export_to_sqlite(listings, append=False)
        }
        
        return results
