from paho.mqtt import publish, subscribe
import threading
import json
import pickle
from datetime import datetime
import time
import random
import socket

hostname = "test.mosquitto.org"

__MAIN_TOPIC = "PGL"
REQUEST_TOPICS = f"{__MAIN_TOPIC}/request/#"
# this is the events that the PI publishes to
REQUEST_STORE_EVENT_IN_DB_TOPIC = f'{__MAIN_TOPIC}/request/store_event'
REQUEST_EMERGENCY_TOPIC = f'{__MAIN_TOPIC}/request/emergency'
# these are the events that the web should request on
REQUEST_STORE_USER_IN_DB_TOPIC = f'{__MAIN_TOPIC}/request/store_user'
REQUEST_CREATE_PRODUCT_TOPIC = f'{__MAIN_TOPIC}/request/store_product'
REQUEST_GET_EVENTS_TOPIC = f'{__MAIN_TOPIC}/request/get_events'
REQUEST_GET_EMERGENCIES_TOPIC = f'{__MAIN_TOPIC}/request/get_emergencies'
REQUEST_VALIDATE_USER_TOPIC = f'{__MAIN_TOPIC}/request/valid_user'
REQUEST_NEW_DEVICE_TOPIC = f'{__MAIN_TOPIC}/request/new_device'
RESPONSE_SEND_EVENTS_TOPIC = f'{__MAIN_TOPIC}/response/send_events'
RESPONSE_VALIDATE_USER_TOPIC = f'{__MAIN_TOPIC}/response/valid_user'
RESPONSE_EMERGENCY_TOPIC = f'{__MAIN_TOPIC}/response/emergency'

user_request = "user1"

# method to create user
def create_user(user, pass_):

    def listen_response():
        while True:
            msg = subscribe.simple(RESPONSE_VALIDATE_USER_TOPIC, hostname=hostname)
            resp = msg.payload.decode("utf-8")
            print(resp)
            exit(0)

    t = threading.Thread(target=listen_response)
    t.start()
    publish.single(REQUEST_STORE_USER_IN_DB_TOPIC, f"{user};{pass_};user;", hostname=hostname)
    # time.sleep(2)
    t.join()


# method to create admin
def create_admin(user, pass_):
    publish.single(REQUEST_STORE_USER_IN_DB_TOPIC, f"{user};{pass_};admin;", hostname=hostname)

# method to create device
def create_device(device):
    publish.single(REQUEST_NEW_DEVICE_TOPIC, f"{device}", hostname=hostname)

# method to create product
def create_product(device, user):
    publish.single(REQUEST_CREATE_PRODUCT_TOPIC, f"{device};{user};", hostname=hostname)

# method to create event
def create_event(device):
    now = datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    r = random.randint(0, 10000)
    t = random.randint(0, 3000)
    publish.single(REQUEST_STORE_EVENT_IN_DB_TOPIC, f"{date_time};{r};{t};{device};", hostname=hostname)

# method to create emergency
def create_emergency(device):
    now = datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    time_passed = random.randint(0, 10000)
    publish.single(REQUEST_EMERGENCY_TOPIC, f"{date_time};{time_passed};{device};", hostname=hostname)

# method to get events
def get_events(user):

    def listen_response():
        while True:
            msg = subscribe.simple(RESPONSE_SEND_EVENTS_TOPIC, hostname=hostname)
            data = json.loads(msg.payload)
            with open(f'testfiles/events_{user}.json', 'w') as f:
                json.dump(data, f)
            exit(0)
    
    t = threading.Thread(target=listen_response)
    t.start()
    publish.single(REQUEST_GET_EVENTS_TOPIC, f"{user};", hostname=hostname)
    # time.sleep(2)
    t.join()


# method to get events to user and device
def get_events_to_user_and_device(user, device):

    def listen_response():
        while True:
            msg = subscribe.simple(RESPONSE_SEND_EVENTS_TOPIC, hostname=hostname)
            data = json.loads(msg.payload)
            with open(f'testfiles/events_{device}_{user}.json', 'w') as f:
                json.dump(data, f)
            exit(0)

    t = threading.Thread(target=listen_response)
    t.start()
    publish.single(REQUEST_GET_EVENTS_TOPIC, f"{user};{device};", hostname=hostname)
    # time.sleep(2)
    t.join()

