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

def env_to_conf(config: configparser.ConfigParser, vars: list) -> configparser.ConfigParser:
    # Take in a configparser and list of envronment variable suffixes to
    # lookup and add to the configparser. Return configparser
    for var in vars:
        if config.defaults().get(var) is None and os.getenv(f"LOOKUP_{var.upper()}") is not None:
            config.set("DEFAULT", var, os.getenv(f"LOOKUP_{var.upper()}"))

    return config
    
    
# Ignore the unbound variable warning because pyright is just stupid here when used in conjunction with argparse
#pyright: reportUnboundVariable=false
class IPList():
    def __init__(self, permalink, user, key, db_cache=None):
        self.permalink = permalink
        self.user = user
        self.key = key
        self.db_cache = db_cache
        self.ip_list: dict = self._build_ip_list()

    def _build_ip_list(self) -> dict:
        database = b""
        tario = ""
        if self.permalink is not None and self.user is not None and self.key is not None:
            if self.db_cache is None:
                response = requests.get(self.permalink, auth = HTTPBasicAuth(self.user, self.key))
                if response.status_code != 200:
                    print(f'non-200 return code {str(response.status_code)}.', file=sys.stdout)
                    sys.exit(1)
        
                content = response.content
                tario = io.BytesIO(content)
                with tarfile.open(fileobj=tario) as tf:
                    for file in tf.getnames():
                        if '.mmdb' in file:
                            member = tf.getmember(file)
                            if member.isfile():
                                file = tf.extractfile(member)
                                if file is not None:
                                    with io.BytesIO(file.read()) as f:
                                        database = f.read()
        else:
            # Catch case that should never happen
            raise Exception("Despite best efforts, we somehow still have missing required values. Check your config")
        
        
        if self.db_cache is not None:
            reader = maxminddb.open_database(self.db_cache)
        countries = {}
        for i in reader.__iter__():
            if type(i[0]) == ipaddress.IPv4Network:
                cr = i[1]
                if type(cr) != dict:
                    continue
                rc = cr.get('registered_country')
                if type(rc) != dict:
                    continue

                iso_code = rc.get('iso_code')
                try:
                    countries[iso_code].append(i[0].exploded)
                except KeyError:
                    countries[iso_code] = [i[0].exploded]

        
        return countries

    def get_country(self, country) -> list:
        country_list = self.ip_list.get(country)
        return country_list if country_list is not None else []

def main():
    # Parse args
    parser = argparse.ArgumentParser(prog="lookup")
    parser.add_argument("-c", "--country", type=str, help="Country to find IPs for", required=True)
    parser.add_argument("--config", dest="config_file", type=str, help="Config file path", required=False, default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini"))
    parser.add_argument("-d", "--db", dest="db_cache", type=str, help="GeoIP database path", required=False, default=None)
    args = parser.parse_args()
    
    #init configparser instance
    config = configparser.ConfigParser()
    
    required_opts: list = ["permalink", "user", "key"]
    
    # if the config file exists and is a file, read it
    if os.path.isfile(args.config_file):
        config.read(args.config_file)
    
    # pass the required_opts to env_to_conf() to override config values with env vars
    config = env_to_conf(config, required_opts)
    
    # Finally, validate that we have all the keys we need between the config file
    # and the environment variables and raise an exception if any are missing
    for opt in required_opts:
        try:
            config.defaults()[opt]
        except KeyError as e:
            print(f"required value: `{opt}` is missing from {args.config_file} and is not defined as an environment variable", file=sys.stdout)
            raise e
    
    ip_list = IPList(config.defaults().get('permalink'), config.defaults().get('user'), config.defaults().get('key'), db_cache=args.db_cache)
    found = ip_list.get_country(args.country)
    print("\n".join(found))
    
    return

if __name__ == "__main__":
    main()
