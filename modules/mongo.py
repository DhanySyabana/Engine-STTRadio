import pymongo
from datetime import datetime

from custom_types.engine import TranskripStatus
client = pymongo.MongoClient('10.10.10.32', 27018)
db = client.stt
def addNewWatchLog(dt: datetime, channel, startTime: datetime, tries = 0):
    return db.watch_log.insert_one({
            "time"  : dt,
            "channel": channel,
            "status" : "STARTED",
            "starttime": startTime,
            "tries": tries
        }).inserted_id

def updateWatchLogStatus(id, status, error = None, tries = None):
    update = {'status': status}
    if status =='COMPLETED' or status == 'FAILED':
        update["endtime"] = datetime.now()
    if error is not None:
        update["error"] = error
    update['tries'] = tries if tries is not None else 0
    print('update : ', update)
    return db.watch_log.update_one(
            {
                '_id' : id    
            }, 
            {
                '$set': update
            }
            )
def getLastProcessedAudio(channel):
    return db.watch_log.find_one({'channel': channel}, sort=[('starttime', -1)])

def SaveResults(result: str , channel: str, channelAlias: str, time: datetime):                                                                                                               
    # print("Saving {} tweets to database...".format(len(tweets)))                                                                                        
    return db['result_stt'].insert_one(
            {
                'result' : result,
                'channel': channel,
                'channelAlias': channelAlias,
                'time': time
            })                                                                                                                                                

def save_audio_chunk(nama_audio: str, total_chunk: int, current_chunk: int, detik_awal: int, detik_akhir: int, result: str, status: TranskripStatus, verbose: bool = False):
    return db['stt_chunk'].insert_one(
            {
                'nama_audio': nama_audio,
                'current_chunk': current_chunk,
                'total_chunk': total_chunk,
                'detik_awal': detik_awal,
                'detik_akhir': detik_akhir,
                'result': result,
                'status': status.name
            }
            )
def save_audio(nama_audio: str, result:str, status: TranskripStatus, progress_transkrip: float, verbose: bool = False):
    return db['stt_audio'].insert_one(
            {
                'nama_audio': nama_audio,
                'result': result,
                'status': status.name,
                'progress_transkrip': progress_transkrip

            }
            )


