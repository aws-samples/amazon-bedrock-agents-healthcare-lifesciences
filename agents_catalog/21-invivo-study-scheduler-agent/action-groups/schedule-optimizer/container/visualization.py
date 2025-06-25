"""
Visualization module for in vivo study scheduling.
Creates visualizations of optimized schedules and uploads them to S3.
"""

import io
import os
import logging
import time
import random
from typing import Dict, Any, Optional

import boto3
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import seaborn as sns

# Use Agg backend for non-interactive environments (like Lambda)
matplotlib.use('Agg')

# Configure logging
logger = logging.getLogger(__name__)


def create_visualization(
    schedule: Dict[str, Any],
    visualization_type: str = "bar_chart",
    bucket_name: str = None
) -> str:
    """
    Create a visualization of the optimized schedule and upload to S3.
    
    Args:
        schedule: The optimized schedule result from the optimizer
        visualization_type: Type of visualization to create
        bucket_name: S3 bucket name for storing the visualization
        
    Returns:
        Presigned URL to the visualization
    """
    if not bucket_name:
        logger.warning("No bucket name provided for visualization storage")
        return None
        
    if visualization_type == "heatmap":
        return create_heatmap_visualization(schedule, bucket_name)
    elif visualization_type == "line_chart":
        return create_line_chart_visualization(schedule, bucket_name)
    else:  # Default to bar chart
        return create_bar_chart_visualization(schedule, bucket_name)


def create_bar_chart_visualization(schedule: Dict[str, Any], bucket_name: str) -> str:
    """Create a bar chart visualization of daily animal and study counts."""
    daily_usage = schedule["daily_usage"]
    days = [day["day"] for day in daily_usage]
    animal_counts = [day["animal_count"] for day in daily_usage]
    study_counts = [day["study_count"] for day in daily_usage]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot animal counts
    bars1 = ax1.bar(days, animal_counts, color='skyblue')
    ax1.set_title('Daily Animal Usage')
    ax1.set_xlabel('Day')
    ax1.set_ylabel('Number of Animals')
    ax1.set_xticks(days[::2])  # Show every other day to avoid crowding
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add average line
    avg_animals = schedule["avg_animals_per_day"]
    ax1.axhline(y=avg_animals, color='r', linestyle='-', label=f'Average: {avg_animals:.1f}')
    ax1.legend()
    
    # Plot study counts
    bars2 = ax2.bar(days, study_counts, color='lightgreen')
    ax2.set_title('Daily Study Count')
    ax2.set_xlabel('Day')
    ax2.set_ylabel('Number of Studies')
    ax2.set_xticks(days[::2])  # Show every other day to avoid crowding
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add average line
    avg_studies = schedule["avg_studies_per_day"]
    ax2.axhline(y=avg_studies, color='r', linestyle='-', label=f'Average: {avg_studies:.1f}')
    ax2.legend()
    
    plt.tight_layout()
    
    # Save to temporary file and upload to S3
    return save_and_upload_visualization(fig, "bar_chart", bucket_name)


def create_heatmap_visualization(schedule: Dict[str, Any], bucket_name: str) -> str:
    """Create a heatmap visualization of the schedule."""
    # Extract schedule data
    studies = schedule["schedule"]
    days_in_period = len(schedule["daily_usage"])
    
    # Create a matrix for the heatmap
    # Rows are studies, columns are days
    heatmap_data = np.zeros((len(studies), days_in_period))
    
    # Fill the matrix with animal counts
    for i, study in enumerate(studies):
        start_day = study["assigned_start_day"] - 1  # Convert to 0-indexed
        duration = study["duration_days"]
        animals = study["animals_required"]
        
        for d in range(duration):
            if start_day + d < days_in_period:
                heatmap_data[i, start_day + d] = animals
    
    # Create the heatmap
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Get study IDs for y-axis labels
    study_ids = [study["study_id"] for study in studies]
    
    # Create heatmap
    sns.heatmap(heatmap_data, cmap="YlGnBu", ax=ax, 
                xticklabels=list(range(1, days_in_period + 1, 2)),  # Show every other day
                yticklabels=study_ids,
                cbar_kws={'label': 'Animals Required'})
    
    ax.set_title('Study Schedule Heatmap')
    ax.set_xlabel('Day')
    ax.set_ylabel('Study ID')
    
    plt.tight_layout()
    
    # Save to temporary file and upload to S3
    return save_and_upload_visualization(fig, "heatmap", bucket_name)


