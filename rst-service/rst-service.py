#!python
#
# author: Christian Colonna

import os

from src.classes import DataSender, FileHandler, RSTMiner

from flask import Flask, request


# TODO : add dotenv
# ==== PARAMS =======
PORT = '5050'
HOST = '0.0.0.0'
FENG_HOST = 'feng'
CONVERTER_HOST = 'conv'
FENG_PORT = '8080'
FENG_ENDPOINT = 'http://' + FENG_HOST + ':' + FENG_PORT + '/parse'
TMP_FOLDER = 'usr/src/rst-service-api/tmp'
CONVERTER_PORT = '5000'
CONVERTER_ENDPOINT = 'http://' + CONVERTER_HOST + ':' + CONVERTER_PORT + '/convert/hilda/dis'
CURL_FILE_KEY = 'input' # this key must be set as filename in CURL request
DOC_NUMBER = 'doc' # this key is the number of the doc to be add to the namespace
NAMESPACE = 'ns'
DEFAULT_NAMESPACE = 'https://w3id.org/stlab/fred/rst/data/'
FORMAT = 'ext'
DEFAULT_FORMAT = 'n3'
TEST_FOLDER = 'usr/src/rst-service-api/test'

# == Flask Config == 
app = Flask(__name__)

@app.route("/test", methods=["GET"])
def test_request():
    return("test passed\n")

@app.route("/converter", methods=["GET"])
def test_converter():
    sender = DataSender()
    filehandler = FileHandler()

    fh = filehandler.open_file(TEST_FOLDER, 'test_short.hilda')

    data = sender.send_file(fh, CONVERTER_ENDPOINT).text
    fh.close()
    return data

@app.route("/", methods=["POST"])
def process_request():

    sender = DataSender()
    filehandler = FileHandler()

    # 1) RECEIVE FILE & PARAMETERS

    plain_file = request.files[CURL_FILE_KEY].filename
    # set rdf parameters
    doc_n = request.form.get(DOC_NUMBER) if request.form.get(DOC_NUMBER) else 1
    ns = request.form.get(NAMESPACE) if request.form.get(NAMESPACE) else DEFAULT_NAMESPACE
    ext = request.form.get(FORMAT) if request.form.get(FORMAT) else DEFAULT_FORMAT
    
    filehandler.save_secure_file(request.files[CURL_FILE_KEY], TMP_FOLDER)
    fh = filehandler.open_file(TMP_FOLDER, plain_file)

    # 2) SEND TO FENG
    data = sender.send_file(fh, FENG_ENDPOINT).text
    hilda_file = filehandler.set_extension(plain_file, 'hilda')
    filehandler.save_file(data, TMP_FOLDER, hilda_file)
    fh = filehandler.open_file(TMP_FOLDER, hilda_file)

    # 3) SEND TO CONVERTER
    data = sender.send_file(fh, CONVERTER_ENDPOINT).text
    fh.close()
    dis_file = filehandler.set_extension(hilda_file, 'dis')
    filehandler.save_file(data, TMP_FOLDER, dis_file)

    # 4) PRODUCE RDF
    rstminer = RSTMiner()
    rstminer.load_tree(TMP_FOLDER + '/' + dis_file)    
    g = rstminer.produce_rdf(doc_n, ns, plain_text=filehandler.open_file_to_string(TMP_FOLDER, plain_file)) 

    # 5) CLEAN TMP DIR
    filehandler.clean_dir(TMP_FOLDER, [plain_file, hilda_file, dis_file, ])

    # 6) SEND DATA 
    data = ( g.serialize(format=ext) ) 
    return data


if __name__ == '__main__':
    app.run(host=HOST, threaded=True, port=PORT)
