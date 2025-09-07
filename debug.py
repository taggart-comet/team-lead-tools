#!/usr/bin/env python3
"""
Debug script to test sprint and task functionality across different datasets.
Allows user to choose a dataset and then either:
1. Display sprint summary
2. Display detailed task information by issue key
"""

import pandas as pd
import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path

# Add the internal directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'internal'))

from jira.task import Task
from jira.sprint import Sprint

def get_available_datasets():
    """Get list of available CSV datasets."""
    datasets_dir = Path("datasets")
    if not datasets_dir.exists():
        print("❌ datasets/ directory not found!")
        return []
    
    csv_files = list(datasets_dir.glob("*.csv"))
    return sorted([f.name for f in csv_files])

def choose_dataset(datasets):
    """Let user choose a dataset from the available options."""
    print("\n📊 AVAILABLE DATASETS:")
    print("=" * 50)
    
    for i, dataset in enumerate(datasets, 1):
        print(f"  {i}. {dataset}")
    
    while True:
        try:
            choice = input(f"\nChoose dataset (1-{len(datasets)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(datasets):
                return datasets[choice_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(datasets)}")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)

def parse_sprint_dates(dataset_name, df):
    """Parse sprint dates from dataset name and/or CSV data."""
    
    # Try to extract from filename pattern (e.g., q3_sprint_5_2025.csv)
    try:
        # Remove .csv extension
        name_parts = dataset_name.replace('.csv', '').split('_')
        if len(name_parts) >= 3:
            year = int(name_parts[-1])  # 2025
            sprint_num = int(name_parts[-2])  # 5
            quarter = name_parts[0].upper()  # Q3
            
            # Estimate sprint dates based on quarter and sprint number
            # Assuming each sprint is 2 weeks and quarters have ~6 sprints
            quarter_num = int(quarter[1])  # Extract number from Q3
            quarter_start_month = (quarter_num - 1) * 3 + 1  # Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct
            
            # Each sprint is ~2 weeks, so sprint N starts at (N-1)*2 weeks into the quarter
            weeks_offset = (sprint_num - 1) * 2
            sprint_start = date(year, quarter_start_month, 1) + timedelta(weeks=weeks_offset)
            sprint_end = sprint_start + timedelta(days=13)  # 2 weeks sprint
            
            return sprint_start, sprint_end
    except (ValueError, IndexError):
        pass
    
    # Fallback: try to extract from CSV data
    try:
        # Look for date columns and use min/max as sprint boundaries
        date_columns = ['Created', 'Updated', 'Status Category Changed', 'Resolved']
        dates = []
        
        for col in date_columns:
            if col in df.columns:
                valid_dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if not valid_dates.empty:
                    dates.extend(valid_dates.tolist())
        
        if dates:
            min_date = min(dates).date()
            max_date = max(dates).date()
            return min_date, max_date
    except Exception:
        pass
    
    # Final fallback: use reasonable defaults
    print("⚠️  Could not determine sprint dates from data, using defaults...")
    return date(2025, 7, 1), date(2025, 7, 14)

def choose_analysis_type():
    """Let user choose between Sprint Summary or Task Summary."""
    print("\n📋 ANALYSIS OPTIONS:")
    print("=" * 50)
    print("  1. Sprint Summary - Overview of entire sprint metrics")
    print("  2. Task Summary - Detailed info for specific task")
    
    while True:
        try:
            choice = input(f"\nChoose analysis type (1-2): ").strip()
            choice_num = int(choice)
            if choice_num == 1:
                return "sprint"
            elif choice_num == 2:
                return "task"
            else:
                print("❌ Please enter 1 or 2")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)

def find_task_by_issue_key(tasks, issue_key):
    """Find a task by its issue key."""
    for task in tasks:
        if task.issue_key.upper() == issue_key.upper():
            return task
    return None

