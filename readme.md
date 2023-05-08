# Prerequisites
The following python packets should be installed with the respective commands:
- MYSQL-connector: ```pip install mysql-connector-python```
- Paho mqtt: ```pip install paho-mqtt```
- Keyboard: ```pip install keyboard```

Moreover, you should download the mariaDB server: https://mariadb.org/download/?t=mariadb&p=mariadb&r=11.1.0&os=windows&cpu=x86_64&pkg=msi&m=dotsrc

When having finished the download go to the download folder and enter the 'bin' folder. Open this folder in terminal and enter ```mysql -uroot -p``` which will ask for the root password. Use the password you chose when downloading the server. Now, the mariadb-server should be running. 

Now, enter the two subsequent commands:
```
CREATE USER 'pgl'@'localhost' identified by 'pgl';
GRANT ALL PRIVILEGES ON pgl.* TO 'pgl'@'localhost';
```
This will (1) create the user used by the python program and (2) grant all privileges to the PGL databse. 

# How to run
- Run the file ```PGLEventManager.py```.
- The file ```publishTest.py``` contains a few testing lines for publishing and subscribing. 
- When executed correctly, this should be indicated in the console. 
 
After having inserted a couple of items, you can view the different tables in the console where the mariadb server is running. For instance to:
- Show all databases: ```SHOW DATABASES;```
- Select some database: ```USE pgl;```
- Describe some table, for instance users: ```DESCRIBE users;```
- Show all data in some table, for instance users: ```SELECT * FROM users;``` 

Alternatively, open the program ```HeidiSQL``` installed together with mariadb for a more elegant view. 

To auto-generate class diagram using pyreverse type: ``` pyreverse src -f ALL -m n -d UML_Diagrams -o puml```. 
