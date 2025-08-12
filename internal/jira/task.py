import pandas as pd
from datetime import datetime
from typing import Optional, Any


class Task:
    """
    Represents a Jira task/issue with methods for sprint analysis.
    
    This class encapsulates the logic for determining task completion
    within sprint boundaries based on Status Category and closure dates.
    """
    
    def __init__(self, row_data: pd.Series):
        """
        Initialize a Task from a pandas DataFrame row.
        
        Args:
            row_data: A pandas Series representing one row from the Jira export
        """
        # Core task information
        self.summary = row_data.get('Summary', '')
        self.issue_key = row_data.get('Issue key', '')
        self.issue_type = row_data.get('Issue_Type', row_data.get('Issue Type', ''))
        self.status = row_data.get('Status', '')
        self.status_category = row_data.get('Status Category', '')
        
        # Platform and assignment
        self.platform = row_data.get('Platform', '')
        self.assignee = row_data.get('Assignee', '')
        self.labels = row_data.get('Labels', '')
        
        # Story points and metrics
        self.story_points = self._parse_story_points(row_data.get('Story_Points', 0))
        
        # Dates
        self.created_date = self._parse_date(row_data.get('Created'))
        self.updated_date = self._parse_date(row_data.get('Updated'))
        self.closure_date = self._parse_date(row_data.get('Status Category Changed'))
        
        # Sprint information
        self.sprint = row_data.get('Sprint', '')
        
        # Store original row data for extensibility
        self._raw_data = row_data
    
    def _parse_story_points(self, value: Any) -> float:
        """Parse story points value to float, handling various formats."""
        try:
            if pd.isna(value):
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse date value to datetime, handling various formats."""
        if pd.isna(date_value) or date_value == '':
            return None
        
        try:
            # Handle different date formats
            if isinstance(date_value, str):
                # Try common Jira export format first
                try:
                    return pd.to_datetime(date_value, format='%d/%b/%y %H:%M')
                except ValueError:
                    # Fallback to general parsing
                    return pd.to_datetime(date_value, errors='coerce')
            else:
                return pd.to_datetime(date_value, errors='coerce')
        except Exception:
            return None
    
    def IsClosed(self, sprint_start_date: datetime, sprint_end_date: datetime) -> bool:
        """
        Determine if this task was closed within the specified sprint date range.
        
        A task is considered closed if:
        1. Status Category is 'Done'
        2. The closure date (Status Category Changed) falls within the sprint range
        
        Args:
            sprint_start_date: Start of the sprint period
            sprint_end_date: End of the sprint period (inclusive)
            
        Returns:
            bool: True if the task was closed within the sprint, False otherwise
        """
        # Must have 'Done' status category to be considered closed
        if self.status_category != 'Done':
            return False
        
        # Must have a valid closure date
        if self.closure_date is None:
            return False
        
        # Convert inputs to datetime if they're dates
        if hasattr(sprint_start_date, 'date'):
            sprint_start = pd.to_datetime(sprint_start_date)
        else:
            sprint_start = pd.to_datetime(sprint_start_date)
            
        if hasattr(sprint_end_date, 'date'):
            sprint_end = pd.to_datetime(sprint_end_date)
        else:
            sprint_end = pd.to_datetime(sprint_end_date)
        
        # Add end of day to sprint_end for inclusive comparison
        from datetime import timedelta
        sprint_end = sprint_end + timedelta(days=1) - timedelta(seconds=1)
        
        # Check if closure date falls within sprint range
        return sprint_start <= self.closure_date <= sprint_end
    
    def IsOriginallyPlanned(self, sprint_start_date: datetime) -> bool:
        """
        Determine if this task was originally planned (created before or on sprint start).
        
        Args:
            sprint_start_date: Start of the sprint period
            
        Returns:
            bool: True if the task was originally planned, False otherwise
        """
        if self.created_date is None:
            return False
        
        sprint_start = pd.to_datetime(sprint_start_date)
        return self.created_date.date() <= sprint_start.date()
    
    def GetPlatform(self) -> str:
        """Get the platform/team this task belongs to."""
        return self.platform
    
    def GetStoryPoints(self) -> float:
        """Get the story points assigned to this task."""
        return self.story_points
    
    def GetIssueType(self) -> str:
        """Get the issue type (Story, Bug, Task, etc.)."""
        return self.issue_type
    
    def GetAssignee(self) -> str:
        """Get the assignee of this task."""
        return self.assignee
    
    def GetLabels(self) -> str:
        """Get the labels assigned to this task."""
        return self.labels
    
    def __str__(self) -> str:
        """String representation of the task."""
        return f"Task({self.issue_key}: {self.summary[:50]}{'...' if len(self.summary) > 50 else ''})"
    
    def __repr__(self) -> str:
        """Developer representation of the task."""
        return f"Task(key='{self.issue_key}', platform='{self.platform}', status='{self.status_category}', points={self.story_points})"
