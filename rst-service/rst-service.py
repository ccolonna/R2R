#!python
#
# author: Christian Colonna

import os

from src.classes import DataSender, FileHandler, RSTMiner

from rdflib import Literal
from flask import Flask, request
from flask_cors import CORS, cross_origin

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
SALIENT = 'sal'

# == Flask Config == 
app = Flask(__name__)
cors = CORS(app) # TODO : in PRODUCTION allow cors just for interservices communication
app.config['CORS_HEADERS'] = 'Content-type'


@app.route("/", methods=["POST"])
def process_request():
    filehandler = FileHandler()
    # 1) RECEIVE FILE & PARAMETERS
    plain_file = request.files[CURL_FILE_KEY].filename
    # set rdf parameters
    doc_n = request.form.get(DOC_NUMBER) if request.form.get(DOC_NUMBER) else 1
    ns = request.form.get(NAMESPACE) if request.form.get(NAMESPACE) else DEFAULT_NAMESPACE
    ext = request.form.get(FORMAT) if request.form.get(FORMAT) else DEFAULT_FORMAT
    salient = request.form.get(SALIENT) if request.form.get(SALIENT) else False
    filehandler.save_secure_file(request.files[CURL_FILE_KEY], TMP_FOLDER)

    # 2) SEND TO FENG
    hilda_file = call_service(FENG_ENDPOINT, plain_file, 'hilda')

    # 3) SEND TO CONVERTER
    dis_file = call_service(CONVERTER_ENDPOINT, hilda_file, 'dis')

    # 4) PRODUCE RDF
    g = produce_rdf(dis_file, plain_file, doc_n, ns) 

    # 5) CLEAN TMP DIR
    filehandler.clean_dir(TMP_FOLDER, [plain_file, hilda_file, dis_file, ])

    # 6) SEND DATA 
    if salient: 
        return salient_annotated_data(g)
    else:
        return (g.serialize (format=ext) )

def salient_annotated_data(g):
    """ Queries the graph to get edus with scores and jsonify data
    """
    rstminer = RSTMiner()
    return rstminer.extract_saliency(g)   

def call_service(endpoint, in_file, out_file_ext):
    sender = DataSender()
    filehandler = FileHandler()
    fh = filehandler.open_file(TMP_FOLDER, in_file)
    data = sender.send_file(fh, endpoint).text
    out_file = filehandler.set_extension(in_file, out_file_ext)
    filehandler.save_file(data, TMP_FOLDER, out_file)
    return out_file

def produce_rdf(dis_file, plain_file, doc_n, ns):
    sender = DataSender()
    rstminer = RSTMiner()
    filehandler = FileHandler()
    rstminer.load_tree(TMP_FOLDER + '/' + dis_file)
    g = rstminer.produce_rdf(doc_n, ns, plain_text=filehandler.open_file_to_string(TMP_FOLDER, plain_file))    
    return g

# ======== TEST API ===============
@app.route("/test", methods=["GET"])
@cross_origin()
def test_request():
    return("test passed\n")

if __name__ == '__main__':
    app.run(host=HOST, threaded=True, port=PORT)
