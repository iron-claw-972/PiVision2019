# PiVision2019
Computer vision and video streaming on Raspberry Pi and writes position data on NetworkTables and includes autostart and restart.

## What does each file do?
### app.py
This is the main file, and it calls all of the other code. It runs the streaming server and sends out the images as well has handling the html templates.
```
# To run the vision and streaming code
python2 app.py
```
### templates
This directory stores templates, which contain the html code for the streaming website.
### camera.py
This handles the threading of the camera and the frame capture, which are passed on to detector.py and app.py.
### detector.py
This runs the computer vision code and looks for the vision targets in a given frame. It also posts the position and rotation data on Networktables:
```python
self.sd.putNumber("piCount", random.randint(1, 999)) # Changes if code is running
self.sd.putNumber("visionX", tvecs[0][0])
self.sd.putNumber("visionY", tvecs[1][0])
self.sd.putNumber("visionZ", tvecs[2][0])
self.sd.putNumber("visionRX", rvecs[0][0])
self.sd.putNumber("visionRY", rvecs[1][0])
self.sd.putNumber("visionRZ", rvecs[2][0])
self.sd.putNumber("visionCount", random.randint(1,999)) # Changes if vision detects a target
```
### service_setup.md
This is a guide on how to connect to and setup a Raspberry Pi to start code on boot.
