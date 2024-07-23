# Everything from this tutorial
# https://packaging.python.org/en/latest/tutorials/packaging-projects/

#sudo apt install python3.10-venv
#python3 -m pip install --upgrade twine

# get in .venv first
source .venv/bin/activate

# ensure build is installed
python3 -m pip install --upgrade build

# Remove old builds
rm dist/tweetinstone-*.whl

# build
python3 -m build

# install generated wheel?
pip3 uninstall -y tweetinstone
pip3 install dist/tweetinstone-*.whl

# Leave venv?
#deactivate