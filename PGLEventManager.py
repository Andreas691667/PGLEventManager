from queue import Empty, Queue
import mysql.connector as mysql
from paho.mqtt.client import Client as MqttClient, MQTTMessage
import warnings
import json
from threading import Event, Thread

import keyboard

class PGLEventManagerModel:
    """Model to store timestamp events in mysql database.
    The model handles all interaction with the database. """

    USERS_TABLE_NAME = "users"
    JOURNEY_TABLE_NAME = "journey"
    PRODUCT_TABLE_NAME = "products"

    USERS_TABLE_DESCRIPTION : str = """users 
                                       (username VARCHAR(320) NOT NULL,
                                        password VARCHAR(255) NOT NULL, 
                                        usertype VARCHAR(30) NOT NULL, 
                                        PRIMARY KEY(username) )"""
    
    JOURNEY_TABLE_DESCRIPTION : str = """ journey 
                                        (journey_id int NOT NULL AUTO_INCREMENT, 
                                        datetime VARCHAR(30) NOT NULL, 
                                        timestamp VARCHAR(30) NOT NULL, 
                                        device int NOT NULL,
                                        PRIMARY KEY (journey_id) )"""
    
    PRODUCTS_TABLE_DESCRIPTION : str = """products 
                                    (product_id int NOT NULL AUTO_INCREMENT,
                                    device  int NOT NULL,
                                    user    VARCHAR(320) NOT NULL,
                                    PRIMARY KEY (product_id),
                                    FOREIGN KEY (user) REFERENCES users(username))"""

    def __init__(self, host, database: str, user: str, password: str) -> None:
        self.__host = host
        self.__database_name = database
        self.__user = user
        self.__password = password
        self.__PGL_db_connection = None

    def connectDB(self) -> None:
        # establish database connection
        try:
            self.__PGL_db_connection = mysql.connect(host = self.__host,
                                                     user = self.__user,
                                                     password = self.__password)
            
            self.__PGL_db_connection.cursor().execute(f"USE {self.__database_name}")
            print("Connected to database succesfully")

        except mysql.Error as err:
            # If the database doesn't exist, then create it.
            if err.errno == mysql.errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist. Will be created.")
                self.createDatabase()
                print(f"Database {self.__database_name} created successfully.")
            else:
                print(f'Failed connecting to database with error: {err}')

    # disconnect from the database
    def disconnectDB(self) -> None:
        self.__PGL_db_connection.disconnect()
        print("Disconnected from database")

    # creates database with parameters from __init__
    def createDatabase(self) -> None:
        cursor = self.__PGL_db_connection.cursor()

        try:
            cursor.execute(f"CREATE DATABASE {self.__database_name} DEFAULT CHARACTER SET 'utf8'")  #create database
        except mysql.Error as err:
            print(f"Failed to create database with error: {err}")                                   #catch error

        else:
            cursor.execute(f'USE {self.__database_name}')                                           #move cursor to work in this database
                  #create events table with two columns
            cursor.execute(f"CREATE TABLE {self.USERS_TABLE_DESCRIPTION}")     #create users table with two columns
            cursor.execute(f'CREATE TABLE {self.PRODUCTS_TABLE_DESCRIPTION}')
            cursor.execute(f"CREATE TABLE {self.JOURNEY_TABLE_DESCRIPTION}") 



        cursor.close()
        self.__PGL_db_connection = self.__database_name
                           
    def userExists(self, username) -> bool:
        cursor = self.__PGL_db_connection.cursor()
        query = f'SELECT COUNT(username) FROM {self.USERS_TABLE_NAME} WHERE username = "{username}";'
        cursor.execute(query)
        duplicates = cursor.fetchone()[0]
        if duplicates == 0: 
            return False 
        else:
            return True


    # store event in database.
    # event is in string format with entry values separated by ';'
    def store(self, event, table : str):
        # we should format the event here in respective columns and such
        try:
            # store timestamp event in 'events' table
            if table == self.JOURNEY_TABLE_NAME:
                cursor = self.__PGL_db_connection.cursor()
                query = f"INSERT INTO {self.JOURNEY_TABLE_NAME} (datetime, timestamp, device) VALUES (%s, %s, %s)"
                val = tuple(event.split(';')[:-1])
                cursor.execute(query, val)
                self.__PGL_db_connection.commit()
                print("Stored event in DB")

            # store user in 'users' table
            elif table == self.USERS_TABLE_NAME:
                cursor = self.__PGL_db_connection.cursor()

                # check that user doesn't already exist
                val = tuple(event.split(';')[:-1])                
                # if no duplicates, insert in table
                if not self.userExists(val[0]):
                    cursor.reset()
                    query = f"INSERT INTO {self.USERS_TABLE_NAME} (username, password, usertype) VALUES (%s, %s, %s)"
                    cursor.execute(query, val)
                    self.__PGL_db_connection.commit()
                    print("Stored user in DB")
                    return 'VALID'

                # user already exists
                else:
                    cursor.reset()
                    cursor.close()
                    print("Duplicate user not stored")
                    return 'INVALID'
            
            # store new 'product' in products table
            elif table == self.PRODUCT_TABLE_NAME:
                cursor = self.__PGL_db_connection.cursor()
                val = tuple(event.split(';')[:-1])
                user = val[0]
                if self.userExists(user):
                    query = f"INSERT INTO {self.PRODUCT_TABLE_NAME}(device, user) VALUES (%s, %s)"                
                    cursor.execute(query, val)
                    self.__PGL_db_connection.commit()
                    print("Stored product in DB")
                else:
                    print("User not found. Didn't store products")

        except mysql.Error as err:
            print(f'Failed to insert into database with error: {err}')

        cursor.close()

    
    def getEvents(self, table : str, credentials : str) -> str:
        # returns all data related to the user from the database as string in json format
        if table == self.JOURNEY_TABLE_NAME:
            credentials = tuple(credentials.split(';')[:-1])                    #get username
            username = credentials[0]
            query = f'SELECT device FROM products WHERE user = "{username}"'    #find all devices related to user from products table
            cursor = self.__PGL_db_connection.cursor()
            journeys = []
            events = []
            cursor.execute(query)
            all_data = cursor.fetchall()                                        #get all devices related to user
            for row in all_data:
                query = f'SELECT * FROM journey WHERE device = "{row[0]}"'      #find all journeys related to device
                cursor.execute(query)
                journeys = cursor.fetchall()
                for j in journeys:
                    events.append(j)

            events_json = json.dumps(events)
            return events_json
        
        # validates a user by checking if the user/pass combination exists in 'users' table
        elif table == self.USERS_TABLE_NAME:
            credentials = tuple(credentials.split(';')[:-1])
            user = credentials[0]
            pass_ = credentials[1] 
            cursor = self.__PGL_db_connection.cursor()
            query = f'SELECT COUNT(*) FROM {self.USERS_TABLE_NAME} WHERE username = "{user}" AND password = "{pass_}"'

            try:
                cursor.execute(query)
                
                if cursor.fetchone()[0] > 0:
                    return 'VALID'
                else:
                    return 'INVALID'
            
            except mysql.Error as err:
                Warning.warn("Failed to validate user")    
                return 'INVALID'            


