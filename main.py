import requests
import time
from Send_email import send_email
from misc import sleepDisplay
from log import logger


def get_jsonAvailableDateAndTime():
    url = "https://transaction.bochk.com/whk/form/openAccount/jsonAvailableDateAndTime.action"
    payload = "bean.appDate="
    headers = {
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
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()


def parse(res_json, check_dates):
    logger.info(str(res_json))
    dateQuota = res_json["dateQuota"]
    AvailableDate_list = []
    for key in dateQuota:
        # print(key,dateQuota[key])
        if dateQuota[key] != "F" and key in check_dates:
            AvailableDate_list.append(key)
    # #  测试
    # AvailableDate_list.append('202503测试')
    return len(AvailableDate_list), AvailableDate_list


def main(check_dates):
    res_json = get_jsonAvailableDateAndTime()
    AvailableDate_num, AvailableDate_list = parse(res_json, check_dates)
    # print(AvailableDate_num,AvailableDate_list)
    logger.info(str(AvailableDate_num) + str(AvailableDate_list))
    if AvailableDate_num > 0:
        send_email('中银香港可预约', f"中银香港可预约\n日期{str(str(AvailableDate_list))}")
        logger.info(f"中银香港可预约\n日期{str(str(AvailableDate_list))}")


if __name__ == "__main__":
    while True:
        try:
            check_dates = ["20260213", "20260214","20260215"]  # 希望捡漏的日期
            main(check_dates)
        except Exception as e:
            logger.error(str(e))
        sleepDisplay(60)
