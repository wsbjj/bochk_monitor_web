import time

from tqdm import tqdm


def sleepDisplay(s):
    for i in tqdm(range(0, s)): 
        time.sleep(1)