def display_task_summary(task, sprint):
    """Display detailed summary for a specific task."""
    print(f"\n📋 TASK SUMMARY FOR {task.issue_key.upper()}")
    print("=" * 60)
    
    # Basic task info
    print(f"  Issue Key                     : {task.issue_key}")
    print(f"  Summary                       : {task.summary}")
    print(f"  Issue Type                    : {task.issue_type}")
    print(f"  Status                        : {task.status}")
    print(f"  Status Category               : {task.status_category}")
    print(f"  Platform                      : {task.platform}")
    print(f"  Assignee                      : {task.assignee}")
    print(f"  Story Points                  : {task.story_points}")
    
    # Labels
    labels = task.GetLabels()
    if labels:
        print(f"  Labels                        : {', '.join(labels)} ({len(labels)} total)")
        # Test specific label checks
        common_labels = ['team_buffer', 'team_dispatch', 'vibe-codable', 'team_reliability']
        for label in common_labels:
            if task.HasLabel(label):
                print(f"    ✅ Has '{label}' label")
    else:
        print(f"  Labels                        : (none)")
    
    # Dates
    print(f"  Created Date                  : {task.created_date or '(not set)'}")
    print(f"  Updated Date                  : {task.updated_date or '(not set)'}")
    print(f"  Closure Date                  : {task.closure_date or '(not set)'}")
    
    # Sprint-related analysis
    print(f"\n🔍 SPRINT ANALYSIS:")
    print("=" * 60)
    
    is_closed = task.IsClosed(sprint.start_date, sprint.end_date)
    is_originally_planned = task.IsOriginallyPlanned(sprint.start_date)
    
    print(f"  Sprint Period                 : {sprint.start_date} → {sprint.end_date}")
    print(f"  Originally Planned            : {'✅ Yes' if is_originally_planned else '❌ No'}")
    print(f"  Closed in Sprint              : {'✅ Yes' if is_closed else '❌ No'}")
    
    if task.created_date:
        days_before_sprint = (sprint.start_date - task.created_date.date()).days
        if days_before_sprint > 0:
            print(f"  Created before sprint start  : {days_before_sprint} days")
        elif days_before_sprint < 0:
            print(f"  Created after sprint start   : {abs(days_before_sprint)} days")
        else:
            print(f"  Created on sprint start       : same day")
    
    if task.closure_date and is_closed:
        closure_day = (task.closure_date.date() - sprint.start_date).days + 1
        print(f"  Closed on sprint day          : Day {closure_day}")
    
    # AI/automation analysis
    if task.HasLabel('vibe-codable'):
        print(f"  🤖 AI-Codable Task            : ✅ Yes ({task.story_points} SP contributes to AI capacity)")
    else:
        print(f"  🤖 AI-Codable Task            : ❌ No")

def analyze_task_summary(dataset_name, tasks, sprint):
    """Handle task summary analysis workflow."""
    print(f"\n🔍 TASK SEARCH IN {dataset_name.upper()}")
    print("=" * 60)
    
    # Show available issue keys for reference
    issue_keys = [task.issue_key for task in tasks]
    print(f"📝 Available tasks ({len(issue_keys)} total):")
    
    # Group by first few characters for better display
    key_groups = {}
    for key in sorted(issue_keys):
        prefix = key.split('-')[0] if '-' in key else key[:3]
        if prefix not in key_groups:
            key_groups[prefix] = []
        key_groups[prefix].append(key)
    
    for prefix, keys in key_groups.items():
        if len(keys) <= 10:
            print(f"  {prefix}: {', '.join(keys)}")
        else:
            print(f"  {prefix}: {', '.join(keys[:8])} ... and {len(keys)-8} more")
    
    while True:
        try:
            issue_key = input(f"\n🎯 Enter issue key (or 'back' to return): ").strip()
            
            if issue_key.lower() == 'back':
                return False
            
            if not issue_key:
                print("❌ Please enter an issue key")
                continue
            
            # Find the task
            task = find_task_by_issue_key(tasks, issue_key)
            
            if task:
                display_task_summary(task, sprint)
                
                # Ask if user wants to search for another task
                choice = input(f"\n🔍 Search for another task? (y/n): ").strip().lower()
                if choice not in ['y', 'yes']:
                    return True
            else:
                print(f"❌ Task '{issue_key}' not found in dataset")
                print("💡 Make sure you're using the exact issue key (case insensitive)")
                
                # Suggest similar keys
                similar_keys = [key for key in issue_keys if issue_key.upper() in key.upper()]
                if similar_keys:
                    print(f"🔍 Did you mean one of these? {', '.join(similar_keys[:5])}")
                
        except KeyboardInterrupt:
            print("\n👋 Going back...")
            return False

