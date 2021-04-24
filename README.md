# x728 UPS RasPi Power Management

This is a python 3 script for the Geekworm x728 Raspberry Pi UPS. Included is a systemd script that can be enabled and started at boot. You can set the low battery capacity threshold which when met, the system will shutdown safely. The x728 power button will tell the system to reboot or shutdown (hold ~1-2 seconds for reboot or ~3-5 seconds for poweroff).

## Install

 * Copy the files to your Raspbian SD card linux partition in the same directory structure as this repo
 * Edit the variables at the top of `/usr/local/sbin/x728` to your liking
 * Boot the system
 * run `sudo apt install -y python3-gpiozero python3-smbus`
 * Enable the i2c bus with `sudo raspi-config`
 * run `sudo systemd enable x728.service`
 * reboot
 
## Scripts
 * `x728batt`: (python3) prints battery voltage and capacity reported by x728
 * `x728off`: (bash) use this to shutdown the RasPi and have the UPS turn off the power (using the system command `shutdown` will not turn off the x728 power)