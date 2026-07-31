"""
Student Roster Manager
Handles loading, categorizing, and querying student records by enrollment year or category.
"""

from dataclasses import dataclass
from pathlib import Path
import csv
import logging
import pandas as pd
from typing import Optional

# --- Logger Configuration ---
logger = logging.getLogger(__name__)


# --- Data Models ---
@dataclass
class StudentRecord:
    """
    Data model representing a single student record.
    """
    name: str
    email: str
    category: str  # e.g., "2021", "2022", "2023", "2024", "2025", or "Staff / Cross-Registered"


# --- Roster Manager Class ---
class RosterManager:
    """
    Manages student roster data loading, DataFrame merging, and category filtering.
    """

    def __init__(self, csv_path: Optional[Path] = None) -> None:
        """
        Initializes an empty student roster or loads records from a CSV file if provided.
        """
        self.students: list[StudentRecord] = []
        if csv_path and csv_path.exists():
            self.load_csv(csv_path)

    # --- Data Loading Methods ---

    def load_csv(self, csv_path: Path) -> None:
        """
        Loads student records from a specified CSV file.
        """
        try:
            records = []
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(
                        StudentRecord(
                            name=row.get("Name", "").strip(),
                            email=row.get("Email", "").strip(),
                            category=row.get("Category", "").strip(),
                        )
                    )
            if records:
                self.students = records
                logger.info("Loaded %d student records from %s", len(records), csv_path)
        except Exception as e:
            logger.error("Failed to load student roster CSV from %s: %s", csv_path, e)
            self.students = []

    def load_dataframe(self, df: pd.DataFrame) -> None:
        """
        Loads student records from a pandas DataFrame containing 'Name' and 'Email' columns.
        """
        try:
            records = []
            for _, row in df.iterrows():
                name = str(row.get("Name", "")).strip()
                email = str(row.get("Email", "")).strip()
                category = str(row.get("Category", "")).strip()
                if name and email:
                    records.append(StudentRecord(name=name, email=email, category=category))
            if records:
                self.students = records
                logger.info("Loaded %d student records from DataFrame.", len(records))
        except Exception as e:
            logger.error("Failed to load student roster from DataFrame: %s", e)

    def load_from_dataframes(self, *dfs: Optional[pd.DataFrame]) -> None:
        """
        Merges student records from multiple pandas DataFrames (e.g., intro sheet and 303 sheet).
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
                    category = str(row.get("Category", "")).strip()
                    if name and email and email.lower() not in seen_emails:
                        seen_emails.add(email.lower())
                        records.append(StudentRecord(name=name, email=email, category=category))
            except Exception as e:
                logger.error("Error parsing DataFrame row in load_from_dataframes: %s", e)

        if records:
            self.students = records
            logger.info("Merged %d student records from DataFrames.", len(records))

    # --- Category & Query Methods ---

    def get_categories(self) -> list[str]:
        """
        Returns sorted category names (enrollment years descending, with Staff at the end).
        """
        categories = set(s.category for s in self.students if s.category)
        default_years = ["2021", "2022", "2023", "2024", "2025", "Staff / Cross-Registered"]
        for cat in default_years:
            categories.add(cat)
        
        years = sorted([c for c in categories if c != "Staff / Cross-Registered"], reverse=True)
        if "Staff / Cross-Registered" in categories:
            years.append("Staff / Cross-Registered")
        return years

    def get_students_by_category(self, category: str) -> list[StudentRecord]:
        """
        Returns student records belonging to a specific category, sorted by name.
        """
        filtered = [s for s in self.students if s.category == category]
        return sorted(filtered, key=lambda s: s.name)

    def get_all_students(self) -> list[StudentRecord]:
        """
        Returns all loaded student records sorted alphabetically by name.
        """
        return sorted(self.students, key=lambda s: s.name)


# --- Global Singleton Instance ---
# Global roster instance accessed by GUI components
roster = RosterManager()

