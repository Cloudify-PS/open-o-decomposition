
from aria import print_exception
from aria.tools.utils import BaseArgumentParser
from aria.tools.rest_server import start_server
from clint.textui import puts, colored, indent
from dsl_parser.tasks import generate_id
from time import sleep

def deploy_post(handler):
    payload = handler.get_json_payload()
    r = {'deployments': []}
    for endpoint in payload['endpoints']:
        r['deployments'].append(endpoint)
    sleep(1)
    return r
    
ROUTES = {
    r'^/$': {'file': 'index.html', 'media_type': 'text/html'},
    r'^/deploy': {'POST': deploy_post, 'media_type': 'application/json'}}

class ArgumentParser(BaseArgumentParser):
    def __init__(self):
        super(ArgumentParser, self).__init__(description='SDN-O Server', prog='sdn-o')
        self.add_argument('--port', type=int, default=8082, help='HTTP port')
        self.add_argument('--root', default='.', help='web root directory')

def main():
    try:
        global args
        args, unknown_args = ArgumentParser().parse_known_args()
        start_server(ROUTES, args.port, args.root)

    except Exception as e:
        print_exception(e)

if __name__ == '__main__':
    main()
