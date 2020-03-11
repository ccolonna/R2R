#!python
#
# author: Christian Colonna
# 
# helpers for rst-service api

import os, io, uuid

import requests
from werkzeug.utils import secure_filename


class FileHandler(object):

    def open_file(self, folder, filename, m='rb'):
        """ Open file in binary mode. You need this to send it via HTTP POST request.
        """
        return open(os.path.join(folder, filename), m)

    def open_encoded_file(self, folder, filename, encoding="utf-8"):
        return io.open(os.path.join(folder, filename), 'r', encoding=encoding)

    def save_secure_file(self, fh, folder):
        """ Save file received by flask app. Secure it here as arrived from outside.
        """
        fh.save(os.path.join(folder, secure_filename(fh.filename)))


    def save_file(self, string, folder, filename):
        """ Save file. 
        """ 
        with open(os.path.join(folder, filename), 'w') as fh:
            fh.write("{}".format(string))
        fh.close()
    
    def set_extension(self, filename, extension):
        f_root = filename.split(".")[0]
        return f_root + '.' + extension

    def open_file_to_string(self, folder, filename):
        fh = self.open_encoded_file(folder, filename)
        raw_file = ''
        for line in fh:
            raw_file += line
        return raw_file    

    def remove_file(self, folder, filename):
        os.remove(os.path.join(folder, filename))
    def clean_dir(self, folder, filelist):
        for filename in filelist:
            self.remove_file(folder, filename)
    
    def parse_request_text(self, request, filekey, folder):
        """ Check if input is text of a http request is text or file and parse it to a tmp plain_file
        """
        if request.files.get(filekey):
            plain_file = request.files[filekey].filename
            self.save_secure_file(request.files[filekey], folder)
        elif request.form.get(filekey):
            uuid_value = uuid.uuid1()
            plain_file = "plain_" + str(uuid_value) + ".txt"
            self.save_file(request.form.get(filekey), folder, plain_file)
        return plain_file


class DataSender(object):
    """ Handle data broadcasting over http between docker api. Send files, binaries...
    """

    def send_file(self, fh, url):
        return requests.post(url, files={'input': fh})

    def call_rst_service(self, endpoint, in_file, out_file_ext, folder):
        filehandler = FileHandler()
        fh = filehandler.open_file(folder, in_file)
        data = self.send_file(fh, endpoint).text
        out_file = filehandler.set_extension(in_file, out_file_ext)
        filehandler.save_file(data, folder, out_file)
        return out_file
