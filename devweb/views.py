from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import (authenticate, get_user_model, login, logout,)
from .forms import UserLoginForm


def login_view(request):
    print(request.user.is_authenticated)
    next = request.GET.get('next')
    name = "Login"
    form = UserLoginForm(request.POST or None)
    if request.user.is_authenticated == True:
        return redirect('/')
    if form.is_valid():
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")
        user = authenticate(username=username, password=password)
        login(request, user)
        if next:
            return redirect(next)
        return redirect('/')
    return render(request, "form.html", {"form": form, "name":name})


def logout_view(request):
    logout(request);
    return redirect('/')

@login_required(login_url='/login/')
def index(request):
    return render(request, "home.html",{'user':request.user}) 


@login_required(login_url='/login/')
def elastic(request):
    import subprocess
    import sys
    #with open('elastic.log','w') as f:
    proc = subprocess.Popen(['curl','node1:9200'], stdout=subprocess.PIPE)
    print("**************************\n")
    print(str(proc))
    '''
    for c in iter(lambda: proc.stdout.read(1),''):
        sys.stdout.write(c)
        f.write(c)

    #webdoc = subprocess.check_call(['curl','node1:9200'])
    print("#######################################\n")
    print(subprocess.check_output(['curl','node1:9200']))
    print("#######################################\n")
    #return HttpResponse("Elastic")
    '''
    return HttpResponse(subprocess.check_output(['curl','node1:8080']))


@login_required(login_url='/login/')
def ambari(request):
    return HttpResponse("Ambari")

