# How to setup code autostart and reboot
### Confirm connection
ping raspberrypi.local

---
### Find all raspberrypis on the network from macos
arp -na | grep -i b8:27:eb

---
### Connect
ssh pi@raspberrypi.local

---
### WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
### remove line starting with raspberrypi from .ssh/known_hosts
---
### Update
sudo apt update
sudo apt -y upgrade

---
### Change default password
sudo passwd pi

---
### Run config tool
sudo raspi-config

---
### And change Network Options -> Hostname

ssh pi@tic.local

sudo apt -y install vim python-dev python-opencv python-matplotlib python-pip

exit

---
### On each one, change tic to toe or toe
scp -r vision.service pi@tic.local:
scp -r vision pi@tic.local:

ssh pi@tic.local

pip install flask

---
### Make sure app is working
cd vision
python app.py

---
### Make it always run
sudo cp vision.service /etc/systemd/system/vision.service
sudo systemctl enable vision
sudo systemctl start vision

sudo reboot

---
### Check streaming is working
http://tic.local:5808/