def analyze_sprint_summary(dataset_name, sprint):
    """Display sprint summary analysis."""
    # Get and display summary
    print("🔄 Generating sprint summary...")
    summary = sprint.GetSummary()
    
    print(f"\n📊 SPRINT SUMMARY FOR {dataset_name.upper()}")
    print("=" * 60)
    
    # Format and display summary
    for key, value in summary.items():
        # Format key for display
        display_key = key.replace('_', ' ').title()
        
        # Format value based on type
        if isinstance(value, float):
            if 'percentage' in key or 'scope_drop' in key:
                formatted_value = f"{value}%"
            else:
                formatted_value = f"{value:.1f}"
        elif isinstance(value, list):
            formatted_value = ", ".join(map(str, value))
        else:
            formatted_value = str(value)
        
        print(f"  {display_key:<35}: {formatted_value}")
    
    # Additional insights
    print(f"\n📋 ADDITIONAL INSIGHTS:")
    print("=" * 60)
    
    # Label analysis
    all_labels = set()
    multi_label_tasks = 0
    
    for task in sprint.tasks:
        labels = task.GetLabels()
        all_labels.update(labels)
        if len(labels) > 1:
            multi_label_tasks += 1
    
    print(f"  All unique labels found       : {len(all_labels)}")
    if len(all_labels) <= 10:
        print(f"  Label list                    : {', '.join(sorted(all_labels))}")
    print(f"  Tasks with multiple labels    : {multi_label_tasks}")
    
    # Platform breakdown
    platform_metrics = sprint.GetPlatformMetrics()
    if not platform_metrics.empty:
        print(f"  Active platforms              : {len(platform_metrics)}")
        print("  Platform breakdown:")
        for _, row in platform_metrics.iterrows():
            print(f"    - {row['Platform']:<20}: {row['Completed_Story_Points']} SP, {row['Contributors']} contributors")

def load_and_analyze_dataset(dataset_name, analysis_type):
    """Load dataset and perform the requested analysis."""
    
    print(f"\n🔄 Loading dataset: {dataset_name}")
    print("=" * 50)
    
    try:
        # Load CSV
        df = pd.read_csv(f"datasets/{dataset_name}")
        print(f"✅ Loaded {len(df)} rows from CSV")
        
        # Parse sprint dates
        start_date, end_date = parse_sprint_dates(dataset_name, df)
        print(f"📅 Sprint period: {start_date} → {end_date}")
        
        # Create Task objects
        print("🔄 Creating Task objects...")
        tasks = []
        errors = 0
        
        for index, row in df.iterrows():
            try:
                task = Task(row)
                tasks.append(task)
            except Exception as e:
                errors += 1
                if errors <= 3:  # Only show first 3 errors
                    print(f"   ⚠️  Error in row {index}: {e}")
        
        if errors > 3:
            print(f"   ⚠️  ... and {errors - 3} more errors")
        
        print(f"✅ Created {len(tasks)} Task objects ({errors} errors)")
        
        # Create Sprint object
        print("🔄 Creating Sprint object...")
        sprint = Sprint(tasks, start_date, end_date)
        
        # Perform the requested analysis
        if analysis_type == "sprint":
            analyze_sprint_summary(dataset_name, sprint)
            return True
        elif analysis_type == "task":
            return analyze_task_summary(dataset_name, tasks, sprint)
        else:
            print(f"❌ Unknown analysis type: {analysis_type}")
            return False
        
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the debug script."""
    
    print("🚀 TEAM LEAD TOOLS DEBUGGER")
    print("=" * 50)
    print("This script helps you debug sprint and task functionality")
    print("across different datasets.")
    
    # Get available datasets
    datasets = get_available_datasets()
    
    if not datasets:
        print("❌ No CSV files found in datasets/ directory!")
        return
    
    while True:
        try:
            # Let user choose dataset
            chosen_dataset = choose_dataset(datasets)
            
            # Let user choose analysis type
            analysis_type = choose_analysis_type()
            
            # Load and analyze
            success = load_and_analyze_dataset(chosen_dataset, analysis_type)
            
            if success:
                if analysis_type == "sprint":
                    print(f"\n✅ Sprint summary completed for {chosen_dataset}")
                else:
                    print(f"\n✅ Task analysis completed for {chosen_dataset}")
            
            # Ask if user wants to continue
            print("\n" + "=" * 60)
            choice = input("Continue with another analysis? (y/n): ").strip().lower()
            if choice not in ['y', 'yes']:
                break
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
    
    print("\n🎉 Thanks for using the Team Lead Tools Debugger!")

if __name__ == "__main__":
    main()
