from ninja import NinjaAPI
from core.auth import TokenVersionJWTAuth
from account.router import router as account_router
from infllist.router import router as infllist_router
from notice.router import router as notice_router
from inquiry.router import router as inquiry_router
from chat.turn import router as turn_router

app = NinjaAPI(version='v1.0.0', auth=TokenVersionJWTAuth())

app.add_router('account/', account_router)
app.add_router('infllist/', infllist_router)
app.add_router('notice/', notice_router)
app.add_router('inquiry/', inquiry_router)
app.add_router('turn/', turn_router)
