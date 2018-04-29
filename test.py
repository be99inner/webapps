topic_name = 'test'

whois_str = '\n{\n     "zkQuorum" : "node1:2181"\n    ,"sensorToFieldList" : {\n          "%s" : {\n             "type" : "ENRICHMENT"\n            ,"fieldToEnrichmentTypes" : {\n                 "domain_without_subdomains" : [ "whois" ]\n              }\n          }\n    }\n}'%(str(topic_name))
command = 'cat > enrichment_config_whois_{}.json << EOF\n{}\nEOF\n'.format(str(topic_name),str(whois_str))
print(command)
