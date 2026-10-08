"""
Domain model for maintenance reports.

This module defines the structured representation of a maintenance
report after it has been parsed from an email.
"""

from dataclasses import dataclass
from datetime import datetime, date


@dataclass
class MaintenanceReport:
    """
    Represents a parsed maintenance report.

    Attributes:
        report_date: Date to which the maintenance report relates.
        switch_overs: Number of switch-over events reported.
        generator: Generator identifier or name.
        running_time_hr: Generator running time in hours.
        running_time_mins: Generator running time in minutes.
        avg_load: Average generator load.
        volume_of_diesel: Volume of diesel reported.
        parsed_by: Identifier of the parser that produced the report.
        message_id: Unique identifier of the source email message.
    """
    
    report_date: tuple[date, int]
    switch_overs: tuple[int, int]
    generator: tuple[str, int]
    running_time_hr: tuple[int, int]
    running_time_mins: tuple[int, int]
    avg_load: tuple[float, int]
    volume_of_diesel: tuple[float, int]
    shift: tuple[str, int]