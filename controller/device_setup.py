import serial
import serial.tools.list_ports
import json
import os
import time

AXES = ["L0","L1","L2","R0","R1","R2"]

MOVEMENTS = {
    "1":"stroke",
    "2":"surge",
    "3":"sway",
    "4":"pitch",
    "5":"roll",
    "6":"twist",
    "7":None
}

PROFILE_FOLDER = "profiles"


def scan_ports():

    ports = list(serial.tools.list_ports.comports())

    print("\nDetected Serial Devices\n")

    for i,p in enumerate(ports):

        print(f"[{i}] {p.device} - {p.description}")

    return ports


def select_port(ports):

    while True:

        try:

            index = int(input("Select device: "))
            return ports[index]

        except:

            print("Invalid selection")


def connect(port):

    ser = serial.Serial(port.device,115200)

    time.sleep(2)

    return ser


def test_axis(ser,axis):

    print(f"\nTesting {axis}")

    ser.write(f"{axis}300\n".encode())
    time.sleep(1)

    ser.write(f"{axis}700\n".encode())
    time.sleep(1)

    ser.write(f"{axis}500\n".encode())
    time.sleep(1)


def ask_movement():

    print("\nWhat movement occurred?")

    print("1 - Stroke")
    print("2 - Surge (forward/back)")
    print("3 - Sway (left/right)")
    print("4 - Pitch")
    print("5 - Roll")
    print("6 - Twist")
    print("7 - Nothing / Not connected")

    while True:

        choice = input("> ")

        if choice in MOVEMENTS:
            return MOVEMENTS[choice]


def run_axis_detection(ser):

    mapping = {}

    for axis in AXES:

        test_axis(ser,axis)

        movement = ask_movement()

        if movement:
            mapping[movement] = axis

    return mapping


def save_profile(name,port,mapping):

    profile = {

        "name":name,

        "connection":{
            "method":"serial",
            "port":port.device,
            "description":port.description
        },

        "protocol":"tcode",

        "mapping":mapping,

        "ranges":{
            "stroke":{"min":200,"max":800},
            "sway":{"min":200,"max":800},
            "surge":{"min":200,"max":800},
            "twist":{"min":300,"max":700},
            "roll":{"min":300,"max":700},
            "pitch":{"min":300,"max":700}
        }
    }

    os.makedirs(PROFILE_FOLDER,exist_ok=True)

    path = os.path.join(PROFILE_FOLDER,name+".json")

    with open(path,"w") as f:
        json.dump(profile,f,indent=4)

    print("\nSaved profile:",path)


def main():

    ports = scan_ports()

    port = select_port(ports)

    name = input("Name this device: ")

    ser = connect(port)

    mapping = run_axis_detection(ser)

    ser.close()

    save_profile(name,port,mapping)


if __name__ == "__main__":
    main()