import os
import time
import hmac
import hashlib
import base64
from ninja import Router

router = Router()

@router.get('/credentials/')
def turn_credentials(request):
    user_id = str(request.auth.id)
    secret = os.getenv('TURN_AUTH_SECRET', '')
    realm = os.getenv('TURN_REALM', '')
    ttl = 24 * 3600
    expiry = int(time.time()) + ttl
    username = f'{expiry}:{user_id}'
    digest = hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()
    password = base64.b64encode(digest).decode()
    return {
        'username': username,
        'password': password,
        'ttl': ttl,
        'urls': [
            f'turn:{realm}:3478?transport=udp',
            f'turn:{realm}:3478?transport=tcp',
            f'turns:{realm}:5349?transport=tcp',
        ],
    }
