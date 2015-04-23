#!/usr/bin/python

import sys
import os
from requests_oauthlib import OAuth2Session

# Credentials you get from registering a new application
client_id = ''
client_secret = ''

# OAuth endpoints given in the GitHub API documentation
authorization_base_url = 'https://runkeeper.com/apps/authorize'
token_url = 'https://runkeeper.com/apps/token'
redirect_uri = 'https://runkeeper.com/apps/authorize'

rk = OAuth2Session(client_id,redirect_uri=redirect_uri)

#Redirect user to Runkeeper for authorization
authorization_url, state = rk.authorization_url(authorization_base_url)
print ('Please go here and authorize,', authorization_url)

# Get the authorization verifier code from the callback url
redirect_response = input('Paste the full redirect URL here:')

# Fetch the access token
print(rk.fetch_token(token_url, client_secret=client_secret,
         authorization_response=redirect_response))


