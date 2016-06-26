
from aria import print_exception, merge
from aria.tools.utils import BaseArgumentParser
from aria.parser import DefaultParser
from aria.consumer import YamlWriter
from clint.textui import puts, colored, indent
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
    puts(colored.blue('Deploying %s topology to NFV-O at %s:%s...' % (type, host, port)))
    url = 'http://%s:%d/deploy' % (host, port)
    response = requests.post(url, data=data)
    with indent(2):
        puts('Received: %s' % response.content)
    return json.loads(response.content)

def deploy_sdn_o(host, port, data):
    puts(colored.blue('Deploying to SDN-O at %s:%s...' % (host, port)))
    url = 'http://%s:%d/deploy' % (host, port)
    data = json.dumps(data)
    response = requests.post(url, data=data)
    return json.loads(response.content)

def save_yaml(name, data):
    with indent(2):
        puts('Saving %s.yaml...' % name)
    with open('%s.yaml' % name, 'w') as f:
        f.write(data)

def delete_node_template(presenter, n):
    raw = dict(presenter.service_template.topology_template.raw['node_templates'])
    del raw[n]
    presenter.service_template.topology_template.node_templates = raw

def decompose(uri):
    presentation = parse(uri)

    puts(colored.blue('Decomposing blueprint...'))
    
    pop_network = []
    for n, group in presentation.service_template.topology_template.groups.iteritems():
        if group.type == 'tosca.groups.nfv.VNFFG':
            pop_network += group.properties['constituent_vnfs'].value

    vl_presenter = presentation.clone()
    pop_presenter = presentation.clone()
    
    for n in presentation.service_template.topology_template.node_templates:
        if n in pop_network:
            delete_node_template(vl_presenter, n)
        else:
            delete_node_template(pop_presenter, n)
    
    vl_yaml = StringIO()
    YamlWriter(vl_presenter, out=vl_yaml).consume()
    vl_yaml = vl_yaml.getvalue()
    
    pop_yaml = StringIO()
    YamlWriter(vl_presenter, out=pop_yaml).consume()
    pop_yaml = pop_yaml.getvalue()
    
    save_yaml('vl', vl_yaml)
    save_yaml('pop', pop_yaml)
    
    return vl_yaml, pop_yaml

def compose(vl_topology, pop_topology):
    sdn_topology = {}
    merge(sdn_topology, vl_topology)
    merge(sdn_topology, pop_topology)
    with indent(2):
        puts('Composed: %s' % json.dumps(sdn_topology))
    return sdn_topology

def install(vl_yaml, pop_yaml):
    vl_topology = deploy_nfv_o('VL', 'localhost', 8080, vl_yaml)
    pop_topology = deploy_nfv_o('PoP', 'localhost', 8081, pop_yaml)
    
    puts(colored.blue('Composing SDN topology...'))
    
    sdn_topology = compose(vl_topology, pop_topology)

    return deploy_sdn_o('localhost', 8082, sdn_topology)

def main():
    try:
        args, unknown_args = ArgumentParser().parse_known_args()

        if args.command == 'decompose':
            vl_yaml, pop_yaml = decompose(args.uri)
        elif args.command == 'install':
            vl_yaml, pop_yaml = decompose(args.uri)
            result = install(vl_yaml, pop_yaml)
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
