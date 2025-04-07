import os
import shutil
import sys
import zipfile
venv_dir = '/tmp/venv'
# append the torch_dir to PATH so python can find it
sys.path.append(venv_dir)
if not os.path.exists(venv_dir):
   tempdir = '/tmp/_venv'
   if os.path.exists(tempdir):
       shutil.rmtree(tempdir)
   zipfile.ZipFile('venv.zip', 'r').extractall(tempdir)
   os.rename(tempdir, venv_dir)