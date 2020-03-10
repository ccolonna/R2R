from rdflib import Graph, URIRef, Literal, XSD
from rdflib.namespace import Namespace, RDF


g = Graph()
fh = open("bridge_graph", 'r')
data = ""
for line in fh:
    data += line
g.parse(data = data , format = 'n3' )


def get_f_offset(s):
    return s.split('_')[1]


# works!
def get_denoted_and_start_offset(g):
    """ In a FRED graph we extract the tuple of all denoteds and relative position
        [(denoted_1, start),(denoted_2, start),...  ] 
    """
    query = """ SELECT ?denoted ?offset WHERE { ?offset a ns2:PointerRange ; ns6:denotes ?denoted . } """
    qres = g.query(query)
    res = []
    for row in qres:
        res.append((row[0], get_f_offset(row[1].strip()))) # denoted, startOffset
    return res

def get_denoted_edu(g, denoted_tuple):
    """ Extract the edu (nucleus or satellite), the denoted belongs to. 
        And creates a relation of membership.
        Example:
         N1 |  i'm hungry , | S1 so i eat an apple.
        apple belongsTo S1
    """
    query = """ SELECT  ?textspan WHERE { ?textspan rst:startOffset ?start ; rst:endOffset ?end . FILTER (?start <= ?denoted_start && ?denoted_start < ?end) }"""
    qres = g.query(query, initBindings={"?denoted_start":Literal(denoted_tuple[1])})
    for row in qres:
        print row[0].strip(), denoted_tuple[0]

# def bridge(g):
#     denoteds = get_denoted_offset(g)
#     spans = get_span_boundaries(g)
#     for d in denoteds:
#         for s in spans:
#             if s[1] <= d[1] < s[2]:
#                 print(s[1], d[1], s[2]) 
#                 print(d[0], 'belongsTo', s[0])
#                 g.add( (d[0] , URIRef('belongsTo'), s[0]))

denoteds = get_denoted_and_start_offset(g) #[(d, start), ...]


for d in denoteds:
    get_denoted_edu(g, d)

#print g.serialize(format='n3')