def create_line_chart_visualization(schedule: Dict[str, Any], bucket_name: str) -> str:
    """Create a line chart visualization of daily resource usage."""
    daily_usage = schedule["daily_usage"]
    days = [day["day"] for day in daily_usage]
    animal_counts = [day["animal_count"] for day in daily_usage]
    study_counts = [day["study_count"] for day in daily_usage]
    
    # Calculate cumulative animals used
    cumulative_animals = np.cumsum(animal_counts)
    
    # Create figure with two y-axes
    fig, ax1 = plt.subplots(figsize=(12, 8))
    
    # Plot animal counts
    color = 'tab:blue'
    ax1.set_xlabel('Day')
    ax1.set_ylabel('Daily Animal Count', color=color)
    ax1.plot(days, animal_counts, color=color, marker='o', label='Daily Animals')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_xticks(days[::2])  # Show every other day to avoid crowding
    
    # Add average line
    avg_animals = schedule["avg_animals_per_day"]
    ax1.axhline(y=avg_animals, color=color, linestyle='--', alpha=0.7, 
                label=f'Avg Animals: {avg_animals:.1f}')
    
    # Create second y-axis for study counts
    ax2 = ax1.twinx()
    color = 'tab:green'
    ax2.set_ylabel('Study Count', color=color)
    ax2.plot(days, study_counts, color=color, marker='s', label='Daily Studies')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Add average line for studies
    avg_studies = schedule["avg_studies_per_day"]
    ax2.axhline(y=avg_studies, color=color, linestyle='--', alpha=0.7,
                label=f'Avg Studies: {avg_studies:.1f}')
    
    # Add third y-axis for cumulative animals
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.1))  # Offset the right spine
    color = 'tab:red'
    ax3.set_ylabel('Cumulative Animals', color=color)
    ax3.plot(days, cumulative_animals, color=color, marker='^', label='Cumulative Animals')
    ax3.tick_params(axis='y', labelcolor=color)
    
    # Add title and grid
    plt.title('Daily and Cumulative Resource Usage')
    ax1.grid(True, alpha=0.3)
    
    # Add combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(lines1 + lines2 + lines3, labels1 + labels2 + labels3, loc='upper left')
    
    plt.tight_layout()
    
    # Save to temporary file and upload to S3
    return save_and_upload_visualization(fig, "line_chart", bucket_name)


def save_and_upload_visualization(fig, viz_type: str, bucket_name: str) -> str:
    """
    Save visualization to a temporary file and upload to S3.
    
    Args:
        fig: Matplotlib figure object
        viz_type: Type of visualization (for filename)
        bucket_name: S3 bucket name
        
    Returns:
        Presigned URL to the visualization
    """
    try:
        # Generate unique filename using timestamp and random number
        timestamp = int(time.time() * 1000)
        random_id = random.randint(1000, 9999)
        filename = f"{viz_type}_{timestamp}_{random_id}.png"
        file_path = f"/tmp/{filename}"
        s3_key = f"visualizations/{filename}"
        
        # Save figure to temporary file
        plt.savefig(file_path, format='png', dpi=100)
        plt.close(fig)
        logger.info(f"Visualization saved to {file_path}")
        
        # Upload to S3
        s3 = boto3.client('s3')
        logger.info(f"Uploading to S3 bucket: {bucket_name}, key: {s3_key}")
        s3.upload_file(file_path, bucket_name, s3_key, ExtraArgs={"ContentType": "image/png"})
        
        # Generate presigned URL
        presigned_url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": s3_key},
            ExpiresIn=3600  # URL valid for 1 hour
        )
        
        # Clean up temporary file
        os.remove(file_path)
        logger.info("Temporary file deleted")
        
        return presigned_url
        
    except Exception as e:
        logger.error(f"Error creating visualization: {str(e)}")
        return None
