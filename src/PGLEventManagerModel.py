import json
import warnings
import mysql.connector as mysql


class PGLEventManagerModel:
    """Model of the PGLEventManager application. Handles the database connection and data storage."""

    # tab½½le names
    __USERS_TABLE_NAME = "users"
    __JOURNEY_TABLE_NAME = "journey"
    __PRODUCT_TABLE_NAME = "products"
    __DEVICES_TABLE_NAME = "devices"
    __EMERGENCY_TABLE_NAME = "emergency"

    # table descriptions
    __USERS_TABLE_DESCRIPTION: str = """users
                                       (user_id int NOT NULL AUTO_INCREMENT,
                                        username VARCHAR(320) UNIQUE NOT NULL,
                                        password VARCHAR(255) NOT NULL, 
                                        usertype VARCHAR(30) NOT NULL, 
                                        PRIMARY KEY(user_id) )"""

    __JOURNEY_TABLE_DESCRIPTION: str = """journey
                                        (journey_id int NOT NULL AUTO_INCREMENT, 
                                        datetime VARCHAR(30) NOT NULL, 
                                        rtt VARCHAR(30) NOT NULL, 
                                        tt  VARCHAR(30),
                                        device_id VARCHAR(255) NOT NULL,
                                        PRIMARY KEY (journey_id),
                                        FOREIGN KEY (device_id) REFERENCES devices(device_id))"""

    __EMERGENCY_TABLE_DESCRIPTION: str = """emergency
                                        (emergency_id int NOT NULL AUTO_INCREMENT,
                                        datetime VARCHAR(30) NOT NULL,
                                        et VARCHAR(30) NOT NULL,
                                        device_id VARCHAR(255) NOT NULL,
                                        PRIMARY KEY (emergency_id),
                                        FOREIGN KEY (device_id) REFERENCES devices(device_id))"""

    __PRODUCTS_TABLE_DESCRIPTION: str = """products (
                                            device_id VARCHAR(255) NOT NULL,
                                            user_id int NOT NULL,
                                            PRIMARY KEY (device_id, user_id),
                                            FOREIGN KEY (device_id) REFERENCES devices(device_id),
                                            FOREIGN KEY (user_id) REFERENCES users(user_id))"""

    __DEVICES_TABLE_DESCRIPTION: str = """devices
                                          (device_id VARCHAR(255) NOT NULL,
                                          PRIMARY KEY (device_id)) """

    __TABLE_DESCRIPTIONS = [__USERS_TABLE_DESCRIPTION, __DEVICES_TABLE_DESCRIPTION, __JOURNEY_TABLE_DESCRIPTION,
                            __PRODUCTS_TABLE_DESCRIPTION, __EMERGENCY_TABLE_DESCRIPTION]

    def __init__(self, host, database: str, user: str, password: str) -> None:
        self.__host = host
        self.__database_name = database
        self.__user = user
        self.__password = password
        self.__PGL_db_connection = None

    def connectDB(self) -> None:
        # establish database connection
        try:
            self.__PGL_db_connection = mysql.connect(host=self.__host,
                                                     user=self.__user,
                                                     password=self.__password)

            self.__PGL_db_connection.cursor().execute(
                f"USE {self.__database_name}")
            print("Connected to database succesfully")

        except mysql.Error as err:
            # If the database doesn't exist, then create it.
            if err.errno == mysql.errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist. Will be created.")
                self.__createDatabase()
                print(f"Database {self.__database_name} created successfully.")
            else:
                print(f'Failed connecting to database with error: {err}')

    # disconnect from the database
    def disconnectDB(self) -> None:
        self.__PGL_db_connection.disconnect()
        print("Disconnected from database")

    # creates database with parameters from __init__
    def __createDatabase(self) -> None:
        cursor = self.__PGL_db_connection.cursor()

        try:
            # create database
            cursor.execute(
                f"CREATE DATABASE {self.__database_name} DEFAULT CHARACTER SET 'utf8'")
        except mysql.Error as err:
            # catch error
            print(f"Failed to create database with error: {err}")

        else:
            # move cursor to work in this database
            cursor.execute(f'USE {self.__database_name}')

            # create tables
            for table in self.__TABLE_DESCRIPTIONS:
                cursor.execute(f"CREATE TABLE {table}")

        cursor.close()
        self.__PGL_db_connection = self.__database_name

    # check if user exists in database
    # returns True if user exists, False otherwise
    def __userExists(self, username) -> bool:
        # retrieves the count of rows with the given username
        cursor = self.__PGL_db_connection.cursor()
        query = f'SELECT COUNT(username) FROM {self.__USERS_TABLE_NAME} WHERE username = "{username}";'
        cursor.execute(query)
        user_count = cursor.fetchone()[0]
        if user_count == 0:
            return False
        else:
            return True

    # check if device exists in database
    # returns True if device exists, False otherwise
    def __deviceExists(self, device_id) -> bool:
        # retrieves the count of rows with the given device_id
        cursor = self.__PGL_db_connection.cursor()
        query = f'SELECT COUNT(device_id) FROM {self.__DEVICES_TABLE_NAME} WHERE device_id = "{device_id}";'
        cursor.execute(query)
        device_count = cursor.fetchone()[0]
        if device_count == 0:
            return False
        else:
            return True

