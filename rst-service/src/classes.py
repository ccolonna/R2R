#! python
#
# author: Christian Colonna
# 
# classes for rst-service docker api

import os

from edualigner import RSTEDUAligner

import requests
from rstmarcutree import load_tree as load_rst_file
from werkzeug.utils import secure_filename
from rdflib import Graph, URIRef, Literal, XSD
from rdflib.namespace import Namespace

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
    
    def set_extension(self, filename, extension):
        f_root = filename.split(".")[0]
        return f_root + '.' + extension
    
    def open_file_to_string(self, folder, filename):
        fh = open(os.path.join(folder, filename), 'r')
        raw_file = ''
        for line in fh:
            raw_file += line
        return raw_file


class DataSender(object):
    """ Handle data broadcasting over http between docker api. Send files, binaries...
    """

    def send_file(self, fh, url):
        return requests.post(url, files={'input': fh})

class RSTMiner(object):
    """ Take rst tree and produce rdf
    """
    
    DEFAULT_NAMESPACE = 'https://w3id.org/stlab/fred/rst/data/'
    
    def __init__(self):
        self.tree = None

    def load_tree(self, filepath):
        """ Bind internal tree attribute to tree
        """
        self.tree = load_rst_file(filepath)
        return self.tree
    
    def produce_rdf(self, doc_ns, ns=DEFAULT_NAMESPACE, plain_text=None):
        """ doc_ns is document namespace added to the base default namespace. A solution? Simply give a number as string.
            If you parse a corpora set up a counter and give a number for every document
        """
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
        doc_ns = Namespace(ns + doc_ns + '/')
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
            else:
                tn = 'satellite_' + str(node_hash_map[terminal_node.index])
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



