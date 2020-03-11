#!python
#
# author: Christian Colonna
# 
# RST classes for rst-service api

from nltk.tokenize import word_tokenize
from rstmarcutree import load_tree as load_rst_file
from rdflib import Graph, URIRef, Literal, XSD
from rdflib.namespace import Namespace, RDF
from edualigner import RSTEDUAligner
from PyFred import FREDDialer

# TODO :
# this namespace is used by two classes
# you need to take it from the graph cause
# g.add() doesn't see it if you didn't declare it
rst = Namespace('https://rst-ontology-ns/') # rst ontology namespace

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
            g.add( ( doc_ns[tn], rst.startOffset, Literal(str(offset[0]), datatype=XSD.nonNegativeInteger) ) )
            g.add( ( doc_ns[tn], rst.endOffset, Literal(str(offset[1]), datatype=XSD.nonNegativeInteger) ) )
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

        query = """ 
                SELECT DISTINCT ?o ?t ?s
                WHERE {
                    ?n rst:startOffset ?o .
                    ?n rst:text ?t .
                    ?n rst:score ?s .
                }
                """
        data = g.query(query)
        data2send = []
        fltr = lambda t : int(t.o)
        for row in sorted(data, key=fltr):
            data2send.append({ 'text' : word_tokenize(row.t) , 'score' : row.s , 'heat_color' : get_heat_color(float(row.s))})
        return { 'edus' : data2send }

    def extract_facts(self, g, saliency_treshold):
	def clean_uri(uri):
		return uri.split("/")[-1]

        query = """
                PREFIX rst: <https://rst-ontology-ns/> 
                PREFIX dul: <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>
                PREFIX vnrole: <http://www.ontologydesignpatterns.org/ont/vn/abox/role/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                SELECT ?event ?agent ?patient ?location
                WHERE {
                    ?event rst:belongsTo ?edu ;
                            rdf:type ?class ;
                            vnrole:Agent ?agent ;
                            vnrole:Location ?location ;
                            ?objectPredicate ?patient .
                    ?edu rst:score ?s .
                    ?class rdfs:subClassOf dul:Event .

                    FILTER ( ?s >=  ?saliency_threshold && ?objectPredicate in (vnrole:Patient , vnrole:Theme) )
                }
                """
        data = g.query(query, initBindings={"?saliency_threshold":Literal(saliency_treshold, datatype=XSD.float)})
        data2send = []

        for row in data:
            data2send.append({ 'event':clean_uri(row.event), 'agent':clean_uri(row.agent), 'patient':clean_uri(row.patient), 'location':clean_uri(row.location)})
        return { 'important_facts' : data2send }

class BridgeGraph(Graph):

    def merge(self, rst_data, fred_data, in_ext):
        self.parse(data = rst_data, format=in_ext)
        self.parse(data = fred_data, format=in_ext)
        self.__bridge()
        return self

    def __get_fred_offset(self, s):
        return s.split('_')[1]

    def __get_denoted_and_start_offset(self):
        """ In a FRED graph we extract the tuple of all denoteds and relative position
            [(denoted_1, start),(denoted_2, start),...  ] 
        """

        query = "PREFIX earmark: <http://www.essepuntato.it/2008/12/earmark#>" \
                "PREFIX semiotics: <http://ontologydesignpatterns.org/cp/owl/semiotics.owl#>" \
                "SELECT ?denoted ?offset WHERE { ?offset a earmark:PointerRange ; semiotics:denotes ?denoted . } "
        qres = self.query(query)

        res = []
        
        for row in qres:
            res.append((row[0], self.__get_fred_offset(row[1].strip()))) # denoted, startOffset
        return res

    def __get_denoted_edu(self, denoted_tuple):
        """ Extract the edu (nucleus or satellite), the denoted belongs to. 
            And creates a relation of membership.
            Example:
            N1 |  i'm hungry , | S1 so i eat an apple.
            apple belongsTo S1
        """
        query = "PREFIX rst: <https://rst-ontology-ns/>" \
                " SELECT  ?textspan WHERE { ?textspan rst:startOffset ?start ; rst:endOffset ?end . FILTER (?start <= ?denoted_start && ?denoted_start < ?end) }"
        qres = self.query(query, initBindings={"?denoted_start":Literal(denoted_tuple[1], datatype=XSD.nonNegativeInteger)})
        #import pdb; pdb.set_trace()

        for row in qres:
            # ============== add membership triple ==================
            self.add( (denoted_tuple[0], rst['belongsTo'], row[0] )) 

    def __bridge(self):
        """ Add a membership relation between R2R edu's and FRED objects and facts
        """ 
        denoteds = self.__get_denoted_and_start_offset() # seeing this with pdb eat_1 is inside the denoteds

        for d in denoteds:
            self.__get_denoted_edu(d)
