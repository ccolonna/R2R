#!python
#
# author: Christian Colonna

import os

from src.classes import DataSender, FileHandler, RSTMiner

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
DEBUG = True

# == Flask Config == 
app = Flask(__name__)
cors = CORS(app) # TODO : in PRODUCTION allow cors just for interservices communication
app.config['CORS_HEADERS'] = 'Content-type'

# helpers
sender = DataSender()
rstminer = RSTMiner()
filehandler = FileHandler()

# ============ API ==============

@app.route("/", methods=["POST"])
def rdf():
    """ Base API: returns pure rdf graph
    """
    g = process_request()
    return (g.serialize (format=set_rdf_serialization()) )

@app.route("/saliency", methods=["POST"])
@cross_origin()
def saliency():
    """ Returns JSON : { '<edu_numb>' : { 'text' : '<edu words>', 'score' : '<edu_score>', 'heat_color': '<heat_map_color>'} }
    """ 
    g = process_request()
    return rstminer.extract_saliency(g)

# ========== FUNCTIONS ============

def process_request():
    # 1) RECEIVE DATA 
    plain_file = parse_text()
    # 2) SET RDF PARAMS
    doc_n, ns = set_rdf_params()
    # 3) PRODUCE RDF
    g = plain_to_rdf(doc_n, ns, plain_file)
    return g

def parse_text():
    """ Check if input is text or file and parse it to a tmp plain_file
    """
    if request.files.get(CURL_FILE_KEY):
        plain_file = request.files[CURL_FILE_KEY].filename
        filehandler.save_secure_file(request.files[CURL_FILE_KEY], TMP_FOLDER)
    elif request.form.get(CURL_FILE_KEY):
        plain_file = "plain.txt"
        filehandler.save_file(request.form.get(CURL_FILE_KEY), TMP_FOLDER, "plain.txt")
    return plain_file

def set_rdf_serialization():
    """ Return rdf serialization as given by api call. Default : n3
    """
    return request.form.get(FORMAT) if request.form.get(FORMAT) else DEFAULT_FORMAT

def set_rdf_params():
    """ Set document namespace and global namespace
    """
    doc_n = request.form.get(DOC_NUMBER) if request.form.get(DOC_NUMBER) else 1
    ns = request.form.get(NAMESPACE) if request.form.get(NAMESPACE) else DEFAULT_NAMESPACE
    return doc_n, ns

def plain_to_rdf(doc_n, ns, plain_file):
    """ Function to wrap all the pipe to get rdf from plain file
    """
    # 2) SEND TO FENG
    hilda_file = call_service(FENG_ENDPOINT, plain_file, 'hilda')

    # 3) SEND TO CONVERTER
    dis_file = call_service(CONVERTER_ENDPOINT, hilda_file, 'dis')

    # 4) PRODUCE RDF
    g = rst_to_rdf(dis_file, plain_file, doc_n, ns) 

    # 5) CLEAN TMP DIR
    filehandler.clean_dir(TMP_FOLDER, [plain_file, hilda_file, dis_file, ])

    return g


def salient_annotated_data(g):
    """ Queries the graph to get edus with scores and jsonify data
    """
    return rstminer.extract_saliency(g)   

def call_service(endpoint, in_file, out_file_ext):
    """ Function to call microservices
    """
    fh = filehandler.open_file(TMP_FOLDER, in_file)
    data = sender.send_file(fh, endpoint).text
    out_file = filehandler.set_extension(in_file, out_file_ext)
    filehandler.save_file(data, TMP_FOLDER, out_file)
    return out_file

def rst_to_rdf(dis_file, plain_file, doc_n, ns):
    """ Function to produce rdf graph from rst tree
    """
    rstminer.load_tree(TMP_FOLDER + '/' + dis_file)
    g = rstminer.produce_rdf(doc_n, ns, plain_text=filehandler.open_file_to_string(TMP_FOLDER, plain_file))    
    return g

# ======== TEST API ===============
@app.route("/test", methods=["GET"])
@cross_origin()
def test_request():
    return("test passed\n")

if __name__ == '__main__':
    app.run(host=HOST, threaded=True, port=PORT, debug=DEBUG)