class PGLEventManagerController:
    """The controller listens on MQTT topics and differentiates between three different. 
    Handles both incoming data to be stored in the database (model) as well as requests for 
    outgoing data (to the web server (?))"""

    # different MQTT topics
    # READ: Right now we publish on the 'RESPONSE_VALIDATE_USER_TOPIC' topic both when explicitly requested (logging in),
    # and when trying to create a new user (check for duplicates). 
    MAIN_TOPIC = "PGL"
    ALL_TOPICS = "PGL/#"
    REQUEST_TOPICS = f"{MAIN_TOPIC}/request/#"
    #this is the events that the PI publishes to
    REQUEST_STORE_EVENT_IN_DB_TOPIC = f'{MAIN_TOPIC}/request/store_event'   
    REQUEST_EMERGENCY_TOPIC = f'{MAIN_TOPIC}/request/emergency'

    # these are the events that the web should request on
    REQUEST_STORE_USER_IN_DB_TOPIC = f'{MAIN_TOPIC}/request/store_user'
    REQUEST_CREATE_PRODUCT_TOPIC = f'{MAIN_TOPIC}/request/store_product'
    REQUEST_GET_EVENTS_TOPIC = f'{MAIN_TOPIC}/request/get_events'
    REQUEST_VALIDATE_USER_TOPIC = f'{MAIN_TOPIC}/request/valid_user'

    RESPONSE_SEND_EVENTS_TOPIC = f'{MAIN_TOPIC}/response/send_events'
    RESPONSE_VALIDATE_USER_TOPIC = f'{MAIN_TOPIC}/response/valid_user'
    RESPONSE_EMERGENCY_TOPIC = f'{MAIN_TOPIC}/response/emergency'

    def __init__(self, mqtt_host:str, model: PGLEventManagerModel,mqtt_port: int = 1883) -> None:
        self.__subscriber_thread = Thread(target=self.worker,
                                          daemon=True)
        self.__stop_worker = Event()
        self.__events_queue = Queue()
        self.__PGLmodel = model

        # mqtt parameters and callback methods
        self.__mqtt_host = mqtt_host
        self.__mqtt_port = mqtt_port
        self.__mqtt_client = MqttClient()
        self.__mqtt_client.on_message = self.onMessage
        self.__mqtt_client.on_connect = self.onConnect
        # initialize other callback methods here

    # connect the model to address and start the subscriber_thread
    def startListening(self) -> None:
        self.__PGLmodel.connectDB()                                 #connect to database

        self.__mqtt_client.connect(host=self.__mqtt_host,           #connect to mqtt
                                   port=self.__mqtt_port)
        
        self.__mqtt_client.loop_start()                             #start loop
        self.__mqtt_client.subscribe(self.REQUEST_TOPICS)           #subscribe to all topics
        self.__subscriber_thread.start()                            #start subscriber thread (listens for mqtt)

    # stop subscriber thread and disconnect the model
    def stopListening(self) -> None:
        self.__stop_worker.set()
        self.__mqtt_client.loop_stop()
        self.__mqtt_client.unsubscribe(self.ALL_TOPICS)
        self.__mqtt_client.disconnect()

        # Disconnect from the database
        self.__PGLmodel.disconnectDB()

    # callback method that is called when __mqtt_client is connected
    def onConnect(self, client, userdata, flags, rc) -> None:
        print("MQTT client connected")

    # callback method that is called whenever a message arrives on a topic that '__mqtt_client' subscribes to
    def onMessage(self, client, userdata, message : MQTTMessage) -> None:
        self.__events_queue.put(message)
        print(f'MQTT Message recievered with payload: {message.payload}')

    # worker is the method that the __subscriber_thread runs
    # listens for MQTT events
    # empties __events_queue
    def worker(self) -> None:
        print("Subscriber_thread worker started")
        while not self.__stop_worker.is_set():
            try:
                # pull message form events queue
                # timeout indicates that we stop trying to dequeue after 1 s
                # throws 'Empty' exception if timeout
                mqtt_message : MQTTMessage = self.__events_queue.get(timeout = 1)
            # if queue empty return
            except Empty:
                pass
            # if the pull was succesful, handle the message
            else:
                try:
                    mqtt_message_topic = mqtt_message.topic
                    # store event from PI in database
                    if mqtt_message_topic == self.REQUEST_STORE_EVENT_IN_DB_TOPIC:
                        # if any logic should be computed on the incoming data, we should do it here?
                        event_string = mqtt_message.payload.decode("utf-8")
                        self.__PGLmodel.store(event_string, self.__PGLmodel.JOURNEY_TABLE_NAME)
                    
                    # store produc in database (from web request)
                    elif mqtt_message_topic == self.REQUEST_CREATE_PRODUCT_TOPIC:
                        event_string = mqtt_message.payload.decode("utf-8")
                        self.__PGLmodel.store(event_string, self.__PGLmodel.PRODUCT_TABLE_NAME)

                    # store user in database
                    elif mqtt_message_topic == self.REQUEST_STORE_USER_IN_DB_TOPIC:
                        # if any logic should be computed on the incoming data, we should do it here
                        event_string = mqtt_message.payload.decode("utf-8")
                        succ = self.__PGLmodel.store(event_string, self.__PGLmodel.USERS_TABLE_NAME)
                        # publish to indicate if user is stored succesfully
                        self.__mqtt_client.publish(self.RESPONSE_VALIDATE_USER_TOPIC, succ)

                    # return all events from database for given user
                    elif mqtt_message_topic == self.REQUEST_GET_EVENTS_TOPIC:
                        # retrieve data from database using the model
                        credentials = mqtt_message.payload.decode("utf-8")
                        data = self.__PGLmodel.getEvents(self.__PGLmodel.JOURNEY_TABLE_NAME, credentials)
                        # publish the data on the proper topic
                        self.__mqtt_client.publish(self.RESPONSE_SEND_EVENTS_TOPIC, data)
                        print("Published data")

                    # validate a user
                    elif mqtt_message_topic == self.REQUEST_VALIDATE_USER_TOPIC:
                        credentials = mqtt_message.payload.decode("utf-8")
                        validity = self.__PGLmodel.getEvents(self.__PGLmodel.USERS_TABLE_NAME, credentials)
                        self.__mqtt_client.publish(self.RESPONSE_VALIDATE_USER_TOPIC, validity)
                        print(f'Validated user: {validity}')

                    else:
                        # not the right topic
                        warnings.warn(f'Message recieved on unkown topic: {mqtt_message.topic}')

                except KeyError:
                    print(f'Error occured in worker: {KeyError}')


def main():
    stop_daemon = Event()
    print("Press 'x' to terminate")

    model = PGLEventManagerModel("localhost", "PGL", "PGL", "PGL")
    controller = PGLEventManagerController("localhost", model)

    controller.startListening()

    while not stop_daemon.is_set():
        if keyboard.is_pressed('x'):
            stop_daemon.set()

    print("Exiting")
    controller.stopListening()


if __name__ == "__main__":
    main()