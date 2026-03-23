from ninja import NinjaAPI
from ninja_jwt.authentication import JWTAuth
from account.router import router as account_router
from infllist.router import router as infllist_router
from notice.router import router as notice_router

app = NinjaAPI(version='v1.0.0', auth=JWTAuth())

app.add_router('account/', account_router)
app.add_router('infllist/', infllist_router)
app.add_router('notice/', notice_router)
