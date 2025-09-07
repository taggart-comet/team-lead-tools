import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import os

# Import our Task and Sprint classes
from internal.jira import Task, Sprint

# Page configuration
st.set_page_config(
    page_title="Sprint Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("📊 Sprint Analytics Dashboard")
st.markdown("---")

def calculate_default_sprint_dates(df):
    """Calculate smart default sprint start and end dates from the data"""
    # Convert Status Category Changed to datetime if it exists
    if 'Status Category Changed' in df.columns:
        # Parse dates from Status Category Changed
        df['Closure_Date'] = pd.to_datetime(df['Status Category Changed'], errors='coerce', format='%d/%b/%y %H:%M')
        
        # Get date range from closed items
        closed_dates = df[df['Status Category'] == 'Done']['Closure_Date'].dropna()
        
        if not closed_dates.empty:
            # Sprint likely spans from a few days before first closure to a few days after last closure
            min_date = closed_dates.min().date()
            max_date = closed_dates.max().date()
            
            # Add some buffer - start 2 days before first closure, end 1 day after last closure
            start_date = min_date - timedelta(days=2)
            end_date = max_date + timedelta(days=1)
            
            return start_date, end_date
    
    # Fallback: use Created dates if Status Category Changed is not available
    if 'Created' in df.columns:
        df['Created_Date'] = pd.to_datetime(df['Created'], errors='coerce')
        created_dates = df['Created_Date'].dropna()
        
        if not created_dates.empty:
            min_date = created_dates.min().date()
            max_date = created_dates.max().date()
            return min_date, max_date
    
    # Ultimate fallback: current date ± 14 days
    today = datetime.now().date()
    return today - timedelta(days=14), today

@st.cache_data
def load_data(filename):
    """Load and preprocess the sprint data"""
    try:
        # Load the CSV file
        df = pd.read_csv(f'datasets/{filename}')
        
        # Clean column names - remove leading/trailing spaces
        df.columns = df.columns.str.strip()
        
        # Find the story points column - it might have different naming
        story_points_cols = [col for col in df.columns if 'Story Points' in col and 'Total' not in col and 'Weekly' not in col]
        if story_points_cols:
            story_points_col = story_points_cols[0]
        else:
            # Fallback to any story points column
            story_points_col = 'Custom field (Story Points)'
        
        # Rename key columns for easier access
        column_mapping = {
            story_points_col: 'Story_Points',
            'Status': 'Status',
            'Platform': 'Platform',
            'Issue Type': 'Issue_Type',
            'Sprint': 'Sprint',
            'Summary': 'Summary',
            'Created': 'Created',
            'Updated': 'Updated',
            'Assignee': 'Assignee'
        }
        
        # Rename columns that exist
        existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=existing_columns)
        
        # Handle custom field platform column if Platform doesn't exist
        if 'Platform' not in df.columns:
            # Look for the main platform column - prioritize 'Custom field (Platform)'
            platform_cols = [col for col in df.columns if 'Platform' in col]
            preferred_platform_col = None
            
            # Prioritize 'Custom field (Platform)' over other platform columns
            for col in platform_cols:
                if col == 'Custom field (Platform)':
                    preferred_platform_col = col
                    break
            
            # If not found, use the first platform column that has actual data
            if not preferred_platform_col and platform_cols:
                for col in platform_cols:
                    if df[col].notna().sum() > 0:
                        preferred_platform_col = col
                        break
            
            if preferred_platform_col:
                df['Platform'] = df[preferred_platform_col]
                print(f"Using platform column: {preferred_platform_col}")
        
        # Convert Story Points to numeric, handling various formats
        if 'Story_Points' in df.columns:
            df['Story_Points'] = pd.to_numeric(df['Story_Points'], errors='coerce')
        else:
            df['Story_Points'] = 0
        
        # Convert dates
        date_columns = ['Created', 'Updated']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Parse Status Category Changed for closure dates
        if 'Status Category Changed' in df.columns:
            df['Closure_Date'] = pd.to_datetime(df['Status Category Changed'], errors='coerce', format='%d/%b/%y %H:%M')
        
        # Filter out rows with missing critical data
        df = df.dropna(subset=['Platform'])
        
        # Standardize platform names
        platform_mapping = {
            'Backend': 'Backend',
            'backend': 'Backend',
            'BE': 'Backend',
            'DataAnalytics': 'DA',
            'Data Analytics': 'DA',
            'DA': 'DA',
            'DataScience': 'DS',
            'Data Science': 'DS',
            'DS': 'DS',
            'Frontend': 'Frontend',
            'FE': 'Frontend',
            'Mobile': 'Mobile',
            'QA': 'QA'
        }
        
        df['Platform'] = df['Platform'].map(platform_mapping).fillna(df['Platform'])
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def calculate_capacity_metrics(df, sprint_start_date, sprint_end_date):
    """Calculate capacity metrics using the Sprint object - much cleaner approach!"""
    
    # Create Task objects from DataFrame rows
    tasks = [Task(row) for idx, row in df.iterrows()]
    
    # Create Sprint object - this encapsulates ALL the business logic!
    sprint = Sprint(tasks, sprint_start_date, sprint_end_date)
    
    # Get all metrics from the Sprint object - so clean and readable!
    capacity_by_platform = sprint.GetPlatformMetrics()
    capacity_by_type = sprint.GetCapacityByType()
    closed_df = sprint.GetClosedTasksAsDataFrame()
    
    return capacity_by_platform, capacity_by_type, closed_df, sprint_start_date, sprint_end_date

