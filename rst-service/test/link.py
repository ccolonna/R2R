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
def get_denoted_offset(g):
    query = """ SELECT ?denoted ?offset WHERE { ?offset a ns2:PointerRange ; ns6:denotes ?denoted . } """
    qres = g.query(query)
    res = []
    for row in qres:
        res.append((row[0], get_f_offset(row[1].strip()))) # denoted, startOffset
    return res

def get_denoted_span(g, denoted_offset):
    query = """ SELECT  ?textspan ?start ?end WHERE { ?textspan rst:startOffset ?start ; rst:endOffset ?end . FILTER (?start <= """+ denoted_offset +""" && """+ denoted_offset +""" < ?end) }"""
    qres = g.query(query)
    res = []
    for row in qres:
        print(row)
        res.append((row[0], row[1].strip(), row[2].strip()))
    return res

def bridge(g):
    denoteds = get_denoted_offset(g)
    spans = get_span_boundaries(g)
    for d in denoteds:
        for s in spans:
            if s[1] <= d[1] < s[2]:
                print(s[1], d[1], s[2]) 
                print(d[0], 'belongsTo', s[0])
                g.add( (d[0] , URIRef('belongsTo'), s[0]))

denoteds = get_denoted_offset(g)

for d in denoteds:
    get_denoted_span(g, d[1])

#print g.serialize(format='n3')

