from ninja import NinjaAPI
from ninja_jwt.authentication import JWTAuth
from account.router import router as account_router

app = NinjaAPI(version='v1.0.0', auth=JWTAuth())

app.add_router('account/', account_router)