@login_required(login_url='/login')
def compile(request):
    if request.method == 'POST':
        #pdb.set_trace()
        path_name = request.POST['logpath']
        grok_regs = request.POST['regular']
        topic_name = request.POST['topics']

        print("Path: {}".format(str(path_name)))
        print("Grok: {}".format(str(grok_regs)))
        print("Topic: {}".format(str(topic_name)))
    
        ### Start Compile New Topology to Metron
        import pdb; 
        import subprocess  
        # -- initial process to vagrant ssh
        print("###### initial Procss\n\n\n")
        proc = subprocess.Popen(['vagrant','ssh'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        # -- STEP2: Create a Kafka Topic for the New Data Source
        print("\n\n\n# -- STEP2: Create a Kafa Topic")
        print("login kafka")
        command = 'sudo su -\n'
        proc.stdin.write(command.encode('utf-8'))

        print("create list")
        command = '/usr/hdp/current/kafka-broker/bin/kafka-topics.sh --zookeeper $ZOOKEEPER_HOST:2181 --create --topic {} --partitions 1 --replication-factor 1\n'.format(str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        #### can't list it now
        #command = '/usr/hdp/current/kafka-broker/bin/kafka-topics.sh --zookeeper $ZOOKEEPER_HOST:2181 --list'
        #tout = proc.stdin.write(command.encode('utf-8'))
        #print(tout)

        # -- STEP3: Create a Grok Statement to Parse the Squid Telemetry Event
        print("\n\n\n# -- STEP3: Create a Grok Statement to Parse")
        print("create tmpfile")
        command = 'touch /tmp/{}\n'.format(str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        print("input text tempfile")
        command = 'echo "{}" > /tmp/{}\n'.format(str(grok_regs),str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        # Change user to hdfs
        print("change user to hdfs")
        command = 'su - hdfs\n'
        proc.stdin.write(command.encode('utf-8'))
        print("hdfs fs")
        command = 'hadoop fs -rm -r /apps/metron/patterns/{}\n'.format(str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        print("hdfs dfs")
        command = 'hdfs dfs -put /tmp/{} /apps/metron/patterns/\n'.format(str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        print("exit from hdfs to root")
        command = 'exit\n'
        proc.stdin.write(command.encode('utf-8'))


        # -- STEP4: Parse and Transform the Squid Message
        print("\n\n\n # -- STEP4: Parse and Transform the Squid Messege")
        print("create json format")
        command = 'touch /usr/metron/0.4.0/config/zookeeper/parsers/{}.json\n'.format(str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        jsonformat = '{\n\"parserClassName\": \"org.apache.metron.parsers.GrokParser\",\n\"sensorTopic\": \"%s\",\n\"parserConfig\": {\n\"grokPath\": \"/apps/metron/patterns/%s\",\n\"patternLabel\": \"SQUID_DELIMITED\",\n\"timestampField\": \"timestamp\"\n},\n\"fieldTransformations\" : [\n{\n    \"transformation\" : \"STELLAR\"\n    ,\"output\" : [ \"full_hostname\", \"domain_without_subdomains\" ]\n    ,\"config\" : {\n                \"full_hostname\" : \"URL_TO_HOST(url)\"\n                ,\"domain_without_subdomains\" : \"DOMAIN_REMOVE_SUBDOMAINS(full_hostname)\"\n                }\n    }\n]\n}'%(str(topic_name),str(topic_name))
        print(jsonformat)
        print("write json file")
        command = 'cat > /usr/metron/0.4.0/config/zookeeper/parsers/{}.json << EOF\n{}\nEOF\n'.format(str(topic_name),str(jsonformat))
        print(command)
        proc.stdin.write(command.encode('utf-8'))
        print("PUSH to zookeeper")
        command = '/usr/metron/0.4.0/bin/zk_load_configs.sh --mode PUSH -i /usr/metron/0.4.0/config/zookeeper -z node1:2181\n'
        proc.stdin.write(command.encode('utf-8'))


        # -- STEP5: Configure Indexing
        print("\n\n\n# -- STEP5: Configure Indexing")
        print("crreate index.json")
        command = 'touch /usr/metron/0.4.0/config/zookeeper/indexing/{}.json\n'.format(str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        #print(command)
        textfill = '\n  { \n    "elasticsearch": {  \n       "index": "%s",  \n       "batchSize": 5, \n   "enabled" : true \n    }, \n    "hdfs":{ \n "index": "%s",  \n   "batchSize": 5, \n       "enabled" : true \n    } \n \n     }'%(str(topic_name),str(topic_name))
        print(textfill)
        print("write json file")
        command = 'cat > /usr/metron/0.4.0/config/zookeeper/indexing/{}.json << EOF\n{}\nEOF\n'.format(str(topic_name),str(textfill))
        proc.stdin.write(command.encode('utf-8'))
        print(command)
        #print(command)
        print("push config")
        command = '/usr/metron/0.4.0/bin/zk_load_configs.sh --mode PUSH -i /usr/metron/0.4.0/config/zookeeper -z node1:2181\n'
        proc.stdin.write(command.encode('utf-8'))


        # -- STEP6: Validate the Squid Message
        print("#\n\n\n -- STEP6: Validate the Squid Message")
        #addtext = '\n"fieldValidations" : [ \n   { \n      "input" : [ "ip_src_addr", "ip_dst_addr" ], \n      "validation" : "IP", \n      "config" : { \n      "type" : "IPV4" \n       } \n   } \n  ]'
        #command = 'eccho "{}" >> /usr/metron/0.4.0/config/zookeeper/global.json'.format(str(addtext))
        #proc.stdin.write(command.encode('utf-8'))
        #print(command)
        command = '/usr/metron/0.4.0/bin/zk_load_configs.sh -i /usr/metron/0.4.0/config/zookeeper -m PUSH -z node1:2181\n'
        proc.stdin.write(command.encode('utf-8'))
        #print(command)

        #command = '/usr/metron/0.4.0/bin/zk_load_configs.sh -m DUMP -z $ZOOKEEPER_HOST:2181'
        #proc.stdin.write(command.encode('utf-8'))
        #print(command)

        # -- STEP7:Deploy the new Parser Topology
        print("#\n\n\n -- STEP7:Deploy the new Parser Topology")
        command = '/usr/metron/0.4.0/bin/start_parser_topology.sh -k node1:6667 -z node1:2181 -s {}\n'.format(str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        #print(command)
        
        # -- LAST: Last Step 
        print("#\n\n\n -- Last STEP -- MAP LOG")
        command = 'tail {} | /usr/hdp/current/kafka-broker/bin/kafka-console-producer.sh --broker-list node1:6667 --topic {}\n'.format(str(path_name),str(topic_name))
        proc.stdin.write(command.encode('utf-8'))

        # Map whois 
        whois_str = '\n{\n     "zkQuorum" : "node1:2181"\n    ,"sensorToFieldList" : {\n          "%s" : {\n             "type" : "ENRICHMENT"\n            ,"fieldToEnrichmentTypes" : {\n                 "domain_without_subdomains" : [ "whois" ]\n              }\n          }\n    }\n}'%(str(topic_name))
        command = 'cat > /usr/whois/enrichment_config_whois_{}.json << EOF\n{}\nEOF\n'.format(str(topic_name),str(whois_str))
        proc.stdin.write(command.encode('utf-8'))

        command = 'iconv -c -f utf-8 -t ascii /usr/whois/enrichment_config_whois_{}.json -o /usr/whois/enrichment_config_whois_{}.json'.format(str(topic_name),str(topic_name))
        proc.stdin.write(command.encode('utf-8'))
        command = '/usr/metron/0.4.0/bin/flatfile_loader.sh -n /usr/whois/enrichment_config_whois_{}.json -i /usr/whois/whois_ref.csv -t enrichment -c t -e /usr/whois/extractor_config_whois.json'.format(str(topic_name))
        proc.stdin.write(command.encode('utf-8'))

        # Check output form the proc
        print("\n\n\n\n ***** Output ****")
        outs, errs = proc.communicate(timeout=None)
        print("**************************************\n")
        print('outs: {}\n\n'.format(str(outs)))
        print('errs:{}\n\n'.format(str(errs)))

        return render(request, "addtelemetry.html", {'status': 'Complete'})

    status = 'No Things to do'
    return render(request, "addtelemetry.html", {'status': status})
