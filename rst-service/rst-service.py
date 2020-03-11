#!python
#
# author: Christian Colonna

import os
from src.classes import DataSender, FileHandler, RSTMiner, FREDDialer, RDFParams, GlobalStorage, BridgeGraph

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
#TMP_FOLDER = 'tmp'
CONVERTER_PORT = '5000'
CONVERTER_ENDPOINT = 'http://' + CONVERTER_HOST + ':' + CONVERTER_PORT + '/convert/hilda/dis'
CURL_FILE_KEY = 'input' # this key must be set as filename in CURL request
DOC_NUMBER = 'doc' # this key is the number of the doc to be add to the namespace
NAMESPACE = 'ns'
DEFAULT_NAMESPACE = 'https://w3id.org/stlab/fred/rst/data/'
FORMAT = 'ext'
DEFAULT_FORMAT = 'n3'
TEST_FOLDER = 'usr/src/rst-service-api/test'
DEBUG = True

# == Flask Config == 
app = Flask(__name__)
cors = CORS(app) # TODO : in PRODUCTION allow cors just for interservices communication
app.config['CORS_HEADERS'] = 'Content-type'

# helpers
sender = DataSender()
rstminer = RSTMiner()
filehandler = FileHandler()
storage = GlobalStorage()

# ============ API ==============

@app.route("/rst", methods=["POST"])
def rst():
    """ Base API: returns pure RDF graph according to RST semantics for a text
    """
    set_rst_params()
    g = produce_rdf()
    return (g.serialize (format=storage.get_rdf_params().serialization ))

@app.route("/saliency", methods=["POST"])
@cross_origin()
def saliency():
    """ Returns JSON : [ { 'text' : '<edu words>', 'score' : '<edu_score>', 'heat_color': '<heat_map_color>'} ... ]
        list of edus
    """ 
    set_rst_params()
    g = produce_rdf()
    return rstminer.extract_saliency(g)

@app.route("/bridge", methods=["POST"])
@cross_origin()
def merge():
    set_rst_params()
    g = produce_bridge_graph()
    return (g.serialize(format=storage.get_rdf_params().serialization))

@app.route("/facts", methods=["POST"])
@cross_origin()
def facts():
    set_rst_params()
    SALIENCY_TRESHOLD = 0
    g = produce_bridge_graph()
    return rstminer.extract_facts(g, SALIENCY_TRESHOLD)

# ========== FUNCTIONS ============

def set_rst_params():
    # 1) SET PARAMS
    storage.set_rdf_params(RDFParams(request.form))
    storage.set_plain_file(filehandler.parse_request_text(request, CURL_FILE_KEY, TMP_FOLDER))
    storage.set_raw_text(filehandler.open_file_to_string(TMP_FOLDER, storage.get_plain_file()))
    
def produce_rdf():
    """ Function to wrap all the pipe to get rdf from plain file
    """
    # 2) SEND TO FENG
    hilda_file = sender.call_rst_service(FENG_ENDPOINT, storage.get_plain_file(), 'hilda', TMP_FOLDER)
    # 3) SEND TO CONVERTER
    dis_file = sender.call_rst_service(CONVERTER_ENDPOINT, hilda_file, 'dis', TMP_FOLDER)
    # 4) PRODUCE RDF
    g = rstminer.produce_rdf(storage.get_rdf_params().doc_n, storage.get_rdf_params().ns, dis_file_path=TMP_FOLDER + '/' + dis_file, plain_text=storage.get_raw_text())    
    # 5) CLEAN TMP DIR
    filehandler.clean_dir(TMP_FOLDER, [storage.get_plain_file(), hilda_file, dis_file, ])
    return g

def produce_fred():
    """ You need to parse the input text to raw_text before and store it !
    """
    fredDialer = FREDDialer()
    g = fredDialer.dial(storage.get_raw_text())
    return g

def produce_bridge_graph():
    rst = produce_rdf().serialize(format=storage.get_rdf_params().serialization)
    fred = produce_fred().serialize(format=storage.get_rdf_params().serialization)
    g = BridgeGraph()
    return g.merge(rst, fred, storage.get_rdf_params().serialization)

# ======== TEST API ===============
@app.route("/test", methods=["GET"])
@cross_origin()
def test_request():
    return("test passed\n")

@app.route("/fred", methods=["POST"])
@cross_origin()
def fred():
    return test_fred()


if __name__ == '__main__':
    app.run(host=HOST, threaded=True, port=PORT, debug=DEBUG)
