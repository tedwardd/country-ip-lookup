#!/usr/bin/env python3

import maxminddb
import configparser
import os
import ipaddress
import requests
from requests.models import HTTPBasicAuth
import tarfile
import io
import sys
import argparse

# Set a default value for config file of "config.ini" in the current working directory
CONFIG_FILE = os.path.join(os.path.abspath(__file__), "config.ini")

# Parse args
parser = argparse.ArgumentParser(prog="lookup")
parser.add_argument("-c", "--config", dest="config_file", type=str, help="Config file path", required=False, default=None)
parser.add_argument("-d", "--db", dest="db_file", type=str, help="GeoIP database path", required=False, default=None)
args = parser.parse_args()

#init configparser instance
config = configparser.ConfigParser()
use_db_cache = False
if args.db is not None:
    use_db_cache = True


def env_to_conf(config: configparser.ConfigParser, vars: list) -> configparser.ConfigParser:
    # Take in a configparser and list of envronment variable suffixes to
    # lookup and add to the configparser. Return configparser
    for var in vars:
        if config.defaults().get(var) is None and os.getenv(f"LOOKUP_{var.upper()}") is not None:
            config.set("DEFAULT", var, os.getenv(f"LOOKUP_{var.upper()}"))

    return config


required_opts: list = ["permalink", "user", "key"]
# if config file was not given as runtime arg, use defaul value
if args.config_file is None:
    config_file = CONFIG_FILE

# if the config file exists and is a file, read it
if os.path.isfile(config_file):
    config.read(config_file)

# pass the required_opts to env_to_conf() to override config values with env vars
config = env_to_conf(config, required_opts)

# Finally, validate that we have all the keys we need between the config file
# and the environment variables and raise an exception if any are missing
for opt in required_opts:
    try:
        config.defaults()[opt]
    except KeyError as e:
        print(f"required value: `{opt}` is missing from {config_file} and is not defined as an environment variable", file=sys.stdout)
        raise e

# Ignore the unbound variable warning because pyright is just stupid here when used in conjunction with argparse
#pyright: reportUnboundVariable=false
permalink = config.defaults().get('permalink')
user = config.defaults().get('user')
key = config.defaults().get('key')

if permalink is not None and user is not None and key is not None:
    if not use_db_cache:
        response = requests.get(permalink, auth = HTTPBasicAuth(user, key))
        database = b""
        if response.status_code != 200:
            print(f'non-200 return code {str(response.status_code)}.', file=sys.stdout)
            sys.exit(1)

        content = response.content
        tario = io.BytesIO(content)
    else:
        with open(args.db, "rb") as f:
            tario = io.BytesIO(f.read())
else:
    # Catch case that should never happen
    raise Exception("Despite best efforts, we somehow still have missing required values. Check your config")

with tarfile.open(fileobj=tario) as tf:
    for file in tf.getnames():
        if '.mmdb' in file:
            member = tf.getmember(file)
            if member.isfile():
                file = tf.extractfile(member)
                if file is not None:
                    with io.BytesIO(file.read()) as f:
                        database = f.read()

reader = maxminddb.open_database(database)
countries = []
for i in reader.__iter__():
    try:
        if type(i[0]) == ipaddress.IPv4Network and i[1].get('registered_country').get('iso_code') == 'US':
            countries.append({'country': i[1].get('registered_country').get('iso_code'), 'ip': i[0]})
    except:
        continue
