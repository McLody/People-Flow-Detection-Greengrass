import basic_discovery as bd
from awscrt.mqtt import QoS
from sendVideo import Frame_Thread
import socket
import json
import time

IOTCORE_TOPIC = 'IotCore/MyClientDevice-raspberrypi2/hello/world'
CLIENT_TOPIC_PUB = 'clients/MyClientDevice-raspberrypi2/hello/world'

def main():
    rpi_name = socket.gethostname() # 获取主机名
    cmdUtils = bd.get_cmdUtils()
    mqtt_connection = bd.get_mqtt_connection(cmdUtils)
    subscribe_future, _ = mqtt_connection.subscribe(IOTCORE_TOPIC, QoS.AT_MOST_ONCE, on_publish)
    subscribe_result = subscribe_future.result()
    message = {}
    message['message'] = 'From raspberrypi2.'
    # message['sequence'] = 'a'
    messageJson = json.dumps(message)
    pub_future, _ = mqtt_connection.publish(CLIENT_TOPIC_PUB, messageJson, QoS.AT_MOST_ONCE)
    pub_future.result()
    frame_thread=Frame_Thread(rpi_name)
    frame_thread.start()

    try:
        while True:
            time.sleep(10)
    except InterruptedError:
        print('Subscribe interrupted.')

    
def on_publish(topic, payload, dup, qos, retain, **kwargs):
    print('Publish received on topic {}'.format(topic))
    print(payload)


if __name__ == '__main__':
    main()