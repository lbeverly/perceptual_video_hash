#!/usr/bin/env python
import os
import subprocess
import sys

# video hashing experiment part 1
# read in videos
# compute hash (outside modules)
# save video and hash


def hash_video(path):
    process = subprocess.Popen(["./phash", path], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    output, errs = process.communicate()
    hash_number = int(output)
    store_hash(path, "phash", hash_number) 

def store_hash(path, hash_type, hash_number):
    with open(path + ".phash", "w") as f:
        f.write(os.path.basename(path) + ":" + hash_type + ":" + str(hash_number))


def hash_directory(path):
    video_list = list(os.listdir(path))
    for v in video_list:
        filepath = os.path.join(path, v)
        hash_video(filepath)
        
if __name__ == '__main__': 
    if len(sys.argv) < 1 or not os.path.isdir(sys.argv[1]): 
        sys.stderr.write("Must specify directory as first argument") 
        sys.exit(1) 
    hash_directory(sys.argv[1])
