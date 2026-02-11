import os
from datetime import datetime

def getTimestampFromFilename(name: str) -> datetime | None:
    try:
        x = name[-18:]
        x = x.replace('.mp3', '')
        x = x.split('-')
        year = datetime.now().year
        this_month = datetime.now().month
        month = int(x[0])

        if (this_month == 1 and month == 12):
            return None
        day = int (x[1])
        hour = int(x[2])
        minutes = int (x[3])
        second = int(x[4])

        return datetime(year=year, month=month, day=day, hour=hour, minute=minutes, second=second) 
    except:
        return None



def getNextUnprocessAudio(path: str, lastProcessedTime: datetime) -> tuple[str | None, datetime | None]:
    files = os.listdir(path)
    print(path)
    mp3 = [f for f in files if f.endswith('.mp3')]
    mp3 = [f for f in files if f.count('.mp3') == 1]
    mp3 = [f for f in files if 'converted' not in f]
    timestamps = [ getTimestampFromFilename(v) for v in mp3]
    mp3WithTimestamps = zip(mp3, timestamps)
    mp3WithTimestamps = [ (a,b) for  (a,b) in mp3WithTimestamps if b is not None]
    sorted_by_timestamps = sorted(mp3WithTimestamps, key= lambda x: x[1])
    sorted_by_timestamps = [ x for x in sorted_by_timestamps if x[1] > lastProcessedTime]
    if len(sorted_by_timestamps) == 0:
        return None, None

    return sorted_by_timestamps[0][0], sorted_by_timestamps[0][1]
