#!python
#
# author: Christian Colonna

import os
from src.api import RDFParams, GlobalStorage
from src.helpers import FileHandler, DataSender
from src.rst import RSTMiner, BridgeGraph, FREDDialer
from src.env import *

from flask import Flask, request
from flask_cors import CORS, cross_origin


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
    g = produce_bridge_graph()
    return rstminer.extract_facts(g, storage.get_rdf_params().treshold)

@app.route("/fred", methods=["POST"])
@cross_origin()
def fred():
    """ Base API: returns pure RDF graph according to FRED semantics for a text
    """
    set_rst_params()
    g = produce_fred()
    return (g.serialize(format=storage.get_rdf_params().serialization))

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


# ====== RUN API =======

if __name__ == '__main__':
    app.run(host=HOST, threaded=False, port=PORT, processes=3, debug=DEBUG)
