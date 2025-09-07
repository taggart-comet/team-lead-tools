import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Tuple
from .task import Task


class Sprint:
    """
    Represents a sprint with all its associated tasks and provides methods
    for calculating sprint metrics, scope drops, and capacity analysis.
    
    This class encapsulates all sprint-related business logic in one place,
    making the code much more readable and maintainable.
    """
    
    def __init__(self, tasks: List[Task], start_date: date, end_date: date):
        """
        Initialize a Sprint with tasks and date boundaries.
        
        Args:
            tasks: List of Task objects for this sprint
            start_date: Sprint start date
            end_date: Sprint end date
        """
        self.tasks = tasks
        self.start_date = start_date
        self.end_date = end_date
        
        # Cache computed results for performance
        self._closed_tasks = None
        self._originally_planned_tasks = None
        self._platform_metrics = None
    
    def GetClosedTasks(self) -> List[Task]:
        """Get all tasks that were closed within this sprint's date range."""
        if self._closed_tasks is None:
            self._closed_tasks = [task for task in self.tasks if task.IsClosed(self.start_date, self.end_date)]
        return self._closed_tasks
    
    def GetOriginallyPlannedTasks(self) -> List[Task]:
        """Get all tasks that were originally planned (created before or on sprint start)."""
        if self._originally_planned_tasks is None:
            self._originally_planned_tasks = [task for task in self.tasks if task.IsOriginallyPlanned(self.start_date)]
        return self._originally_planned_tasks
    
    def GetActivePlatforms(self) -> List[str]:
        """Get list of all platforms that have tasks in this sprint."""
        platforms = set()
        for task in self.tasks:
            platform = task.GetPlatform()
            if platform:  # Skip empty platforms
                platforms.add(platform)
        return sorted(list(platforms))
    
    def GetTotalCompletedStoryPoints(self) -> float:
        """Get total story points completed in this sprint."""
        return sum(task.GetStoryPoints() for task in self.GetClosedTasks())
    
    def GetTotalPlannedStoryPoints(self) -> float:
        """Get total story points planned for this sprint (all tasks)."""
        return sum(task.GetStoryPoints() for task in self.tasks)
    
    def GetOriginallyPlannedStoryPoints(self) -> float:
        """Get total story points that were originally planned (first day tasks)."""
        return sum(task.GetStoryPoints() for task in self.GetOriginallyPlannedTasks())
    
    def GetOriginallyCompletedStoryPoints(self) -> float:
        """Get story points from originally planned tasks that were completed."""
        originally_planned = self.GetOriginallyPlannedTasks()
        closed_tasks = self.GetClosedTasks()
        
        # Find intersection: tasks that are both originally planned AND closed
        originally_planned_ids = {id(task) for task in originally_planned}
        completed_points = 0
        
        for task in closed_tasks:
            if id(task) in originally_planned_ids:
                completed_points += task.GetStoryPoints()
                
        return completed_points
    
    def GetCompletedItems(self) -> int:
        """Get number of items completed in this sprint."""
        return len(self.GetClosedTasks())
    
    def GetTotalContributors(self) -> int:
        """Get total number of unique contributors across all platforms."""
        contributors = set()
        for task in self.tasks:
            assignee = task.GetAssignee()
            if assignee:  # Skip empty assignees
                contributors.add(assignee)
        return len(contributors)
    
    def GetAverageStoryPointsPerItem(self) -> float:
        """Get average story points per completed item."""
        completed_items = self.GetCompletedItems()
        if completed_items == 0:
            return 0.0
        return self.GetTotalCompletedStoryPoints() / completed_items
    
    def GetAverageCapacityPerContributor(self) -> float:
        """Get average story points delivered per full-time contributor (≥5 SP)."""
        full_time_contributors = self.GetFullTimeContributorsCount()
        if full_time_contributors == 0:
            return 0.0
        return self.GetTotalCompletedStoryPoints() / full_time_contributors
    
    def GetFullTimeContributorsCount(self) -> int:
        """Get count of full-time contributors (those who completed ≥5 story points)."""
        contributor_points = {}
        closed_tasks = self.GetClosedTasks()
        
        for task in closed_tasks:
            contributor = task.GetAssignee()
            if contributor:  # Skip empty assignees
                if contributor not in contributor_points:
                    contributor_points[contributor] = 0
                contributor_points[contributor] += task.GetStoryPoints()
        
        # Count contributors with ≥5 story points
        full_time_count = sum(1 for points in contributor_points.values() if points >= 5.0)
        return full_time_count
    
    def GetNaiveScopeDrop(self) -> float:
        """
        Get naive scope drop percentage (based on all planned work).
        Formula: (All Planned SP - Completed SP) / All Planned SP × 100
        """
        total_planned = self.GetTotalPlannedStoryPoints()
        total_completed = self.GetTotalCompletedStoryPoints()
        
        if total_planned == 0:
            return 0.0
        
        return ((total_planned - total_completed) / total_planned) * 100
    
    def GetActualScopeDrop(self) -> float:
        """
        Get actual scope drop percentage (based on originally planned work).
        Formula: (Originally Planned SP - Originally Completed SP) / Originally Planned SP × 100
        """
        originally_planned = self.GetOriginallyPlannedStoryPoints()
        originally_completed = self.GetOriginallyCompletedStoryPoints()
        
        if originally_planned == 0:
            return 0.0
        
        return ((originally_planned - originally_completed) / originally_planned) * 100
    
    def GetPlatformMetrics(self) -> pd.DataFrame:
        """
        Get comprehensive metrics broken down by platform.
        
        Returns:
            DataFrame with columns: Platform, Completed_Story_Points, Avg_Story_Points,
            Contributors, Avg_Capacity_Per_Contributor, Naive_Scope_Drop, Actual_Scope_Drop
        """
        if self._platform_metrics is not None:
            return self._platform_metrics
        
        platforms = {}
        closed_tasks = self.GetClosedTasks()
        originally_planned_tasks = self.GetOriginallyPlannedTasks()
        
        # Process all tasks to gather platform metrics
        for task in self.tasks:
            platform = task.GetPlatform()
            if not platform:  # Skip empty platforms
                continue
                
            if platform not in platforms:
                platforms[platform] = {
                    'total_planned_points': 0,
                    'completed_points': 0,
                    'originally_planned_points': 0,
                    'originally_completed_points': 0,
                    'completed_items': 0,
                    'contributors': set()
                }
            
            # Add to platform totals
            platforms[platform]['total_planned_points'] += task.GetStoryPoints()
            platforms[platform]['contributors'].add(task.GetAssignee())
            
            # If closed in sprint
            if task in closed_tasks:
                platforms[platform]['completed_points'] += task.GetStoryPoints()
                platforms[platform]['completed_items'] += 1
            
            # If originally planned
            if task in originally_planned_tasks:
                platforms[platform]['originally_planned_points'] += task.GetStoryPoints()
                
                # If originally planned AND closed in sprint
                if task in closed_tasks:
                    platforms[platform]['originally_completed_points'] += task.GetStoryPoints()
        
        # Convert to DataFrame format
        platform_data = []
        for platform, metrics in platforms.items():
            # Calculate derived metrics
            avg_story_points = (metrics['completed_points'] / metrics['completed_items'] 
                              if metrics['completed_items'] > 0 else 0)
            
            contributors_count = len(metrics['contributors'])
            
            # Calculate full-time contributors for this platform (≥5 SP)
            platform_tasks = [task for task in self.tasks if task.GetPlatform() == platform]
            platform_contributor_points = {}
            
            for task in platform_tasks:
                if task in closed_tasks:
                    contributor = task.GetAssignee()
                    if contributor:
                        if contributor not in platform_contributor_points:
                            platform_contributor_points[contributor] = 0
                        platform_contributor_points[contributor] += task.GetStoryPoints()
            
            full_time_contributors_count = sum(1 for points in platform_contributor_points.values() if points >= 5.0)
            
            avg_capacity_per_contributor = (metrics['completed_points'] / full_time_contributors_count 
                                          if full_time_contributors_count > 0 else 0)
            
            # Calculate scope drops
            naive_scope_drop = ((metrics['total_planned_points'] - metrics['completed_points']) / 
                              metrics['total_planned_points'] * 100 
                              if metrics['total_planned_points'] > 0 else 0)
            
            actual_scope_drop = ((metrics['originally_planned_points'] - metrics['originally_completed_points']) / 
                               metrics['originally_planned_points'] * 100 
                               if metrics['originally_planned_points'] > 0 else 0)
            
            platform_data.append({
                'Platform': platform,
                'Completed_Story_Points': round(metrics['completed_points'], 1),
                'Completed_Items': metrics['completed_items'],
                'Avg_Story_Points': round(avg_story_points, 1),
                'Contributors': full_time_contributors_count,  # Only count full-time contributors
                'Avg_Capacity_Per_Contributor': round(avg_capacity_per_contributor, 1),
                'Total_Planned_Story_Points': round(metrics['total_planned_points'], 1),
                'First_Day_Planned_Story_Points': round(metrics['originally_planned_points'], 1),
                'First_Day_Completed_Story_Points': round(metrics['originally_completed_points'], 1),
                'Naive_Scope_Drop': round(naive_scope_drop, 1),
                'Actual_Scope_Drop': round(actual_scope_drop, 1)
            })
        
        self._platform_metrics = pd.DataFrame(platform_data)
        return self._platform_metrics
    
    def GetCapacityByType(self) -> pd.DataFrame:
        """Get capacity breakdown by platform and issue type."""
        capacity_by_type = {}
        closed_tasks = self.GetClosedTasks()
        
        for task in closed_tasks:
            platform = task.GetPlatform()
            issue_type = task.GetIssueType()
            key = (platform, issue_type)
            
            if key not in capacity_by_type:
                capacity_by_type[key] = 0
            capacity_by_type[key] += task.GetStoryPoints()
        
        # Convert to DataFrame
        capacity_list = []
        for (platform, issue_type), story_points in capacity_by_type.items():
            capacity_list.append({
                'Platform': platform,
                'Issue_Type': issue_type,
                'Story_Points': round(story_points, 1)
            })
        
        return pd.DataFrame(capacity_list)
    
    def GetAICapacity(self) -> float:
        """
        Get total capacity (story points) for all closed issues with 'vibe-codable' label.
        
        Returns:
            float: Total story points of closed tasks that have the 'vibe-codable' label
        """
        closed_tasks = self.GetClosedTasks()
        ai_capacity = 0.0
        
        for task in closed_tasks:
            # Check if the task has the 'vibe-codable' label
            if task.HasLabel('vibe-codable'):
                ai_capacity += task.GetStoryPoints()
        
        return round(ai_capacity, 1)
    
    def GetPlatformLabelMetrics(self, platform: str) -> pd.DataFrame:
        """
        Get comprehensive metrics broken down by labels for a specific platform.
        
        Args:
            platform: The platform to analyze (e.g., 'Backend', 'DA', 'DS')
            
        Returns:
            DataFrame with columns: Label, Completed_Story_Points, Avg_Story_Points,
            Contributors, Avg_Capacity_Per_Contributor, Naive_Scope_Drop, Actual_Scope_Drop
        """
        # Filter tasks for the specified platform
        platform_tasks = [task for task in self.tasks if task.GetPlatform() == platform]
        
        if not platform_tasks:
            return pd.DataFrame()  # Return empty DataFrame if no tasks for this platform
        
        labels = {}
        closed_tasks = self.GetClosedTasks()
        originally_planned_tasks = self.GetOriginallyPlannedTasks()
        
        # Process all platform tasks to gather label metrics
        for task in platform_tasks:
            task_labels = task.GetLabels()
            if not task_labels:  # Skip tasks with no labels
                task_labels = ['No Label']
                
            # For each label on this task, add the task's metrics to that label
            for label in task_labels:
                if label not in labels:
                    labels[label] = {
                        'total_planned_points': 0,
                        'completed_points': 0,
                        'originally_planned_points': 0,
                        'originally_completed_points': 0,
                        'completed_items': 0,
                        'contributors': set()
                    }
                
                # Add to label totals
                labels[label]['total_planned_points'] += task.GetStoryPoints()
                labels[label]['contributors'].add(task.GetAssignee())
                
                # If closed in sprint
                if task in closed_tasks:
                    labels[label]['completed_points'] += task.GetStoryPoints()
                    labels[label]['completed_items'] += 1
                
                # If originally planned
                if task in originally_planned_tasks:
                    labels[label]['originally_planned_points'] += task.GetStoryPoints()
                    
                    # If originally planned AND closed in sprint
                    if task in closed_tasks:
                        labels[label]['originally_completed_points'] += task.GetStoryPoints()
        
        # Convert to DataFrame format
        label_data = []
        for label, metrics in labels.items():
            # Calculate derived metrics
            avg_story_points = (metrics['completed_points'] / metrics['completed_items'] 
                              if metrics['completed_items'] > 0 else 0)
            
            contributors_count = len(metrics['contributors'])
            
            # Calculate full-time contributors for this label (≥5 SP)
            label_tasks = [task for task in platform_tasks if task.HasLabel(label)]
            label_contributor_points = {}
            
            for task in label_tasks:
                if task in closed_tasks:
                    contributor = task.GetAssignee()
                    if contributor:
                        if contributor not in label_contributor_points:
                            label_contributor_points[contributor] = 0
                        label_contributor_points[contributor] += task.GetStoryPoints()
            
            full_time_contributors_count = sum(1 for points in label_contributor_points.values() if points >= 5.0)
            
            avg_capacity_per_contributor = (metrics['completed_points'] / full_time_contributors_count 
                                          if full_time_contributors_count > 0 else 0)
            
            # Calculate scope drops
            naive_scope_drop = ((metrics['total_planned_points'] - metrics['completed_points']) / 
                              metrics['total_planned_points'] * 100 
                              if metrics['total_planned_points'] > 0 else 0)
            
            actual_scope_drop = ((metrics['originally_planned_points'] - metrics['originally_completed_points']) / 
                               metrics['originally_planned_points'] * 100 
                               if metrics['originally_planned_points'] > 0 else 0)
            
            # Only include labels that have meaningful activity (completed points, items, or contributors)
            # This filters out empty "No Label" entries that would show up with all zeros
            if (metrics['completed_points'] > 0 or 
                metrics['completed_items'] > 0 or 
                full_time_contributors_count > 0):
                
                label_data.append({
                    'Label': label,
                    'Completed_Story_Points': round(metrics['completed_points'], 1),
                    'Completed_Items': metrics['completed_items'],
                    'Avg_Story_Points': round(avg_story_points, 1),
                    'Contributors': full_time_contributors_count,  # Only count full-time contributors
                    'Avg_Capacity_Per_Contributor': round(avg_capacity_per_contributor, 1),
                    'Total_Planned_Story_Points': round(metrics['total_planned_points'], 1),
                    'First_Day_Planned_Story_Points': round(metrics['originally_planned_points'], 1),
                    'First_Day_Completed_Story_Points': round(metrics['originally_completed_points'], 1),
                    'Naive_Scope_Drop': round(naive_scope_drop, 1),
                    'Actual_Scope_Drop': round(actual_scope_drop, 1)
                })
        
        return pd.DataFrame(label_data)
    
    def GetPlatformLabelContributorBreakdown(self, platform: str, label: str) -> pd.DataFrame:
        """
        Get contributor breakdown for a specific platform and label.
        
        Args:
            platform: The platform to analyze (e.g., 'Backend', 'DA', 'DS')
            label: The specific label to analyze (e.g., 'team_reliability', 'team_buffer')
            
        Returns:
            DataFrame with columns: Contributor, Completed_Story_Points, Completed_Items, Avg_Story_Points
        """
        # Filter tasks for the specified platform and label
        platform_label_tasks = [
            task for task in self.tasks 
            if task.GetPlatform() == platform and task.HasLabel(label)
        ]
        
        if not platform_label_tasks:
            return pd.DataFrame()  # Return empty DataFrame if no tasks
        
        contributors = {}
        closed_tasks = self.GetClosedTasks()
        
        # Process tasks to gather contributor metrics
        for task in platform_label_tasks:
            contributor = task.GetAssignee()
            if not contributor:  # Skip empty assignees
                contributor = 'Unassigned'
                
            if contributor not in contributors:
                contributors[contributor] = {
                    'completed_points': 0,
                    'completed_items': 0,
                    'total_items': 0
                }
            
            # Count all items for this contributor
            contributors[contributor]['total_items'] += 1
            
            # If closed in sprint, count towards completion
            if task in closed_tasks:
                contributors[contributor]['completed_points'] += task.GetStoryPoints()
                contributors[contributor]['completed_items'] += 1
        
        # Convert to DataFrame format
        contributor_data = []
        for contributor, metrics in contributors.items():
            avg_story_points = (metrics['completed_points'] / metrics['completed_items'] 
                              if metrics['completed_items'] > 0 else 0)
            
            contributor_data.append({
                'Contributor': contributor,
                'Completed_Story_Points': round(metrics['completed_points'], 1),
                'Completed_Items': metrics['completed_items'],
                'Total_Items': metrics['total_items'],
                'Avg_Story_Points': round(avg_story_points, 1)
            })
        
        # Sort by completed story points descending
        contributor_df = pd.DataFrame(contributor_data)
        if not contributor_df.empty:
            contributor_df = contributor_df.sort_values('Completed_Story_Points', ascending=False)
        
        return contributor_df
    
    def GetPlatformContributorBreakdown(self, platform: str) -> pd.DataFrame:
        """
        Get contributor breakdown for a specific platform.
        
        Args:
            platform: The platform to analyze (e.g., 'Backend', 'DA', 'DS')
            
        Returns:
            DataFrame with columns: Contributor, Completed_Story_Points, Completed_Items, Total_Items, Avg_Story_Points
        """
        # Filter tasks for the specified platform
        platform_tasks = [
            task for task in self.tasks 
            if task.GetPlatform() == platform
        ]
        
        if not platform_tasks:
            return pd.DataFrame()  # Return empty DataFrame if no tasks
        
        contributors = {}
        closed_tasks = self.GetClosedTasks()
        
        # Process tasks to gather contributor metrics
        for task in platform_tasks:
            contributor = task.GetAssignee()
            if not contributor:  # Skip empty assignees
                contributor = 'Unassigned'
                
            if contributor not in contributors:
                contributors[contributor] = {
                    'completed_points': 0,
                    'completed_items': 0,
                    'total_items': 0
                }
            
            # Count all items for this contributor
            contributors[contributor]['total_items'] += 1
            
            # If closed in sprint, count towards completion
            if task in closed_tasks:
                contributors[contributor]['completed_points'] += task.GetStoryPoints()
                contributors[contributor]['completed_items'] += 1
        
        # Convert to DataFrame format
        contributor_data = []
        for contributor, metrics in contributors.items():
            avg_story_points = (metrics['completed_points'] / metrics['completed_items'] 
                              if metrics['completed_items'] > 0 else 0)
            
            contributor_data.append({
                'Contributor': contributor,
                'Completed_Story_Points': round(metrics['completed_points'], 1),
                'Completed_Items': metrics['completed_items'],
                'Total_Items': metrics['total_items'],
                'Avg_Story_Points': round(avg_story_points, 1)
            })
        
        # Sort by completed story points descending
        contributor_df = pd.DataFrame(contributor_data)
        if not contributor_df.empty:
            contributor_df = contributor_df.sort_values('Completed_Story_Points', ascending=False)
        
        return contributor_df
    
    def GetClosedTasksAsDataFrame(self) -> pd.DataFrame:
        """Get closed tasks as DataFrame for compatibility with existing UI code."""
        closed_tasks = self.GetClosedTasks()
        
        closed_data = []
        for task in closed_tasks:
            closed_data.append({
                'Platform': task.GetPlatform(),
                'Story_Points': task.GetStoryPoints(),
                'Issue_Type': task.GetIssueType(),
                'Assignee': task.GetAssignee(),
                'Summary': task.summary,
                'Status': task.status,
                'Status_Category': task.status_category
            })
        
        return pd.DataFrame(closed_data)
    
    def GetSummary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of all sprint metrics.
        
        Returns:
            Dictionary with all key sprint metrics for easy display
        """
        return {
            'sprint_period': f"{self.start_date.strftime('%d %b %Y')} → {self.end_date.strftime('%d %b %Y')}",
            'total_tasks': len(self.tasks),
            'active_platforms': len(self.GetActivePlatforms()),
            'platforms': self.GetActivePlatforms(),
            'total_completed': self.GetTotalCompletedStoryPoints(),
            'total_planned': self.GetTotalPlannedStoryPoints(),
            'originally_planned': self.GetOriginallyPlannedStoryPoints(),
            'originally_completed': self.GetOriginallyCompletedStoryPoints(),
            'ai_capacity': self.GetAICapacity(),
            'naive_scope_drop': round(self.GetNaiveScopeDrop(), 1),
            'actual_scope_drop': round(self.GetActualScopeDrop(), 1),
            'completed_items': self.GetCompletedItems(),
            'total_contributors': self.GetTotalContributors(),
            'full_time_contributors': self.GetFullTimeContributorsCount(),
            'avg_capacity_per_contributor': round(self.GetAverageCapacityPerContributor(), 1),
            'avg_story_points_per_item': round(self.GetAverageStoryPointsPerItem(), 1)
        }
    
    def __str__(self) -> str:
        """String representation of the sprint."""
        return f"Sprint({self.start_date} to {self.end_date}, {len(self.tasks)} tasks, {len(self.GetActivePlatforms())} platforms)"
    
    def __repr__(self) -> str:
        """Developer representation of the sprint."""
        return f"Sprint(start={self.start_date}, end={self.end_date}, tasks={len(self.tasks)}, platforms={self.GetActivePlatforms()})"
