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
# IOTCORE_TOPIC_PUB = 'IotCore/MyClientDevice-raspberrypi1/hello/world'
TIMEOUT = 10

# VIDEO_PATH = './video/pedestrian.mp4'
VIDEO_PATH = '/home/ggc_user/project2Congfig/pedestrian.mp4'
RESULT_PATH = './out/result.mp4'

DEEPSORT_CONFIG_PATH = "/home/ggc_user/project2Congfig/deep_sort.yaml"
# DEEPSORT_CONFIG_PATH = "./deep_sort/configs/deep_sort.yaml"
# YOLOV5_WEIGHT_PATH = './weights/yolov5s.pt'
YOLOV5_WEIGHT_PATH = '/home/ggc_user/project2Congfig/yolov5s.pt'

class Frame_Thread1(Thread):
    def __init__(self):
        ''' Constructor. '''
        Thread.__init__(self)
        
    def run(self):
        print("start queue get frame")
        mp.set_start_method('fork',True)
        process = mp.Process(target=get_video,args=(queue, 1,  ))
        process.daemon = True
        process.start()

class Frame_Thread2(Thread):
    def __init__(self):
        ''' Constructor. '''
        Thread.__init__(self)
        
    def run(self):
        print("start queue get frame")
        mp.set_start_method('fork',True)
        process = mp.Process(target=get_video,args=(queue, 2,  ))
        process.daemon = True
        process.start()

def get_video(q, thread_num):
    if thread_num == 2:
        image_hub = imagezmq.ImageHub(open_port='tcp://192.168.137.131:5555',REQ_REP=False)
    else:
        image_hub = imagezmq.ImageHub(open_port='tcp://192.168.137.125:5555',REQ_REP=False)
    
    # image_hub = imagezmq.ImageHub(open_port='tcp://192.168.137.125:5555',REQ_REP=False)
    # frame_count = 1
    # time1 = 0
    # cap = cv2.VideoCapture(VIDEO_PATH)
    # fps = int(cap.get(5))
    while True:
    # while frame_count == 1:
        try:
            print('start receive images')
            # time1 = time.time() if frame_count == 1 else time1
            name, image = image_hub.recv_jpg()
            # # 解码
            frm = simplejpeg.decode_jpeg(image, colorspace='BGR')
            pack = (name, frm)
            # # cv2.imshow(name.split('*')[0], image)
            # # cv2.waitKey(1)
            # time2 = time.time()
            # print('where is my pic?')
            # # print(image)
            # print(image.shape[:2], int(frame_count/(time2-time1)))
            # frame_count += 1
            # st = time.time()
            # ret,frm = cap.read()
            # if not(ret):
            #     cap.release()
            #     cap = cv2.VideoCapture(VIDEO_PATH)
            #     #cap = cv2.VideoCapture("rtsp://localhost:8554/unicast")
            #     print("total time lost due to reinitialization : ",time.time()-st)
            #     continue
            q.put(pack)
            # if q.qsize() > 1:
            #     for i in range(q.qsize()-1):
            #         q.get()
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

def count(bboxes, name):
    vehicle = 0
    human = 0
    for (x1, y1, x2, y2, cls_id, pos_id) in bboxes:
        if cls_id > 0:
            vehicle += 1
            if name == "raspberrypi1":
                ids_vihecle1.add(str(cls_id) + str(pos_id))
            elif name == "raspberrypi2":
                ids_vihecle2.add(str(cls_id) + str(pos_id))
        else:
            human += 1
            if name == "raspberrypi1":
                ids_human1.add(pos_id)
            elif name == "raspberrypi2":
                ids_human2.add(pos_id)
    return vehicle, human

queue = mp.Queue(maxsize=10)
frame_thread1=Frame_Thread1()
frame_thread1.start()
frame_thread2=Frame_Thread2()
frame_thread2.start()
ids_vihecle1 = set()
ids_human1 = set()
ids_vihecle2 = set()
ids_human2 = set()

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
        name, frame = queue.get()
        # if not _: break
        name = name[0:12]
        print(name)
        
        result = det.update(frame)
        frame = result['frame']
        bboxes = result['obj_bboxes']
        vihicle, human = count(bboxes, name)
        frame = imutils.resize(frame, height=500)

        IOTCORE_TOPIC_PUB = 'IotCore/MyClientDevice-raspberrypi1/hello/world'
        if name == "raspberrypi1" :
            IOTCORE_TOPIC_PUB = 'IotCore/MyClientDevice-raspberrypi1/hello/world'
            message = {}
            message['from'] = "The image is from " + name + "."
            message['vihicle'] = "The current number of vehicles is:" + str(vihicle)
            message['vihicle_flow'] = "The current traffic flow is:" + str(len(ids_vihecle1))
            message['person'] = "The current number of pedestrians is:" + str(human)
            message['person_flow'] = "The current flow of pedestrians is:" + str(len(ids_human1))
            message['sequence'] = loop_count
        elif name == "raspberrypi2" :
            IOTCORE_TOPIC_PUB = 'IotCore/MyClientDevice-raspberrypi2/hello/world'
            message = {}
            message['from'] = "The image is from " + name + "."
            message['vihicle'] = "The current number of vehicles is:" + str(vihicle)
            message['vihicle_flow'] = "The current traffic flow is:" + str(len(ids_vihecle2))
            message['person'] = "The current number of pedestrians is:" + str(human)
            message['person_flow'] = "The current flow of pedestrians is:" + str(len(ids_human2))
            message['sequence'] = loop_count

        messageJson = json.dumps(message)
        print(message)
        
        res = publish_binary_message_to_topic(ipc_clientV2, IOTCORE_TOPIC_PUB, messageJson)
        loop_count += 1
        time.sleep(0.1)
    

except Exception:
    print('Exception occurred when using IPC subsciption.', file=sys.stderr)
    traceback.print_exc()
    exit(1)