def get_available_files():
    """Get list of CSV files in the datasets folder"""
    import os
    datasets_path = Path('datasets')
    if datasets_path.exists():
        csv_files = [f for f in os.listdir(datasets_path) if f.endswith('.csv')]
        return sorted(csv_files)
    return []

def main():
    # Sidebar file selector
    st.sidebar.header("📁 File Selection")
    
    available_files = get_available_files()
    
    if not available_files:
        st.error("No CSV files found in the datasets folder. Please add CSV files to the datasets/ directory.")
        return
    
    # Default to the existing file if it exists, otherwise use the first file
    default_file = 'q3_sprint_2_2025.csv' if 'q3_sprint_2_2025.csv' in available_files else available_files[0]
    
    selected_file = st.sidebar.selectbox(
        "Select Sprint Data File",
        available_files,
        index=available_files.index(default_file) if default_file in available_files else 0,
        help="Choose which sprint CSV file to analyze"
    )
    
    # Display selected file info
    st.sidebar.info(f"📊 Analyzing: **{selected_file}**")
    
    # Load data
    with st.spinner(f"Loading data from {selected_file}..."):
        df = load_data(selected_file)
    
    if df.empty:
        st.error(f"No data loaded from {selected_file}. Please check the CSV file.")
        return
    
    # Calculate default sprint dates
    default_start, default_end = calculate_default_sprint_dates(df)
    
    # Sprint Date Selection
    st.subheader("🎯 Sprint Date Range")
    col1, col2 = st.columns(2)
    
    with col1:
        sprint_start_date = st.date_input(
            "Sprint Start Date",
            value=default_start,
            help="Select the start date of your sprint"
        )
    
    with col2:
        sprint_end_date = st.date_input(
            "Sprint End Date", 
            value=default_end,
            help="Select the end date of your sprint"
        )
    
    # Display selected sprint range
    st.success(f"📅 **Analyzing Sprint**: {sprint_start_date.strftime('%d %b %Y')} → {sprint_end_date.strftime('%d %b %Y')}")
    st.caption("ℹ️ Only tasks with Status Category 'Done' within this date range are counted as 'Closed'")
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Platform filter
    platforms = ['All'] + sorted(df['Platform'].unique().tolist())
    selected_platform = st.sidebar.selectbox("Select Platform", platforms)
    
    # Status filter
    statuses = ['All'] + sorted(df['Status'].unique().tolist())
    selected_status = st.sidebar.selectbox("Select Status", statuses)
    
    # Issue type filter
    issue_types = ['All'] + sorted(df['Issue_Type'].dropna().unique().tolist())
    selected_issue_type = st.sidebar.selectbox("Select Issue Type", issue_types)
    
    # Apply filters
    filtered_df = df.copy()
    if selected_platform != 'All':
        filtered_df = filtered_df[filtered_df['Platform'] == selected_platform]
    if selected_status != 'All':
        filtered_df = filtered_df[filtered_df['Status'] == selected_status]
    if selected_issue_type != 'All':
        filtered_df = filtered_df[filtered_df['Issue_Type'] == selected_issue_type]
    
    # Create Task objects and Sprint - the new clean approach!
    tasks = [Task(row) for idx, row in filtered_df.iterrows()]
    sprint = Sprint(tasks, sprint_start_date, sprint_end_date)
    
    # Get metrics from Sprint object for backward compatibility
    capacity_by_platform = sprint.GetPlatformMetrics()
    
    # Enhanced Metrics Section with Subtle Styling
    st.markdown("""
    <style>
    .metric-card {
        background: #f8f9fa;
        padding: 0.6rem;
        border-radius: 6px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        margin: 0.25rem 0;
        transition: box-shadow 0.2s ease;
        color: #212529;
    }
    
    .metric-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .metric-completed {
        background: #f8f9fa;
        border-left: 4px solid #28a745;
    }
    
    .metric-planned {
        background: #f8f9fa;
        border-left: 4px solid #007bff;
    }
    
    .metric-scope {
        background: #f8f9fa;
        border-left: 4px solid #dc3545;
    }
    
    .metric-title {
        font-size: 0.7rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        margin: 0.1rem 0;
        color: #212529;
    }
    
    .metric-subtitle {
        font-size: 0.65rem;
        color: #6c757d;
        margin-top: 0.1rem;
    }
    
    .metric-icon {
        font-size: 1rem;
        margin-bottom: 0.15rem;
        display: block;
        opacity: 0.7;
    }
    
    .progress-bar {
        width: 100%;
        height: 3px;
        background-color: #e9ecef;
        border-radius: 2px;
        margin-top: 0.4rem;
        overflow: hidden;
    }
    
    .progress-fill {
        height: 100%;
        background-color: #007bff;
        border-radius: 2px;
        transition: width 0.3s ease;
    }
    
    .metric-completed .progress-fill {
        background-color: #28a745;
    }
    
    .metric-planned .progress-fill {
        background-color: #007bff;
    }
    
    .metric-scope .progress-fill {
        background-color: #dc3545;
    }
    
    .metric-ai {
        background: linear-gradient(135deg, #ede9fe 0%, #c4b5fd 100%);
        color: #212529;
        border-left: 4px solid #7c3aed; /* Strong violet */
        box-shadow: 0 3px 12px rgba(124, 58, 237, 0.15);
    }
    
    .metric-ai .metric-title {
        color: #6b21a8;
        font-weight: 700;
    }
    
    .metric-ai .metric-value {
        color: #111827; /* dark gray for visibility */
        text-shadow: none;
    }
    
    .metric-ai .metric-subtitle {
        color: #4b5563; /* soft gray */
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("📈 Key Metrics")
    
    # Calculate metrics
    total_completed = sprint.GetTotalCompletedStoryPoints()
    total_planned = sprint.GetTotalPlannedStoryPoints()
    scope_drop = sprint.GetActualScopeDrop()
    ai_capacity = sprint.GetAICapacity()
    ai_percentage = (ai_capacity / total_completed * 100) if total_completed > 0 else 0
    
    # Calculate completion rate for progress bar
    completion_rate = (total_completed / total_planned * 100) if total_planned > 0 else 0
    completion_rate = min(completion_rate, 100)  # Cap at 100%
    # Color code scope drop: green if low, yellow if medium, red if high
    scope_color = "rgba(255, 255, 255, 0.9)"
    if scope_drop <= 10:
        scope_color = "rgba(56, 239, 125, 0.9)"
    elif scope_drop <= 20:
        scope_color = "rgba(255, 193, 7, 0.9)"
    else:
        scope_color = "rgba(220, 53, 69, 0.9)"
    
    # Create enhanced metric cards in 2x2 layout
    # Top row
    top_col1, top_col2 = st.columns(2)
    
    with top_col1:

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card metric-planned">
                <div class="metric-icon">🎯</div>
                <div class="metric-title">Total Planned</div>
                <div class="metric-value">{total_planned:.0f}</div>
                <div class="metric-subtitle">Story Points</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 100%"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
                            <div class="metric-card metric-completed">
                                <div class="metric-icon">✅</div>
                                <div class="metric-title">Total Completed</div>
                                <div class="metric-value">{total_completed:.0f}</div>
                                <div class="metric-subtitle">Story Points</div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {completion_rate:.1f}%"></div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                    <div class="metric-card metric-scope">
                        <div class="metric-icon">📉</div>
                        <div class="metric-title">Scope Drop</div>
                        <div class="metric-value" style="color: {scope_color};">{scope_drop:.1f}%</div>
                        <div class="metric-subtitle">From Original Plan</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(scope_drop, 100):.1f}%; background-color: {scope_color};"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown(f"""
                <div class="metric-card metric-ai">
                    <div class="metric-icon">🤖</div>
                    <div class="metric-title">AI Coded</div>
                    <div class="metric-value">{ai_percentage:.1f}%</div>
                    <div class="metric-subtitle">{ai_capacity:.1f} Story Points</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {ai_percentage:.1f}%"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with top_col2:
        pass
    

    # Backend Labels Breakdown
    st.header("🔧 Sprint Metrics Backend")

    # Get Backend label metrics
    backend_label_metrics = sprint.GetPlatformLabelMetrics('Backend')
    
    # Filter to only show team labels (labels starting with "team_")
    if not backend_label_metrics.empty:
        backend_label_metrics = backend_label_metrics[
            backend_label_metrics['Label'].str.startswith('team_', na=False)
        ]

    if not backend_label_metrics.empty:
        # Select columns to display for label breakdown
        label_display_columns = [
            'Label',
            'Completed_Story_Points',
            'Avg_Story_Points',
            'Contributors',
            'Avg_Capacity_Per_Contributor',
            'Actual_Scope_Drop'
        ]

        st.dataframe(
            backend_label_metrics[label_display_columns].style.format({
                'Completed_Story_Points': '{:.1f}',
                'Avg_Story_Points': '{:.1f}',
                'Contributors': '{:.0f}',
                'Avg_Capacity_Per_Contributor': '{:.1f}',
                'Actual_Scope_Drop': '{:.1f}%'
            }),
            use_container_width=True
        )
    else:
        st.info("No Backend tasks found with labels in this sprint.")

    # Display capacity table
    st.header("📊 Sprint Metrics by Platform")
    
    # Select columns to display (excluding naive scope drop)
    display_columns = [
        'Platform', 
        'Completed_Story_Points', 
        'Avg_Story_Points', 
        'Contributors', 
        'Avg_Capacity_Per_Contributor', 
        'Actual_Scope_Drop'
    ]
    
    st.dataframe(
        capacity_by_platform[display_columns].style.format({
            'Completed_Story_Points': '{:.1f}',
            'Avg_Story_Points': '{:.1f}',
            'Contributors': '{:.0f}',
            'Avg_Capacity_Per_Contributor': '{:.1f}',
            'Actual_Scope_Drop': '{:.1f}%'
        }),
        use_container_width=True
    )

    # Detailed data view
    st.header("📋 Detailed Data")
    
    # Show filters applied
    st.write(f"**Applied filters:** Platform: {selected_platform}, Status: {selected_status}, Issue Type: {selected_issue_type}")
    st.write(f"**Total records:** {len(filtered_df)}")
    
    # Display filtered data
    display_columns = ['Summary', 'Platform', 'Status', 'Issue_Type', 'Story_Points', 'Assignee', 'Labels', 'Created']
    available_columns = [col for col in display_columns if col in filtered_df.columns]
    
    if available_columns:
        st.dataframe(
            filtered_df[available_columns].head(100),  # Limit to first 100 rows for performance
            use_container_width=True
        )

        # Platform-based Contributor Breakdown (moved outside of Backend-specific section)
        st.header("👥 Contributor Breakdown by Platform")

        # Get available platforms for selection
        available_platforms = sprint.GetActivePlatforms()

        if available_platforms:
            # Platform selection
            selected_platform = st.selectbox(
                "Select a platform to see contributor breakdown:",
                available_platforms,
                help="Choose a platform to see how much each team member contributed"
            )

            if selected_platform:
                # Get contributor breakdown for selected platform
                contributor_breakdown = sprint.GetPlatformContributorBreakdown(selected_platform)

                if not contributor_breakdown.empty:
                    st.write(f"**Contributor breakdown for `{selected_platform}` platform:**")

                    # Display contributor breakdown table
                    st.dataframe(
                        contributor_breakdown.style.format({
                            'Completed_Story_Points': '{:.1f}',
                            'Completed_Items': '{:.0f}',
                            'Total_Items': '{:.0f}',
                            'Avg_Story_Points': '{:.1f}'
                        }),
                        use_container_width=True
                    )

                    # Add some insights
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        total_contributors = len(contributor_breakdown)
                        st.metric("Contributors", f"{total_contributors}")

                    with col2:
                        total_sp = contributor_breakdown['Completed_Story_Points'].sum()
                        st.metric("Total SP", f"{total_sp:.1f}")

                    with col3:
                        avg_sp_per_contributor = total_sp / total_contributors if total_contributors > 0 else 0
                        st.metric("Avg SP/Contributor", f"{avg_sp_per_contributor:.1f}")

                else:
                    st.info(f"No contributor data found for platform '{selected_platform}'.")
        else:
            st.info("No platforms found in this sprint.")

if __name__ == "__main__":
    main() 