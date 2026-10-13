"""
Domain model for maintenance reports.

This module defines the structured representation of a maintenance
report after it has been parsed from an email.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class MaintenanceReport:
    """Structured representation of a parsed maintenance report."""

    report_date: tuple[date, int]
    switch_overs: tuple[int, int]
    generator: tuple[str, int]
    running_time_hr: tuple[float, int]
    running_time_mins: tuple[float, int]
    avg_load: tuple[float, int]
    volume_of_diesel: tuple[float, int]
    shift: tuple[str, int]