from __future__ import print_function
import argparse
import json
from fictrac_vendomatic import FicTracVendomatic
from fake_fictrac import FakeFicTrac

def vendomatic_app():

    parser = argparse.ArgumentParser(description='Fictrac client for triggering "food" stimulus')
    parser.add_argument('-c','--config', help='json configuration file')
    
    args = parser.parse_args()
    
    config_dict = None
    if args.config is not None:
        with open(args.config,'r') as f:
            config_dict = json.load(f)
    
    if config_dict is None:
        client = FicTracVendomatic()
    else:
        client = FicTracVendomatic(param=config_dict)
    client.run()


def fake_fictrac_app():

    parser = argparse.ArgumentParser(description='Fake Fictrac publisher for testing vendomatic')
    parser.add_argument('-c','--config', help='json configuration file')
    
    args = parser.parse_args()
    
    config_dict = None
    if args.config is not None:
        with open(args.config,'r') as f:
            config_dict = json.load(f)
    
    if config_dict is None:
        faker = FakeFicTrac()
    else:
        faker = FakeFicTrac(param=config_dict)
    faker.run()
