
from aria import print_exception, merge
from aria.tools.utils import BaseArgumentParser
from aria.parser import DefaultParser
from aria.presenter.tosca import ToscaSimplePresenter1_0, TopologyTemplate
from aria.consumer import YamlWriter
from clint.textui import puts, colored, indent
from copy import deepcopy
from cStringIO import StringIO
import requests, json

class ArgumentParser(BaseArgumentParser):
    def __init__(self):
        super(ArgumentParser, self).__init__(description='CLI', prog='gs-o')
        self.add_argument('command', help='commmand')
        self.add_argument('uri', help='URI or file path to profile')

def parse(uri):
    puts(colored.blue('Parsing blueprint from "%s"...' % uri))
    
    parser = DefaultParser(uri)
    presentation, issues = parser.validate()
        
    if issues:
        puts(colored.red('Validation errors:'))
        with indent(2):
            for issue in issues:
                puts('%s' % issue)
        exit(0)
    
    return presentation

def deploy_nfv_o(type, host, port, data):
    puts(colored.blue('Deploying %s to NFV-O at %s:%s...' % (type, host, port)))
    url = 'http://%s:%d/deploy' % (host, port)
    response = requests.post(url, data=data)
    return json.loads(response.content)

def deploy_sdn_o(host, port, data):
    puts(colored.blue('Deploying to SDN-O at %s:%s...' % (host, port)))
    url = 'http://%s:%d/deploy' % (host, port)
    data = json.dumps(data)
    response = requests.post(url, data=data)
    return json.loads(response.content)

def decompose(uri):
    presentation = parse(uri)

    puts(colored.blue('Decomposing blueprint...'))
    
    vnf_network = []
    for n, group in presentation.service_template.topology_template.groups.iteritems():
        if group.type == 'tosca.groups.nfv.VNFFG':
            vnf_network += group.properties['constituent_vnfs'].value

    vl_presenter = ToscaSimplePresenter1_0(deepcopy(presentation.raw))
    vnf_presenter = ToscaSimplePresenter1_0(deepcopy(presentation.raw))
    
    for n in presentation.service_template.topology_template.node_templates:
        if n in vnf_network:
            raw = dict(vl_presenter.service_template.topology_template.raw['node_templates'])
            del raw[n]
            vl_presenter.service_template.topology_template.node_templates = raw
        else:
            raw = dict(vnf_presenter.service_template.topology_template.raw['node_templates'])
            del raw[n]
            vnf_presenter.service_template.topology_template.node_templates = raw
    
    vl_yaml = StringIO()
    YamlWriter(vl_presenter, out=vl_yaml).consume()
    vl_yaml = vl_yaml.getvalue()
    
    vnf_yaml = StringIO()
    YamlWriter(vl_presenter, out=vnf_yaml).consume()
    vnf_yaml = vnf_yaml.getvalue()
    
    return vl_yaml, vnf_yaml

def install(vl_yaml, vnf_yaml):
    vl_topology = deploy_nfv_o('VL', 'localhost', 8080, vl_yaml)
    vnf_topology = deploy_nfv_o('VNF', 'localhost', 8081, vnf_yaml)
    
    puts(colored.blue('Composing SDN topology...'))
    
    sdn_topology = {}
    merge(sdn_topology, vl_topology)
    merge(sdn_topology, vnf_topology)

    return deploy_sdn_o('localhost', 8082, sdn_topology)

def main():
    try:
        args, unknown_args = ArgumentParser().parse_known_args()

        if args.command == 'decompose':
            vl_yaml, vnf_yaml = decompose(args.uri)
        elif args.command == 'install':
            vl_yaml, vnf_yaml = decompose(args.uri)
            result = install(vl_yaml, vnf_yaml)
            puts('Successful deployments:')
            with indent(2):
                for deployment in result['deployments']:
                    puts(deployment)
        else:
            raise Exception('unknown command: %s' % args.command)

    except Exception as e:
        print_exception(e)

if __name__ == '__main__':
    main()
