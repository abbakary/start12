import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

try:
    from tracker.utils.chart_utils import generate_monthly_trend_chart
    print("Successfully imported generate_monthly_trend_chart from tracker.utils.chart_utils")
    print(f"Function: {generate_monthly_trend_chart}")
except ImportError as e:
    print(f"Error importing: {e}")
    print("Current Python path:")
    for p in sys.path:
        print(f"  {p}")
    
    print("\nContents of tracker/utils directory:")
    utils_path = os.path.join(os.path.dirname(__file__), 'tracker', 'utils')
    if os.path.exists(utils_path):
        for f in os.listdir(utils_path):
            print(f"  {f}")
    else:
        print(f"Directory not found: {utils_path}")
