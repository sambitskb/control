from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

class MockSerial:
    def __init__(self):
        self.port = ""
        self.baudrate = 9600
        self.parity = "N"
        self.bytesize = 8
        self.stopbits = "1"
        self.is_open = False
        self.response = ""

    def open(self):
        self.is_open = True
        print("Mock: Serial port opened.")

    def close(self):
        self.is_open = False
        print("Mock: Serial port closed.")

    def write(self, data):
        print(f"Mock: Sending command: {data}")
        if data == b"*OPC?\n":
            self.response = b"1\r\n"

    def readline(self):
        return self.response

class PowerSupplyControlApp:
    def __init__(self):
        self.com = MockSerial()
        self.load_config()
        self.v1_voltage = "0"
        self.v1_current = "0"
        self.v2_voltage = "0"
        self.v2_current = "0"
        self.connected = False

    def load_config(self):
        try:
            self.config = ["COM1", "9600", "N", "8", "1"]
            self.com.port = self.config[0].strip()
            self.com.baudrate = int(self.config[1].strip())
            self.com.parity = self.config[2].strip()
            self.com.bytesize = int(self.config[3].strip())
            self.com.stopbits = self.config[4].strip()
        except Exception as ex:
            print(f"Failed to load config: {ex}")

    def connect(self):
        try:
            self.com.open()
            self.com.write(b"*OPC?\n")
            response = self.com.readline()
            if response == b"1\r\n":
                self.connected = True
                self.com.close()
                return {"success": True, "message": "Successfully connected to Sorensen XPF60-20DP!"}
            else:
                self.connected = False
                self.com.close()
                return {"success": False, "message": "Failed to connect to Sorensen XPF60-20DP."}
        except Exception as e:
            self.connected = False
            return {"success": False, "message": f"Failed to connect to Sorensen XPF60-20DP: {e}"}

    def send_command(self, command):
        try:
            self.com.open()
            self.com.write(f"{command}\n".encode())
            self.com.close()
            return True
        except Exception as e:
            print(f"Failed to send command: {e}")
            return False

    def set_voltage(self, channel, model):
        if model == "DI-8110":
            voltage, current = "24", "0.5"
        elif model == "DI-8111":
            voltage, current = "48", "0.5"
        elif model == "DI-8112":
            voltage, current = "110", "0.5"
        elif model == "DI-8113":
            voltage, current = "220", "0.5"
        else:
            return False

        if channel == "1":
            self.send_command(f"v1 {voltage}")
            self.send_command(f"i1 {current}")
            self.v1_voltage = voltage
            self.v1_current = current
        elif channel == "2":
            self.send_command(f"v2 {voltage}")
            self.send_command(f"i2 {current}")
            self.v2_voltage = voltage
            self.v2_current = current

        return True

    def reset_control(self, reset_option):
        try:
            self.com.open()
            if reset_option == "V1 CONTROL":
                self.send_command("OP1 0")
                self.send_command("v1 0")
                self.send_command("i1 0")
                self.v1_voltage = "0"
                self.v1_current = "0"
            elif reset_option == "V2 CONTROL":
                self.send_command("OP2 0")
                self.send_command("v2 0")
                self.send_command("i2 0")
                self.v2_voltage = "0"
                self.v2_current = "0"
            elif reset_option == "BOTH CONTROL":
                self.send_command("OP1 0")
                self.send_command("OP2 0")
                self.send_command("v1 0")
                self.send_command("i1 0")
                self.send_command("v2 0")
                self.send_command("i2 0")
                self.v1_voltage = "0"
                self.v1_current = "0"
                self.v2_voltage = "0"
                self.v2_current = "0"
            self.com.close()
            return True
        except Exception as e:
            print(f"Failed to reset control: {e}")
            return False

# Initialize the power supply controller
psu_controller = PowerSupplyControlApp()

@app.route('/')
def index():
    return render_template('index.html', 
                         v1_voltage=psu_controller.v1_voltage,
                         v1_current=psu_controller.v1_current,
                         v2_voltage=psu_controller.v2_voltage,
                         v2_current=psu_controller.v2_current,
                         connected=psu_controller.connected)

@app.route('/connect', methods=['POST'])
def connect():
    result = psu_controller.connect()
    return jsonify(result)

@app.route('/set_voltage', methods=['POST'])
def set_voltage():
    channel = request.form.get('channel')
    model = request.form.get('model')

    success = psu_controller.set_voltage(channel, model)
    if success:
        return redirect(url_for('index'))
    else:
        return jsonify({"success": False, "message": "Failed to set voltage"})

@app.route('/reset', methods=['POST'])
def reset():
    reset_option = request.form.get('reset_option')
    success = psu_controller.reset_control(reset_option)

    if success:
        return redirect(url_for('index'))
    else:
        return jsonify({"success": False, "message": "Failed to reset"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)