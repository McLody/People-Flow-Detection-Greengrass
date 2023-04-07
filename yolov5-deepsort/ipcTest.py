import sys
import time
import traceback
import os
import imagezmq
import traceback
import time
import simplejpeg
import json
import multiprocessing as mp
from threading import Thread

from shells.shell import Shell
import imutils
import cv2

import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
import awsiot.greengrasscoreipc.model as model
from awsiot.greengrasscoreipc.model import (
    PublishMessage,
    BinaryMessage,
    PublishToTopicRequest
)

# CLIENT_DEVICE_HELLO_WORLD_TOPIC = 'clients/+/hello/world'
CLIENT_TOPIC = 'clients/+/hello/world'
IOTCORE_TOPIC_PUB = 'IotCore/MyClientDevice-raspberrypi1/hello/world'
TIMEOUT = 10

# VIDEO_PATH = './video/pedestrian.mp4'
VIDEO_PATH = '/home/ggc_user/project2Congfig/pedestrian.mp4'
RESULT_PATH = './out/result.mp4'

# DEEPSORT_CONFIG_PATH = "/home/ggc_user/project2Congfig/deep_sort.yaml"
DEEPSORT_CONFIG_PATH = "./deep_sort/configs/deep_sort.yaml"
# YOLOV5_WEIGHT_PATH = './weights/yolov5s.pt'
YOLOV5_WEIGHT_PATH = '/home/ggc_user/project2Congfig/yolov5s.pt'

class Frame_Thread(Thread):
    def __init__(self):
        ''' Constructor. '''
        Thread.__init__(self)
        
    def run(self):
        print("start queue get frame")
        mp.set_start_method('fork',True)
        process = mp.Process(target=get_video,args=(queue, ))
        process.daemon = True
        process.start()

def get_video(q):
    # image_hub = imagezmq.ImageHub(open_port='tcp://192.168.137.58:5555',REQ_REP=False)
    # frame_count = 1
    # time1 = 0
    cap = cv2.VideoCapture(VIDEO_PATH)
    # fps = int(cap.get(5))
    while True:
    # while frame_count == 1:
        try:
            # print('ready')
            # time1 = time.time() if frame_count == 1 else time1
            # name, image = image_hub.recv_jpg()
            # # 解码
            # image = simplejpeg.decode_jpeg(image, colorspace='BGR')
            # # cv2.imshow(name.split('*')[0], image)
            # # cv2.waitKey(1)
            # time2 = time.time()
            # print('where is my pic?')
            # # print(image)
            # print(image.shape[:2], int(frame_count/(time2-time1)))
            # frame_count += 1
            st = time.time()
            ret,frm = cap.read()
            if not(ret):
                cap.release()
                cap = cv2.VideoCapture(VIDEO_PATH)
                #cap = cv2.VideoCapture("rtsp://localhost:8554/unicast")
                print("total time lost due to reinitialization : ",time.time()-st)
                continue
            q.put(frm)
            if q.qsize() > 1:
                for i in range(q.qsize()-1):
                    q.get()
        except:
            print(traceback.format_exc())
            break

def on_hello_world_message(event):
    try:
        message = str(event.binary_message.message, 'utf-8')
        print('Received new message: %s' % message)
    except:
        traceback.print_exc()

def publish_binary_message_to_topic(ipc_client, topic, message):
    binary_message = BinaryMessage(message=bytes(message, 'utf-8'))
    publish_message = PublishMessage(binary_message=binary_message)
    return ipc_client.publish_to_topic(topic=topic, publish_message=publish_message)

def count(bboxes):
    vehicle = 0
    human = 0
    for (x1, y1, x2, y2, cls_id, pos_id) in bboxes:
        if cls_id > 0:
            vehicle += 1
            ids_vihecle.add(pos_id)
        else:
            human += 1
            ids_human.add(pos_id)
    return vehicle, human

queue = mp.Queue(maxsize=4)
frame_thread=Frame_Thread()
frame_thread.start()
ids_vihecle = set()
ids_human = set()

try:
    ipc_clientV2 = GreengrassCoreIPCClientV2()

    # SubscribeToTopic returns a tuple with the response and the operation.
    _, operation = ipc_clientV2.subscribe_to_topic(
        topic=CLIENT_TOPIC, on_stream_event=on_hello_world_message)
    print('Successfully subscribed to topic: %s' %
          CLIENT_TOPIC)
    det = Shell(DEEPSORT_CONFIG_PATH, YOLOV5_WEIGHT_PATH)
    loop_count = 0
    while True:
        frame = queue.get()
        # if not _: break
        
        result = det.update(frame)
        frame = result['frame']
        bboxes = result['obj_bboxes']
        vihicle, human = count(bboxes)
        frame = imutils.resize(frame, height=500)
        # print(frame)

        message = {}
        message['message'] = "园区内流量如下："
        message['vihicle'] = "当前车辆数为:" + str(vihicle)
        message['vihicle_flow'] = "当前车流量为:" + str(len(ids_vihecle))
        message['person'] = "当前行人数为:" + str(human)
        message['person_flow'] = "当前人流量为:" + str(len(ids_human))
        message['sequence'] = loop_count
        # message['size']
        messageJson = json.dumps(message)
        print(message)
        
        ipc_client = GreengrassCoreIPCClientV2()
        res = publish_binary_message_to_topic(ipc_clientV2, IOTCORE_TOPIC_PUB, messageJson)
        loop_count += 1
        time.sleep(0.1)
    
    

except Exception:
    print('Exception occurred when using IPC subsciption.', file=sys.stderr)
    traceback.print_exc()
    exit(1)