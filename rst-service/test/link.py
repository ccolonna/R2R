from rdflib import Graph, URIRef, Literal, XSD
from rdflib.namespace import Namespace, RDF

g = Graph()
fh = open("bridge_graph", 'r')
data = ""
for line in fh:
    data += line
g.parse(data = data , format = 'n3' )

class BridgeGraph(Graph):

    def merge(self, rst_data, fred_data, in_ext):
        self.parse(data = rst_data, format=in_ext)
        self.parse(data = fred_data, format=in_ext)
        self.__bridge()

    def __get_fred_offset(self, s):
        return s.split('_')[1]

    def __get_denoted_and_start_offset(self):
        """ In a FRED graph we extract the tuple of all denoteds and relative position
            [(denoted_1, start),(denoted_2, start),...  ] 
        """
        query = """ SELECT ?denoted ?offset WHERE { ?offset a ns2:PointerRange ; ns6:denotes ?denoted . } """
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
        query = """ SELECT  ?textspan WHERE { ?textspan rst:startOffset ?start ; rst:endOffset ?end . FILTER (?start <= ?denoted_start && ?denoted_start < ?end) }"""
        qres = self.query(query, initBindings={"?denoted_start":Literal(denoted_tuple[1])})
        for row in qres:
            # ============== add membership triple ==================
            self.add( (denoted_tuple[0], URIRef('belongsTo'), row[0] )) 

    def __bridge(self):
        """ Add a membership relation between R2R edu's and FRED objects and facts
        """ 
        denoteds = self.__get_denoted_and_start_offset()
        for d in denoteds:
            self.__get_denoted_edu(d)

# def get_f_offset(s):
#     return s.split('_')[1]


# # works!
# def get_denoted_and_start_offset(g):
#     """ In a FRED graph we extract the tuple of all denoteds and relative position
#         [(denoted_1, start),(denoted_2, start),...  ] 
#     """
#     query = """ SELECT ?denoted ?offset WHERE { ?offset a ns2:PointerRange ; ns6:denotes ?denoted . } """
#     qres = g.query(query)
#     res = []
#     for row in qres:
#         res.append((row[0], get_f_offset(row[1].strip()))) # denoted, startOffset
#     return res

# def get_denoted_edu(g, denoted_tuple):
#     """ Extract the edu (nucleus or satellite), the denoted belongs to. 
#         And creates a relation of membership.
#         Example:
#          N1 |  i'm hungry , | S1 so i eat an apple.
#         apple belongsTo S1
#     """
#     query = """ SELECT  ?textspan WHERE { ?textspan rst:startOffset ?start ; rst:endOffset ?end . FILTER (?start <= ?denoted_start && ?denoted_start < ?end) }"""
#     qres = g.query(query, initBindings={"?denoted_start":Literal(denoted_tuple[1])})
#     for row in qres:
#         # ============== add membership triple ==================
#         g.add( (denoted_tuple[0], URIRef('belongsTo'), row[0] )) 


# def bridge(g):
#     denoteds = get_denoted_and_start_offset(g)
#     for d in denoteds:
#         get_denoted_edu(g, d)

# bridge(g)

# print g.serialize(format='n3')

