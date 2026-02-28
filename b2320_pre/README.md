zip-zop-zoop flattener
======================
named after the Zoop! from Abiyoyo (a children's book)


small pyqt5 app that opens a window
drag folders on it
click flatten zips for a normal unpack
click super flatten zips if you also want one folder level removed
outer zip files are overwritten and the log shows what happened

requirements
------------
- python 3.8 or newer
- pyqt5 

setup
-----
python -m venv venv
venv\Scripts\activate    # mac/linux: source venv/bin/activate
pip install -r requirements.txt

run
---
python zipzopzoop.py

Simply 
---------------------------
1. look for zip files in every dropped folder
2. unzip each one to a temp spot
3. find inner zips, unzip them, delete those inner archives
4. if super flatten is on and everything sits in one top folder move the files up
5. zip the new content and overwrite the original file
6. if two files end up with the same name add a short random suffix

