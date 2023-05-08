from paho.mqtt.client import Client as MqttClient, MQTTMessage
from threading import Event, Thread
from queue import Empty, Queue
import warnings

from PGLEventManagerModel import PGLEventManagerModel


class PGLEventManagerController:
    """The controller listens on MQTT topics and differentiates between three different. 
    Handles both incoming data to be stored in the database (model) as well as requests for 
    outgoing data (to the web server (?))"""

    # different MQTT topics
    # READ: Right now we publish on the '__RESPONSE_VALIDATE_TOPIC' topic both when explicitly reque(logging in),
    # and when trying to create a new user (check for duplicates).
    __MAIN_TOPIC = "PGL"
    __REQUEST_TOPICS = f"{__MAIN_TOPIC}/request/#"
    # this is the events that the PI publishes to
    __REQUEST_STORE_EVENT_IN_DB_TOPIC = f'{__MAIN_TOPIC}/request/store_event'
    __REQUEST_EMERGENCY_TOPIC = f'{__MAIN_TOPIC}/request/emergency'

    # these are the events that the web should request on
    __REQUEST_STORE_USER_IN_DB_TOPIC = f'{__MAIN_TOPIC}/request/store_user'
    __REQUEST_CREATE_PRODUCT_TOPIC = f'{__MAIN_TOPIC}/request/store_product'
    __REQUEST_GET_EVENTS_TOPIC = f'{__MAIN_TOPIC}/request/get_events'
    __REQUEST_GET_EMERGENCIES_TOPIC = f'{__MAIN_TOPIC}/request/get_emergencies'
    __REQUEST_VALIDATE_USER_TOPIC = f'{__MAIN_TOPIC}/request/valid_user'
    __REQUEST_NEW_DEVICE_TOPIC = f'{__MAIN_TOPIC}/request/new_device'

    __RESPONSE_SEND_EVENTS_TOPIC = f'{__MAIN_TOPIC}/response/send_events'
    __RESPONSE_VALIDATE_TOPIC = f'{__MAIN_TOPIC}/response/valid'
    __RESPONSE_EMERGENCY_TOPIC = f'{__MAIN_TOPIC}/response/emergency'

    def __init__(self, mqtt_host: str, model: PGLEventManagerModel, mqtt_port: int = 1883) -> None:
        self.__subscriber_thread = Thread(target=self.__worker,
                                          daemon=True)
        self.__stop___worker = Event()
        self.__events_queue = Queue()
        self.__PGLmodel = model

        # mqtt parameters and callback methods
        self.__mqtt_host = mqtt_host
        self.__mqtt_port = mqtt_port
        self.__mqtt_client = MqttClient(reconnect_on_failure=True, protocol=5)
        self.__mqtt_client.on_message = self.__onMessage
        self.__mqtt_client.on_connect = self.__onConnect
        self.__mqtt_client.on_disconnect = self.__onDisconnect

    # connect the model to address and start the subscriber_thread
    def startListening(self) -> None:
        self.__PGLmodel.connectDB()  # connect to database

        self.__mqtt_client.connect(host=self.__mqtt_host,  # connect to mqtt
                                   port=self.__mqtt_port,
                                   clean_start=True)

        self.__mqtt_client.loop_start()  # start loop
        self.__mqtt_client.subscribe(
            self.__REQUEST_TOPICS)  # subscribe to all topics
        self.__subscriber_thread.start()  # start subscriber thread (listens for mqtt)

    # stop subscriber thread and disconnect the model
    def stopListening(self) -> None:

        # Disconnect from MQTT when events queue is empty
        while not self.__events_queue.empty():
            pass

        # stop subscriber thread
        self.__stop___worker.set()
        self.__mqtt_client.loop_stop()                          # stop mqtt loop
        # unsubscribe from all topics
        self.__mqtt_client.unsubscribe(self.__REQUEST_TOPICS)
        self.__mqtt_client.disconnect()                         # disconnect from mqtt

        # Disconnect from the database
        self.__PGLmodel.disconnectDB()

    # callback method that is called when __mqtt_client is connected
    def __onConnect(self, client, userdata, flags, rc, _) -> None:
        print("MQTT client connected")

    # callback method that is called when __mqtt_client is disconnected
    def __onDisconnect(self, client, userdata, rc, _) -> None:
        # publish an empty message to all request topics with retain=True to clear the mqtt queue
        self.__mqtt_client.publish(
            self.__REQUEST_STORE_EVENT_IN_DB_TOPIC, "", retain=True)
        self.__mqtt_client.publish(
            self.__REQUEST_EMERGENCY_TOPIC, "", retain=True)
        self.__mqtt_client.publish(
            self.__REQUEST_STORE_USER_IN_DB_TOPIC, "", retain=True)
        self.__mqtt_client.publish(
            self.__REQUEST_CREATE_PRODUCT_TOPIC, "", retain=True)
        self.__mqtt_client.publish(
            self.__REQUEST_GET_EVENTS_TOPIC, "", retain=True)
        self.__mqtt_client.publish(
            self.__REQUEST_GET_EMERGENCIES_TOPIC, "", retain=True)
        self.__mqtt_client.publish(
            self.__REQUEST_VALIDATE_USER_TOPIC, "", retain=True)
        self.__mqtt_client.publish(
            self.__REQUEST_NEW_DEVICE_TOPIC, "", retain=True)
        print("MQTT client disconnected")

    # callback method that is called whenever a message arrives on a topic that '__mqtt_client' subscribes to
    def __onMessage(self, client, userdata, message: MQTTMessage) -> None:
        if message.payload == b'':
            print("Empty MQTT message received")
        else:
            # put message in queue
            self.__events_queue.put(message)
            print(f'MQTT Message received with payload: {message.payload}')

    # __worker is the method that the __subscriber_thread runs
    # listens for MQTT events
    # empties __events_queue
    def __worker(self) -> None:
        print("Subscriber_thread __worker started")
        while not self.__stop___worker.is_set():
            try:
                # pull message from events queue
                # timeout indicates that we stop trying to dequeue after 1 s
                # throws 'Empty' exception if timeout
                mqtt_message: MQTTMessage = self.__events_queue.get(timeout=1)
            # if queue empty return
            except Empty:
                pass
            # if the pull was succesful, handle the message to corresponding topic
            else:
                try:
                    mqtt_message_topic = mqtt_message.topic
                    match mqtt_message_topic:
                        case self.__REQUEST_NEW_DEVICE_TOPIC:
                            event_string = mqtt_message.payload.decode("utf-8")
                            self.__PGLmodel.storeDevice(event_string)

                        # store journey from PI in database
                        case self.__REQUEST_STORE_EVENT_IN_DB_TOPIC:
                            event_string = mqtt_message.payload.decode("utf-8")
                            self.__PGLmodel.storeJourney(event_string)

                        # store product in database (from web request)
                        # publishes to indicate if product is stored succesfully, either 'VALID' or 'INVALID'
                        case self.__REQUEST_CREATE_PRODUCT_TOPIC:
                            event_string = mqtt_message.payload.decode("utf-8")
                            success, user = self.__PGLmodel.storeProduct(
                                event_string)
                            self.__mqtt_client.publish(
                                f'{self.__RESPONSE_VALIDATE_TOPIC}/{user}/response', success)
                            print(f'Stored product: {success}')

                        # store user in database (from web request)
                        # publishes to indicate if user is stored succesfully, either 'VALID' or 'INVALID'
                        case self.__REQUEST_STORE_USER_IN_DB_TOPIC:
                            event_string = mqtt_message.payload.decode("utf-8")
                            succ, user = self.__PGLmodel.storeUser(
                                event_string)
                            self.__mqtt_client.publish(
                                f'{self.__RESPONSE_VALIDATE_TOPIC}/{user}/response', succ)
                            print(f'Validated user: {succ}')

                        # return all journies from database for given user
                        case self.__REQUEST_GET_EVENTS_TOPIC:
                            # retrieve data from database using the model
                            user = mqtt_message.payload.decode("utf-8")
                            data, user = self.__PGLmodel.getJourneys(user)
                            # publish the data on the proper topic
                            self.__mqtt_client.publish(
                                f"{self.__RESPONSE_SEND_EVENTS_TOPIC}/{user}/response", data)
                            print("Published data")

                        # validate a user
                        case self.__REQUEST_VALIDATE_USER_TOPIC:
                            credentials = mqtt_message.payload.decode("utf-8")
                            validity, user = self.__PGLmodel.validateUser(
                                credentials)
                            self.__mqtt_client.publish(
                                f'{self.__RESPONSE_VALIDATE_TOPIC}/{user}/response', validity)
                            print(f'Validated user: {validity}')

                        # store emergency message in database from pi
                        case self.__REQUEST_EMERGENCY_TOPIC:
                            event_string = mqtt_message.payload.decode("utf-8")
                            self.__PGLmodel.storeEmergency(
                                event_string)

                        # return all emergencies from database for given user
                        case self.__REQUEST_GET_EMERGENCIES_TOPIC:
                            payload = mqtt_message.payload.decode("utf-8")
                            data, user = self.__PGLmodel.getEmergencies(
                                payload)
                            self.__mqtt_client.publish(
                                f'{self.__RESPONSE_EMERGENCY_TOPIC}/{user}/response', data)
                            print("Published emergencies")

                        case _:
                            # not the right topic
                            warnings.warn(
                                f'Message recieved on unkown topic: {mqtt_message.topic}')

                except KeyError:
                    print(f'Error occured in __worker: {KeyError}')
