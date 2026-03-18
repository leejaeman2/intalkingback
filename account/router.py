from ninja import Router, File, Form
from ninja.files import UploadedFile
from ninja.error import HttpError
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from account.models import IntalkingUser
from account.schema import (SignupOutputSchema, TokenSchema, SigninSchema,
  IsLoginSchema, IntalkingUserSchema, EditFanSchema, EditInflSchema)
from django.shortcuts import get_object_or_404
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.schema import (TokenObtainPairInputSchema, 
  TokenObtainPairOutputSchema, TokenRefreshInputSchema)

router = Router()

@router.post('signup/', response=SignupOutputSchema, auth=None)
def signup(request, email: str = Form(...)):
  hashed = make_password()
  user = IntalkingUser.objects.create(email=email)

@router.post('signin/', response=TokenSchema, auth=None)
def signin(request, payload: SigninSchema):
  try:
    IntalkingUser.objects.get(email=payload.email)
  except IntalkingUser.DoesNotExist:
    raise HttpError(401, '이메일이 존재하지 않습니다')
  
  authuser = authenticate(email=payload.email, password=payload.password)
  if authuser is None:
    raise HttpError(401, '비밀번호가 일치하지 않습니다')

  refresh = RefreshToken.for_user(authuser)
  return {
    "access": str(refresh.access_token),
    "refresh": str(refresh),
    "id": authuser.id,
    "email": authuser.email,
    "nickname": authuser.nickname,
    "point": authuser.point,
    "photo1": authuser.photo1.url if authuser.photo1 else None
  }

@router.post('refresh/', response=TokenObtainPairOutputSchema, auth=None)
def getRefresh(request, payload: TokenRefreshInputSchema):
  try:
    refresh = RefreshToken(payload.refresh)
    access = refresh.access_token
    return {
      "access": str(access),
      "refresh": str(refresh),
      "email": ''
    }
  except Exception as e:
    return router.create_error_response(status=401, message=str(e))

@router.get('islogin/', response=IntalkingUserSchema)
def isLogin(request):
  return { "islogin": True }

@router.get('me/', response=IntalkingUserSchema)
def getProfile(request):
  return request.user

@router.patch('fan/', response=IntalkingUserSchema)
def editProfile(request, payload: EditFanSchema):
  user = get_object_or_404(IntalkingUser, email=payload.email)
  user.nickname = payload.nickname
  user.save()
  return user

@router.delete('me/', response={204: str})
def deleteUser(request):
  user = get_object_or_404(IntalkingUser, email=request.user.email)
  email = user.email
  user.delete()
  return f"Delete {email}"

@router.get('infl/', response=list[IntalkingUserSchema])
def getInflUsers(request):
  users = IntalkingUser.objects.filter(fan='INFL')
  return users
