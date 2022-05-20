#!/bin/bash
# additional server install script

# setup multiarch qemu
sudo apt-get install qemu binfmt-support qemu-user-static
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker run --rm -t arm64v8/ubuntu uname -m

# pip dependencies
sudo apt install pip
pip install -r builder/requirements.txt

##
exit 0
