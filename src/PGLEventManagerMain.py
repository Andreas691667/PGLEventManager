from threading import Event
import keyboard
from PGLEventManagerModel import PGLEventManagerModel
from PGLEventManagerController import PGLEventManagerController
from time import sleep

def main():
    print("Press 'x' to terminate")

    model = PGLEventManagerModel("localhost", "PGL", "PGL", "PGL")
    controller = PGLEventManagerController("test.mosquitto.org", model)

    controller.startListening()

    try:
        while True:
            sleep(2)

    except KeyboardInterrupt:
        print("Exiting")
        controller.stopListening()


if __name__ == "__main__":
    main()
