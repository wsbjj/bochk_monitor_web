"""
BOCHK appointment monitoring module.
Core logic for checking appointment availability and sending notifications.
"""
import requests
import time

from .config import load_config
from .send_email import send_email
from .logger import logger
from .utils import sleep_display


# BOCHK API endpoint
BOCHK_API_URL = "https://transaction.bochk.com/whk/form/openAccount/jsonAvailableDateAndTime.action"

BOCHK_HEADERS = {
    'Host': 'transaction.bochk.com',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Origin': 'https://transaction.bochk.com',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63060012)',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://transaction.bochk.com/whk/form/openAccount/continueInput.action',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
}


def get_jsonAvailableDateAndTime():
    """
    Fetch appointment availability data from BOCHK API.
    
    Returns:
        dict: API response containing dateQuota information
    """
    payload = "bean.appDate="
    response = requests.request("POST", BOCHK_API_URL, headers=BOCHK_HEADERS, data=payload)
    return response.json()


def parse(res_json, check_dates):
    """
    Parse API response and find available dates.
    
    Args:
        res_json: API response JSON
        check_dates: List of dates to check (or ["all"] for all available dates)
        
    Returns:
        tuple: (number of available dates, list of available dates)
    """
    logger.info(str(res_json))
    dateQuota = res_json.get("dateQuota", {})
    available_date_list = []
    
    # Support 'all' mode: monitor all available dates
    if "all" in check_dates:
        for key in dateQuota:
            if dateQuota[key] != "F":
                available_date_list.append(key)
    else:
        for key in dateQuota:
            if dateQuota[key] != "F" and key in check_dates:
                available_date_list.append(key)
    
    return len(available_date_list), available_date_list


def run_monitor(check_dates):
    """
    Run a single monitoring cycle.
    
    Args:
        check_dates: List of dates to monitor
    """
    res_json = get_jsonAvailableDateAndTime()
    available_num, available_list = parse(res_json, check_dates)
    
    logger.info(f"Monitor cycle: {available_num} available dates: {available_list}")
    
    if available_num > 0:
        send_email(
            '中银香港可预约',
            f"中银香港可预约\n日期{available_list}"
        )
        logger.info(f"Notification sent for available dates: {available_list}")


def main():
    """Main entry point for standalone monitor (no web UI)."""
    logger.info("Starting BOCHK appointment monitor (no web UI mode)")
    retry_count = 0
    max_retries = 3
    
    while True:
        try:
            # Load configuration
            config = load_config()
            check_dates = config.get("monitor", {}).get("check_dates", [])
            interval_seconds = config.get("monitor", {}).get("interval_seconds", 60)
            
            if not check_dates:
                logger.warning("No check_dates configured, retrying in 60 seconds...")
                sleep_display(60)
                continue
            
            run_monitor(check_dates)
            retry_count = 0  # Reset retry counter on success
            
        except Exception as e:
            logger.error(f"Error during monitoring cycle: {str(e)}")
            retry_count += 1
            
            if retry_count >= max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded, restarting...")
                retry_count = 0
        
        sleep_display(interval_seconds)


if __name__ == "__main__":
    main()
