import conf
import urllib.request
import rdflib

class FREDParameters:
    def __init__(self, 
                 output=None, 
                 format=conf.DEFAULT_SERIALIZATION, 
                 prefix=conf.DEFAULT_FRED_PREFIX,
                 namespace=conf.DEFAULT_FRED_NAMESPACE,
                 ctxNamespaces=False,
                 wsd=True):
        self.__output = output
        self.__format = format
        self.__namespace = namespace
        self.__ctxNamespaces = ctxNamespaces,
        self.__wsd = wsd
    
    def getOutput(self):
        return self.__output
    
    def setOutput(self, output):
        self.__output = output
        
    def getFormat(self):
        return self.__format
    
    def setFormat(self, format):
        self.__format = format
        
    def getNamespace(self):
        return self.__namespace
    
    def setNamespace(self, namespace):
        self.__namespace = namespace
        
    def isCtxNamespaces(self):
        return self.__ctxNamespacesctxNamespaces
    
    def setCtxNamespaces(self, ctxNamespaces):
        self.__ctxNamespaces = ctxNamespaces
        
    def isWSD(self):
        return self.__wsd
    
    def setWSD(self, wsd):
        self.__wsd = wsd 

class FREDDialer:
    def __init__(self, fred_endpoint = conf.FRED_ENDPOINT, requestMimeType=conf.DEFAULT_FRED_SERIALIZATION_OUPUT):
        self.__fred_endpoint = fred_endpoint + "?%s"
        self.__requestMimeType = requestMimeType
    
    def dial(self, text, fredParameters=FREDParameters()):
        params = {'text': text, 
             'namespace': fredParameters.getNamespace(),
             'wsd': fredParameters.isWSD()}
        
       	params = urllib.parse.urlencode(params)
        
        print(self.__fred_endpoint % params)
        graph=rdflib.Graph()
        request = urllib.request.Request(self.__fred_endpoint % params, headers={"Accept": self.__requestMimeType})
        try:
            response = urllib.request.urlopen(request)
            output = response.read()
            
            graph.parse(data = output, format=self.__requestMimeType)
        except:
            print("The graph produced is empty due to an exception occurred with FRED.")
        return graph