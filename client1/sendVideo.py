
import time
import cv2
import imagezmq
import traceback
import simplejpeg
import random
import socket
import multiprocessing as mp
from threading import Thread

class Frame_Thread(Thread):
    def __init__(self, rpi_name):
        ''' Constructor. '''
        Thread.__init__(self)
        self.rpi_name = rpi_name
        
    def run(self):
        print("start queue read frame")
        mp.set_start_method('fork',True)
        process = mp.Process(target=send_video,args=(self.rpi_name,))
        process.daemon = True
        process.start()


def send_video(rpi_name):
    # capture=cv2.VideoCapture('/dev/video0') # 获取摄像头视频
    capture=cv2.VideoCapture('./pedestrian.mp4')
    capture.set(3,640) # set Width
    capture.set(4,480)
    # capture=cv2.VideoCapture(r"D:\project\dataset\video\测试.mp4")
    # 192.168.100.104 为发送端主机ip地址
    sender = imagezmq.ImageSender(connect_to='tcp://192.168.137.125:5555', REQ_REP=False)

    time.sleep(2.0)  
    jpeg_quality = 95   #调整图片压缩质量，95%
    while(True):
        try:
            ref, frame=capture.read()
            time.sleep(1/60)
            imgID = "image-" + time.strftime("%Y%m%d%H%M%S") + str(random.randint(0,9)) + '.jpg'
            # cv2.imwrite(imgID, frame)
            # image = cv2.resize(frame,(1280,720))
            image = frame
            curtime = time.time()
            msg = rpi_name+'*'+str(curtime)
            # 通过simplejpeg函数将图片编码为jpeg格式，提高传输效率
            jpg_buffer = simplejpeg.encode_jpeg(image, quality=jpeg_quality,
                                                colorspace='BGR')
            sender.send_jpg(msg, jpg_buffer)
            # cv2.imshow(rpi_name, image)
            # cv2.waitKey(1)
        except:
            print(traceback.print_exc())
            break

if __name__ == '__main__':
    rpi_name = socket.gethostname()
    print(rpi_name)
    send_video(rpi_name)