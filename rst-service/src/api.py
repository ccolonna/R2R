#!python
#
# author: Christian Colonna
# 
# api classes for rst-service docker api

import os


class RDFParams(object):
    """ RDF parameters for RST model
    """
    # form keys
    DOC_NUMBER = 'doc' # this key is the number of the doc to be add to the namespace
    NAMESPACE = 'ns'
    FORMAT = 'ext'
    TRESHOLD = 's'
    # default values
    DEFAULT_FORMAT = 'n3'
    DEFAULT_TRESHOLD = 0.6
    DEFAULT_NAMESPACE = 'https://w3id.org/stlab/fred/rst/data/'

    def __init__(self, request_form):
        self.doc_n = request_form.get(self.DOC_NUMBER) if request_form.get(self.DOC_NUMBER) else 1
        self.ns = request_form.get(self.NAMESPACE) if request_form.get(self.NAMESPACE) else self.DEFAULT_NAMESPACE
        self.serialization = request_form.get(self.FORMAT) if request_form.get(self.FORMAT) else self.DEFAULT_FORMAT
        self.treshold = float(request_form.get(self.TRESHOLD)) if request_form.get(self.TRESHOLD) else self.DEFAULT_TRESHOLD

class GlobalStorage(object):

    def __init__(self):
        self.raw_text = None
        self.rdf_params = None
        self.plain_file = None
        
    def set_raw_text(self, raw_text):
        self.raw_text = raw_text
    def get_raw_text(self):
        return self.raw_text
    def set_rdf_params(self, rdf_params):
        self.rdf_params = rdf_params
    def get_rdf_params(self):
        return self.rdf_params    
    def set_plain_file(self, plain_file):
        self.plain_file = plain_file
    def get_plain_file(self):
        return self.plain_file

    