# method to get emergencies
def get_emergencies(user):

    def listen_response():
        while True:
            msg = subscribe.simple(RESPONSE_EMERGENCY_TOPIC, hostname=hostname)
            data = json.loads(msg.payload)
            with open(f'testfiles/emergencies_{user}.json', 'w') as f:
                json.dump(data, f)
            exit(0)

    t = threading.Thread(target=listen_response)
    t.start()
    publish.single(REQUEST_GET_EMERGENCIES_TOPIC, f"{user};", hostname=hostname)
    # time.sleep(2)
    t.join()

# method to get emergenvies to user and device
def get_emergencies_to_user_and_device(user, device):

    def listen_response():
        while True:
            msg = subscribe.simple(RESPONSE_EMERGENCY_TOPIC, hostname=hostname)
            data = json.loads(msg.payload)
            with open(f'testfiles/emergencies_{device}_{user}.json', 'w') as f:
                json.dump(data, f)
            exit(0)

    t = threading.Thread(target=listen_response)
    t.start()
    publish.single(REQUEST_GET_EMERGENCIES_TOPIC, f"{user};{device};", hostname=hostname)
    # time.sleep(2)
    t.join()


# method to validate user
def validate_user(user, pass_):
    def listen_response():
        while True:
            msg = subscribe.simple(RESPONSE_VALIDATE_USER_TOPIC, hostname=hostname)
            resp = msg.payload.decode("utf-8")
            print(resp)
            exit(0)

    t = threading.Thread(target=listen_response)
    t.start()
    publish.single(REQUEST_VALIDATE_USER_TOPIC, f"{user};{pass_};", hostname=hostname)
    # time.sleep(2)
    t.join()


def test_case_1_single_user(user, i : int):
    # create a user
    create_user(user, "pass")
    # validate user
    validate_user(user, "pass")
    # create a device
    create_device(f"device{i}")
    # create a product
    create_product(f"device{i}", user)
    # create 10 events forf device{i}
    for i in range(10):
        create_event(f"device{i}")

    # create 10 emergencies forf device{i}
    for i in range(10):
        create_emergency(f"device{i}")

    # get events
    get_events(user)
    # get events to user and device
    get_events_to_user_and_device(user, f"device{i}")
    # get emergencies
    get_emergencies(user)
    # get emergencies to user and device
    get_emergencies_to_user_and_device(user, f"device{i}")


# create a test script
if __name__ == "__main__":

    # # create another test case with a admin
    # user_request = "admin1"
    # # create a admin
    # create_admin(user_request, "pass")
    # # validate user
    # validate_user(user_request, "pass")
    # # create a device
    # create_device("device2")
    # # create a product
    # create_product("device2", user_request)
    # create_product("device1", user_request)
    # # create 10 events for device2
    # for i in range(10):
    #     create_event("device2")

    # # create 10 emergencies for device2
    # for i in range(10):
    #     create_emergency("device2")
    # # get events
    # get_events(user_request)
    # # get events to user and device
    # get_events_to_user_and_device(user_request, "device2")
    # # get emergencies
    # get_emergencies(user_request)
    # # get emergencies to user and device
    # get_emergencies_to_user_and_device(user_request, "device2")

    # spawn 10 threads to call test_case_1_single_user with different users
    # threads = []
    # for i in range(10):
    #     t = threading.Thread(target=test_case_1_single_user, args=(f"user{i}", i))
    #     t.start()
    #     time.sleep(0.1)
    #     threads.append(t)

    # # wait for all threads to finish
    # for t in threads:
    #     t.join()

    # for i in range(100):
    #     test_case_1_single_user(f"user{i}", i)

    # test_case_1_single_user("user100", 1)

    # create_event("device100")
    create_device("pigeonhost")



