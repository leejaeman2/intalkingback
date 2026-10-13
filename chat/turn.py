import os
import time
import hmac
import hashlib
import base64
from ninja import Router

router = Router()

def make_turn_credentials(user_id):
    """coturn REST API(use-auth-secret) 방식 임시 계정. 녹음 서버(aiortc)도 같은 TURN 을 씀"""
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

@router.get('/credentials/')
def turn_credentials(request):
    return make_turn_credentials(str(request.auth.id))
