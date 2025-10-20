import base64
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from django.utils import timezone
import numpy as np

def generate_monthly_trend_chart(monthly_data, title, width=10, height=6):
    """
    Generate a monthly trend chart from the given data
    
    Args:
        monthly_data: List of dicts with 'month' and 'orders' keys
        title: Chart title
        width: Figure width in inches
        height: Figure height in inches
        
    Returns:
        Base64 encoded PNG image
    """
    if not monthly_data:
        return None
        
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(monthly_data)
    
    # Ensure we have datetime objects
    df['month'] = pd.to_datetime(df['month'])
    
    # Create a complete date range to ensure all months are shown
    date_range = pd.date_range(
        start=df['month'].min(),
        end=df['month'].max(),
        freq='MS'  # Month Start frequency
    )
    
    # Reindex to include all months in the range
    df = df.set_index('month').reindex(date_range).fillna(0).reset_index()
    df = df.rename(columns={'index': 'month'})
    
    # Create the plot
    plt.style.use('seaborn')
    plt.rcParams['font.family'] = 'sans-serif'
    
    fig, ax = plt.subplots(figsize=(width, height))
    
    # Plot the data
    ax.plot(
        df['month'], 
        df['orders'], 
        marker='o', 
        linewidth=2,
        color='#4361ee',
        markersize=8,
        markerfacecolor='white',
        markeredgewidth=2
    )
    
    # Format the x-axis to show month and year
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    
    # Rotate and align the x-axis labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Set labels and title
    ax.set_xlabel('Month', fontsize=12, labelpad=10)
    ax.set_ylabel('Number of Orders', fontsize=12, labelpad=10)
    ax.set_title(title, fontsize=14, pad=20, fontweight='bold')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save to base64 string
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
