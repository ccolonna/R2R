from rdflib import Graph, URIRef, Literal, XSD
from rdflib.namespace import Namespace, RDF

g = Graph()
fh = open("bridge_graph2", 'r')
data = ""
for line in fh:
    data += line
g.parse(data = data , format = 'n3' )

query = """ PREFIX rst: <https://rst-ontology-ns/>
            SELECT  ?textspan WHERE
	        { ?textspan rst:startOffset ?start ;
                        	  rst:endOffset ?end .
             FILTER (?start <= ?denoted_start && ?denoted_start < ?end)
	        }"""
  #    
       


qres = g.query(query, initBindings={"?denoted_start": Literal(6)})
for row in qres:
	print row

#print g.serialize(format='n3')

