import argparse
import getpass
import json
import os
import sys
from .core import Agent, Model, Store
from .server import serve

def main():
    parser=argparse.ArgumentParser(prog='opendeveloper',description='Analyze → differentiate → approve → build')
    parser.add_argument('--home',help='Project data directory')
    sub=parser.add_subparsers(dest='command',required=True)
    web=sub.add_parser('serve'); web.add_argument('--port',type=int,default=8765); web.add_argument('--no-browser',action='store_true')
    plan=sub.add_parser('plan'); plan.add_argument('url'); plan.add_argument('--brief',default='')
    revise=sub.add_parser('revise'); revise.add_argument('id'); revise.add_argument('feedback')
    for name in ('show','approve','build'):
        cmd=sub.add_parser(name); cmd.add_argument('id')
    sub.add_parser('list')
    login=sub.add_parser('connect'); login.add_argument('--base-url',required=True); login.add_argument('--model',required=True)
    args=parser.parse_args()
    if args.home: os.environ['OPENDEVELOPER_HOME']=args.home
    try:
        if args.command=='serve': return serve(args.port,not args.no_browser)
        if args.command=='connect':
            # Keep credentials only in this process, then launch the localhost app.
            from .server import App,make_server
            app=App(); app.config={'base_url':args.base_url,'model':args.model,'token':getpass.getpass('API key (hidden): ')}
            server=make_server(app=app)
            print('Connected for this process. Open http://127.0.0.1:8765'); server.serve_forever(); return
        store=Store(); agent=Agent(store,Model())
        if args.command=='plan': result=agent.plan(args.url,args.brief)
        elif args.command=='revise': result=agent.revise(args.id,args.feedback)
        elif args.command=='show': result=store.get(args.id)
        elif args.command=='list': result=store.list()
        elif args.command=='approve':
            p=store.get(args.id); print(json.dumps(p['plan'],ensure_ascii=False,indent=2))
            if input('Approve this exact plan? Type APPROVE: ')!='APPROVE': print('Not approved.'); return
            result=agent.approve(args.id,p['revision'])
        else:
            result=agent.build(args.id); print('Download files:',store.root/args.id/'project.zip')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except KeyboardInterrupt: print('\nStopped.'); return 130
    except Exception as e:
        print('Error: '+(str(e) if isinstance(e,ValueError) else 'Operation failed. Check configuration and network.'),file=sys.stderr); return 1

if __name__=='__main__': sys.exit(main())