# region Store data in database
    # store a new device in the database with the given device_id
    def storeDevice(self, device_id: str) -> None:
        try:
            if not self.__deviceExists(device_id):
                cursor = self.__PGL_db_connection.cursor()
                query = f'INSERT INTO {self.__DEVICES_TABLE_NAME} (device_id) VALUES ("{device_id}")'
                cursor.execute(query)
                self.__PGL_db_connection.commit()
                print("Stored device in DB")
                cursor.close()
            else:
                print("Device already exists in DB")

        except mysql.Error as err:
            print(f'Failed to insert into database with error: {err}')

    # store a new journey in the database with the given payload
    def storeJourney(self, payload: str) -> None:
        try:
            cursor = self.__PGL_db_connection.cursor()
            val = tuple(payload.split(';')[:-1])

            # check if device exists in database and create it if it doesn't
            device = val[3].strip()
            if not self.__deviceExists(device):
                print(
                    f"Device: {device} does not exist in DB. Will be created.")
                self.storeDevice(device)

            # store journey in database
            query = f"INSERT INTO {self.__JOURNEY_TABLE_NAME} (datetime, rtt, tt, device_id) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, val)
            self.__PGL_db_connection.commit()
            print("Stored event in DB")
            cursor.close()

        except mysql.Error as err:
            print(f'Failed to insert journey into database with error: {err}')

    # store a new emergency in the database with the given payload
    def storeEmergency(self, payload: str) -> None:
        try:
            cursor = self.__PGL_db_connection.cursor()
            val = tuple(payload.split(';')[:-1])

            # check if device exists in database and create it if it doesn't
            device = val[2].strip()
            if not self.__deviceExists(device):
                print(
                    f"Device: {device} does not exist in DB. Will be created.")
                self.storeDevice(device)

            # store emergency in database
            query = f"INSERT INTO {self.__EMERGENCY_TABLE_NAME} (datetime, et, device_id) VALUES (%s, %s, %s)"
            cursor.execute(query, val)
            self.__PGL_db_connection.commit()
            print("Stored emergency in DB")
            cursor.close()

        except mysql.Error as err:
            print(
                f'Failed to insert emergency into database with error: {err}')

    # store a new user in the database with the given credentials
    def storeUser(self, credentials: str) -> str:
        try:
            cursor = self.__PGL_db_connection.cursor()
            val = tuple(credentials.split(';')[:-1])
            username = val[0]

            # if no duplicates, insert in table
            if not self.__userExists(username):
                cursor.reset()
                query = f"INSERT INTO {self.__USERS_TABLE_NAME} (username, password, usertype) VALUES (%s, %s, %s)"
                cursor.execute(query, val)
                self.__PGL_db_connection.commit()
                print("Stored user in DB")
                cursor.close()
                return 'VALID', username

            # user already exists
            else:
                cursor.reset()
                cursor.close()
                print("Duplicate user not stored")
                return 'INVALID', username

        except mysql.Error as err:
            print(f'Failed to insert into database with error: {err}')

    # create a new product in the database with the given user and device
    # this method is invoked from public storeProduct method which handles user types
    def __createProduct(self, user: str, device: str, cursor):
        query = f"""INSERT INTO products (device_id, user_id) 
                VALUES ('{device}', 
                    (SELECT user_id FROM users WHERE username = '{user}'));"""

        cursor.execute(query)
        self.__PGL_db_connection.commit()
        print(f'Created product for user: {user} and device_id: {device}')
        cursor.close()

    # store a new product in the database with the given payload
    def storeProduct(self, payload: str) -> str:
        try:
            cursor = self.__PGL_db_connection.cursor()
            val = tuple(payload.split(';')[:-1])
            user = val[1]
            device_id = val[0]

            # get user type
            query = f"SELECT usertype FROM users WHERE username = '{user}';"
            cursor.execute(query)
            usertype = cursor.fetchone()[0]

            # if user is caregiver then create product
            if usertype == 'caregiver':
                self.__createProduct(user, device_id, cursor)
                return 'VALID', user

            # if user is resident then check if a product exists
            elif usertype == 'resident':
                query = f"""SELECT COUNT(device_id) FROM products 
                                WHERE user_id = (SELECT user_id FROM users WHERE username = '{user}');"""
                cursor.execute(query)
                product_count = cursor.fetchone()[0]
                if product_count == 0:
                    self.__createProduct(user, device_id, cursor)
                    return 'VALID', user
                else:
                    print(f'Product already exists for resident-user: {user}')
                    return 'INVALID', user

            # invalid usertype or user not found
            else:
                return 'INVALID', user

        except mysql.Error as err:
            print(f'Failed to insert into database with error: {err}')
            return 'INVALID', user

