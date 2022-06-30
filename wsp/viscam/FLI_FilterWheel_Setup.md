# Setting Up the FLI Filter Wheeel on Raspberry Pi

## Pi Hardware
This was tested on a Raspberry Pi 4 Model B with 4 Gb of RAM. This is a 64 bit device.

## Pi Setup
### Setting up OS
The FLI kernel object and SDK were successfully compiled on ubuntu on the Pi. I was unable to get them working using Raspian. To set this up you need a 32 Gb micro SD card and a computer you can plug it into. To install ubuntu, follow these steps on your PC:
1. Download the [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert the SD card
3. Click the box under Operating System. Select `Other general-purpose OS` --> `Ubuntu` --> `Ubuntu Desktop <Version>`. When I did this it was `Ubuntu Desktop 22.04 LTS (RPi 4/400)`, "64-bit desktop OS for Pi 4 models with 2Gb+".
4. Click the storage box, and select your micro SD drive.
5. Then click write! Should take 10-15 min to flash the drive.
### Setting up the Pi itself
The ubuntu version downloaded is very "light" in that it has almost no included packages. Some packages will need to get installed:
- git: `sudo apt install git`
- make: `sudo apt install make`
## FLI Driver Setup
### Dependencies for the drivers
- bison: `sudo apt install bison`
- 
### Download the driver packages 
There are two zip files of files that must be downloaded from FLI
#### USB Driver
Used the later version. Modified the Makefile

### SDK
Used the version from the website, but used the Makefile from https://github.com/SydneyAstrophotonicInstrumentationLab/python-FLI to create the .so object
