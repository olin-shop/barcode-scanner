"""
Student Roster Manager
Handles loading, storing, and querying student name and email records.
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

# --- Logger Configuration ---
# Global logger instance for student roster operations
logger = logging.getLogger(__name__)


# --- Data Models ---
@dataclass
class StudentRecord:
    """
    Data model representing a single student record with a name and email.
    """

    name: str
    email: str


# --- Roster Manager Class ---
class RosterManager:
    """
    Manages student roster data loading, DataFrame merging, and name sorting.
    """

    def __init__(self, csv_path: Optional[Path] = None) -> None:
        """
        Initializes an empty student roster list or loads records from CSV if a path is provided.
        """
        self.students: list[StudentRecord] = []
        if csv_path and csv_path.exists():
            self.load_csv(csv_path)

    # --- Data Loading Methods ---

    def load_csv(self, csv_path: Path) -> None:
        """
        Loads student records from a specified CSV file containing 'Name' and 'Email' headers.
        """
        try:
            records = []
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("Name", "").strip()
                    email = row.get("Email", "").strip()
                    if name and email:
                        records.append(StudentRecord(name=name, email=email))
            if records:
                self.students = records
                logger.info("Loaded %d student records from %s", len(records), csv_path)
        except Exception as e:
            logger.error("Failed to load student roster CSV from %s: %s", csv_path, e)
            self.students = []

    def load_dataframe(self, df: pd.DataFrame) -> None:
        """
        Loads student records from a single pandas DataFrame containing 'Name' and 'Email' columns.
        """
        try:
            records = []
            for _, row in df.iterrows():
                name = str(row.get("Name", "")).strip()
                email = str(row.get("Email", "")).strip()
                if name and email:
                    records.append(StudentRecord(name=name, email=email))
            if records:
                self.students = records
                logger.info("Loaded %d student records from DataFrame.", len(records))
        except Exception as e:
            logger.error("Failed to load student roster from DataFrame: %s", e)

    def load_from_dataframes(self, *dfs: Optional[pd.DataFrame]) -> None:
        """
        Merges student records from multiple pandas DataFrames (e.g., intro sheet and 303 sheet).
        De-duplicates records based on unique email addresses.
        """
        seen_emails = set()
        records = []
        for df in dfs:
            if df is None:
                continue
            try:
                for _, row in df.iterrows():
                    name = str(row.get("Name", "")).strip()
                    email = str(row.get("Email", "")).strip()
                    if name and email and email.lower() not in seen_emails:
                        seen_emails.add(email.lower())
                        records.append(StudentRecord(name=name, email=email))
            except Exception as e:
                logger.error(
                    "Error parsing DataFrame row in load_from_dataframes: %s", e
                )

        if records:
            self.students = records
            logger.info("Merged %d student records from DataFrames.", len(records))

    # --- Query Methods ---

    def get_all_students(self) -> list[StudentRecord]:
        """
        Returns all loaded student records sorted alphabetically by name.
        """
        return sorted(self.students, key=lambda s: s.name)


# --- Global Singleton Instance ---
# Shared singleton roster instance accessed across GUI pages and controllers
roster = RosterManager()
