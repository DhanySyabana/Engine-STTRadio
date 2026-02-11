#!/bin/bash
cd /home/stt/projects/wishper-updated
source /home/stt/projects/wishper-updated/bin/activate
CURRENT_TIME=$(date +%d-%m-%Y-%H:%M-%S)
if ! pgrep -f 'prambors.py' > /dev/null
then
    python /home/stt/projects/wishper-updated/prambors.py
else
    echo "Running"
fi
find /home/stt/projects/wishper-updated/cron/ -type f -mtime +3 -delete
