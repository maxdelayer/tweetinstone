# Everything from this tutorial
# https://packaging.python.org/en/latest/tutorials/packaging-projects/

# get in .venv first
source /.venv/bin/activate

# ensure build is installed
python3 -m pip install --upgrade build
#sudo apt install python3.10-venv
# twine is used for uploading
#python3 -m pip install --upgrade twine

# build
python3 -m build

# install generated wheel?
pip3 uninstall -y tis
pip3 install dist/tis-*.whl

# Leave venv?
#deactivate