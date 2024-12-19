# GeoIP lookup

## Summary

This project was born of a desire to ask the question "What IPs belong to
Country XX" where "XX" is the ISO country code for any country in the world.
Existing python projects such as GeoIP2 and maxminddb are not natively able to
answer this question in a straight forward manner.
This project aims to make answering such a question straight forward.
By abstracting the [maxminddb](https://pypi.org/project/maxminddb/) library to
return an easy to parse dictionary of IPs for a country.

## Setup

At a minimum, you will need a free tier MaxMind account ID and API key
(to download the GeoIP DB)

1. Copy `config.ini.example`` to`config.ini`
2. Add your Account ID and API key to the corresponding `user` and `key` fields
in `config.ini`
3. (optional) alternatively, you can set these to environment variables:
  a. `permalink` = LOOKUP_PERMALINK
  b. `user` = LOOKUP_USER
  c. `key` = LOOKUP_KEY
4. Install all requirements with `pip install -r requirements.txt`

NOTE: Free tier MaxMind accounts have a limit to how many times they can
download the GeoIP database in a 24hr period. Use the `--db` flag if you wish
to use a locally cached database file
