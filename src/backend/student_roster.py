"""
Student Roster Manager
Handles loading, storing, and querying student name and email records using gather_intro_data() and gather_303_data().
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

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

    def __init__(self) -> None:
        self.students: list[StudentRecord] = []

    # --- Data Loading Methods ---

    def load_dataframe(self, df: pd.DataFrame) -> None:
        """
        Loads student records from a single pandas DataFrame.
        """
        self.load_from_dataframes(df)

    def load_from_dataframes(self, *dfs: Optional[pd.DataFrame]) -> None:
        """
        Merges student records from multiple pandas DataFrames (e.g., intro sheet and 303 sheet).
        De-duplicates records based on unique email addresses.
        Checks for 'Training Complete' flag if present.
        """
        df_ids = tuple(id(df) for df in dfs if df is not None)
        if getattr(self, '_last_df_ids', None) == df_ids:
            return
        self._last_df_ids = df_ids

        seen_emails = set()
        records = []
        for df in dfs:
            if df is None or not isinstance(df, pd.DataFrame):
                continue
            try:
                for _, row in df.iterrows():
                    # Extract name
                    name_raw = row.get("Name")
                    if pd.isna(name_raw) or not str(name_raw).strip():
                        name_raw = row.get("Trainee Name", "")
                    name = str(name_raw).strip()

                    # Extract email
                    email_raw = row.get("Email")
                    if pd.isna(email_raw) or not str(email_raw).strip():
                        email_raw = row.get("Trainee Email", "")
                    email = str(email_raw).strip()

                    # Check training complete if column exists
                    if "Training Complete" in row.index:
                        tc = row.get("Training Complete")
                        if pd.isna(tc):
                            continue
                        if isinstance(tc, bool):
                            if not tc:
                                continue
                        else:
                            tc_str = str(tc).strip().lower()
                            if tc_str not in ("true", "yes", "1", "on", "checked", "t", "y"):
                                continue

                    if (
                        name
                        and email
                        and name.lower() != "nan"
                        and email.lower() != "nan"
                        and email.lower() not in seen_emails
                    ):
                        seen_emails.add(email.lower())
                        records.append(StudentRecord(name=name, email=email))
            except (AttributeError, KeyError, ValueError, TypeError) as e:
                logger.error(
                    "Error parsing DataFrame row in load_from_dataframes: %s", e
                )

        if records:
            self.students = records
            logger.info("Merged %d student records from DataFrames.", len(records))

    async def refresh_from_backend(self) -> list[StudentRecord]:
        """
        Fetches intro and 303 sheet DataFrames from Power Automate using
        gather_intro_data() and gather_303_data() from backend.requests
        and merges them into the roster.
        """
        try:
            from backend.requests import gather_intro_data, gather_303_data

            df_intro = await gather_intro_data()
            df_303 = await gather_303_data()
            self.load_from_dataframes(df_intro, df_303)
        except Exception as e:
            logger.error("Error refreshing roster from backend: %s", e)
        return self.get_all_students()

    # --- Query Methods ---

    def get_all_students(self) -> list[StudentRecord]:
        """
        Returns all loaded student records sorted alphabetically by name.
        """
        return sorted(self.students, key=lambda s: s.name)


# --- Global Singleton Instance ---
# Shared singleton roster instance accessed across GUI pages and controllers
roster = RosterManager()

