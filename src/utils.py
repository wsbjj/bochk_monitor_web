"""
Utility functions.
"""
import time
from tqdm import tqdm


def sleep_display(seconds):
    """
    Sleep for specified seconds with progress bar display.
    
    Args:
        seconds: Number of seconds to sleep
    """
    for _ in tqdm(range(0, seconds)):
        time.sleep(1)


# Backward compatibility alias
sleepDisplay = sleep_display