# endregion

    # convert data with row_headers_count to json
    def __eventsToJson(self, data, row_headers_count) -> str:
        events = []
        for row in data:
            events.append(dict(zip(row_headers_count, row)))
        events_json = json.dumps(events)
        return events_json

# region Get data from database

    # get journeys from database corresponding to the given payload
    def getJourneys(self, payload: str) -> str:
        payload_in = tuple(payload.split(';')[:-1])  # get payload as tuple
        # get username from payload
        username = payload_in[0]

        if len(payload_in) > 1:
            # get device_id from payload if available
            device_id = payload_in[1]
        else:
            device_id = 0

        # return ALL data related to user. Returns empty list if no data
        if device_id == 0:
            cursor = self.__PGL_db_connection.cursor()
            query = f"""SELECT * FROM {self.__JOURNEY_TABLE_NAME} 
                                JOIN {self.__PRODUCT_TABLE_NAME} ON journey.device_id = products.device_id 
                                    WHERE products.user_id = 
                                        (SELECT user_id FROM {self.__USERS_TABLE_NAME} 
                                            WHERE username = '{username}')"""
            cursor.execute(query)
            # fetch all data in format [(row1), (row2), ... row(row_headers)]
            all_data = cursor.fetchall()
            # this will extract row headers
            row_headers = [x[0] for x in cursor.description]
            return self.__eventsToJson(all_data, row_headers), username

        # return data related to specific device and user. Returns empty list if no data
        elif device_id != 0:
            cursor = self.__PGL_db_connection.cursor()
            query = f"""SELECT * FROM {self.__JOURNEY_TABLE_NAME} 
                                JOIN {self.__PRODUCT_TABLE_NAME} ON journey.device_id = products.device_id 
                                    WHERE products.user_id = 
                                        (SELECT user_id FROM {self.__USERS_TABLE_NAME} WHERE username = '{username}') 
                                            AND products.device_id = '{device_id}'"""
            cursor.execute(query)
            all_data = cursor.fetchall()
            # this will extract row headers
            row_headers = [x[0] for x in cursor.description]
            return self.__eventsToJson(all_data, row_headers), username

    # get emergencies from database corresponding to the given payload
    def getEmergencies(self, payload: str) -> str:
        payload_in = tuple(payload.split(';')[:-1])  # get payload as tuple
        # get username from payload
        username = payload_in[0]

        if len(payload_in) > 1:
            # get device_id from payload if available
            device_id = payload_in[1]
        else:
            device_id = 0

        # return ALL emergencies related to user. Returns empty list if no data
        if device_id == 0:
            cursor = self.__PGL_db_connection.cursor()
            query = f"""SELECT * FROM {self.__EMERGENCY_TABLE_NAME}
                            JOIN {self.__PRODUCT_TABLE_NAME} ON emergency.device_id = products.device_id
                                WHERE products.user_id =
                                    (SELECT user_id FROM {self.__USERS_TABLE_NAME} 
                                        WHERE username = '{username}')"""

            cursor.execute(query)
            all_data = cursor.fetchall()
            # this will extract row headers
            row_headers = [x[0] for x in cursor.description]
            return self.__eventsToJson(all_data, row_headers), username

        elif device_id != 0:
            cursor = self.__PGL_db_connection.cursor()
            query = f"""SELECT * FROM {self.__EMERGENCY_TABLE_NAME} 
                            JOIN {self.__PRODUCT_TABLE_NAME} ON emergency.device_id = products.device_id 
                                WHERE products.user_id = 
                                    (SELECT user_id FROM {self.__USERS_TABLE_NAME} WHERE username = '{username}') 
                                        AND products.device_id = '{device_id}'"""
            cursor.execute(query)
            all_data = cursor.fetchall()
            # this will extract row headers
            row_headers = [x[0] for x in cursor.description]
            return self.__eventsToJson(all_data, row_headers), username

    # validate user with given credentials
    def validateUser(self, credentials: str) -> str:
        try:
            payload_in = tuple(credentials.split(';')[:-1])
            user = payload_in[0]
            pass_ = payload_in[1]
            cursor = self.__PGL_db_connection.cursor()
            query = f'SELECT COUNT(*) FROM {self.__USERS_TABLE_NAME} WHERE username = "{user}" AND password = "{pass_}"'
            cursor.execute(query)
            rows = cursor.fetchone()
            count = rows[0]
            cursor.reset()
            cursor.close()
            if (count > 0):
                return 'VALID', user
            else:
                return 'INVALID', user

        except mysql.Error as err:
            warnings.warn("Failed to validate user with error: " + str(err))
            return 'INVALID', user

# endregion
