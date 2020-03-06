#! python
#
# author: Christian Colonna
# 
# classes for rst-service docker api

import os

from edualigner import RSTEDUAligner
from PyFred import FREDDialer

import requests
from nltk.tokenize import word_tokenize
from rstmarcutree import load_tree as load_rst_file
from werkzeug.utils import secure_filename
from rdflib import Graph, URIRef, Literal, XSD
from rdflib.namespace import Namespace, RDF

class FileHandler(object):

    def open_file(self, folder, filename):
        """ Open file in binary mode. You need this to send it via HTTP POST request.
        """
        return open(os.path.join(folder, filename), 'rb')

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
        fh = open(os.path.join(folder, filename), 'r')
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
            plain_file = "plain.txt"
            self.save_file(request.form.get(filekey), folder, "plain.txt")
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

class RDFParams(object):
    """ RDF parameters for RST model
    """
    DOC_NUMBER = 'doc' # this key is the number of the doc to be add to the namespace
    NAMESPACE = 'ns'
    DEFAULT_NAMESPACE = 'https://w3id.org/stlab/fred/rst/data/'
    FORMAT = 'ext'
    DEFAULT_FORMAT = 'n3'
    def __init__(self, request_form):
        self.doc_n = request_form.get(self.DOC_NUMBER) if request_form.get(self.DOC_NUMBER) else 1
        self.ns = request_form.get(self.NAMESPACE) if request_form.get(self.NAMESPACE) else self.DEFAULT_NAMESPACE
        self.serialization = request_form.get(self.FORMAT) if request_form.get(self.FORMAT) else self.DEFAULT_FORMAT

class RSTMiner(object):
    """ Take rst tree and produce rdf
    """

    def load_tree(self, filepath):
        """ Bind internal tree attribute to tree
        """
        self.tree = load_rst_file(filepath)
        return self.tree
    
    def produce_rdf(self, doc_number, ns, dis_file_path, plain_text=None):
        """ 
            ns is namespace for parsed document default is: https://w3id.org/stlab/fred/rst/data/

            doc_number is document number added to the base namespace.
            If you parse a corpora set up a counter and give a number for every document
        """
        self.tree = self.load_tree(dis_file_path)

        rst = Namespace('https://rst-ontology-ns/') # rst ontology namespace
        
        ### LAMBDA FILTERS
        multinuc_relation_filter = lambda node : node if node.schema == 'MULTINUC' else None
        nuclear_relation_filter = lambda node : node if node.schema == 'DEP' else None
        terminal_node_filter = lambda node : node if node.is_terminal() else None

        if plain_text:
            offsets = RSTEDUAligner.get_original_edu_offsets(self.tree.get_edus(), plain_text)
        else:
            raise NotImplementedError("Miss a way to get offsets from Feng. Gotta open their code with STafordNLP tokenizer")

        ### PARAMS
        s_count = 1
        n_count = 1
        node_hash_map = {} # a map with node index and its counter    
        doc_ns = Namespace(ns + str(doc_number) + '/')
        g = Graph()
        g.bind('rst', rst)

        # ======== ADD TRIPLE ======== (nucleus relation nucleus)
        for relation in self.tree.get_node(filter_func=multinuc_relation_filter):
            # nuc 1
            n_left = relation.get_nucleus()[0] 
            node_hash_map[n_left.index] = n_count
            n_left = 'nucleus_' + str(n_count)
            n_count += 1
            # nuc 2
            n_right = relation.get_nucleus()[1]
            node_hash_map[n_right.index] = n_count
            n_right = 'nucleus_' + str(n_count)
            n_count += 1

            g.add( ( doc_ns[n_right], RDF.type, rst.Nucleus ))
            g.add( ( doc_ns[n_left] , RDF.type, rst.Nucleus ))
            g.add( ( doc_ns[n_left], rst[self.camelize_relation(relation.relation)], doc_ns[n_right] ) )
            
        # ======= ADD TRIPLE (nucleus relation satellite)
        for relation in self.tree.get_node(filter_func=nuclear_relation_filter):
            # nuc
            n = relation.get_nucleus()
            node_hash_map[n.index] = n_count
            n = 'nucleus_' + str(n_count)
            n_count += 1
            # sat
            s = relation.get_satellite()
            node_hash_map[s.index] = s_count
            s = 'satelite_' + str(s_count)
            s_count += 1
            
            g.add( ( doc_ns[n], RDF.type, rst.Nucleus ))
            g.add( ( doc_ns[s], RDF.type, rst.Satellite))
            g.add( (doc_ns[n], rst[self.camelize_relation(relation.relation)], doc_ns[s] ) )

        # === ADD TRIPLES (terminal_node offset Literal(tuple))
        #                                       score Literal(score))
        #                                       text Literal(text)
        for terminal_node in self.tree.get_node(filter_func=terminal_node_filter):
            
            # TODO: REFACTOR
            offset =  RSTEDUAligner.get_edu_offset(offsets,terminal_node.index)
            text = plain_text[offset[0]:offset[1]]

            if terminal_node.status == 'N':
                tn = 'nucleus_' + str(node_hash_map[terminal_node.index])
                tnclass = 'Nucleus'
            else:
                tn = 'satellite_' + str(node_hash_map[terminal_node.index])
                tnclass = 'Satellite'
            g.add( (doc_ns[tn], RDF.type, rst[tnclass]))
            g.add( ( doc_ns[tn], rst.startOffset, Literal(str(offset[0])) ) )
            g.add( ( doc_ns[tn], rst.endOffset, Literal(str(offset[1])) ) )
            g.add( ( doc_ns[tn], rst.text, Literal(text) ) )
            g.add( ( doc_ns[tn], rst.score, Literal(terminal_node.get_saliency_score(),datatype=XSD.float ) ) )
        
        return g

    def camelize_relation(self, relation):
        """ Return relation in camel case notation
        """
        relation = relation.lower()
        if '-' in relation:
            tmp_relation = relation.split('-')
            tmp_relation = ''.join(map(lambda s : s.capitalize(), tmp_relation))
            relation = tmp_relation[:1].lower() + tmp_relation[1:]
        return relation

    def extract_saliency(self, g):
        """ Send edus with saliency score and an heat-map blue-red color. Serialized as json.
        """
        def get_heat_color(value):
            """ Function accepts a value in (0,1] and returns an heat color according
                to a binary gradient blue-red (blue : 0 , red : 1) 
            """
            aR, aG, aB = (0, 0, 255)
            bR, bG, bB = (255, 0, 0)
            red = ((bR - aR) * value) + aR
            green = ((bG - aG) * value) + aG
            blue = ((bB - aB) * value) + aB
            return (red, green, blue)

        QUERY = """ 
            SELECT DISTINCT ?o ?t ?s
            WHERE {
                ?n rst:startOffset ?o .
                ?n rst:text ?t .
                ?n rst:score ?s .
            }
        """
        data = g.query(QUERY)
        data2send = []
        fltr = lambda t : int(t.o)
        for row in sorted(data, key=fltr):
            data2send.append({ 'text' : word_tokenize(row.t) , 'score' : row.s , 'heat_color' : get_heat_color(float(row.s))})
        return { 'edus' : data2send }


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
        

class BridgeGraph(Graph):

    def merge(self, rst_data, fred_data, in_ext):
        Q1 = """ SELECT ?offset ?denoted WHERE { ?offset a ns4:PointerRange . }
             """
        self.parse(data = rst_data, format=in_ext)
        self.parse(data = fred_data, format=in_ext)
    


