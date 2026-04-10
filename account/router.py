from ninja import Router, File, Form
from ninja.files import UploadedFile
from ninja.errors import HttpError
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from account.models import IntalkingUser, DeletedUser
from account.schema import (SignupFanSchema, SignupInflSchema, SignupOutputSchema, InflSchema,
  TokenSchema, SigninSchema, IsLoginSchema, IntalkingUserSchema, EditFanSchema, EditInflSchema,
  PointChargeSchema)
from typing import Optional
from django.shortcuts import get_object_or_404
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.schema import (TokenObtainPairInputSchema, 
  TokenObtainPairOutputSchema, TokenRefreshInputSchema)

router = Router()

@router.post('signup/fan/', response=SignupOutputSchema, auth=None)
def signupFan(request, payload: SignupFanSchema):
  user = IntalkingUser.objects.create(
    email=payload.email,
    username=payload.email,
    password=make_password(payload.password),
    nickname=payload.nickname,
    phone=payload.phone,
    charnum=payload.character,
    fan='FAN',
  )
  return user

@router.post('signup/infl/', response=SignupOutputSchema, auth=None)
def signupInfl(request,
  email: str = Form(...), password: str = Form(...),
  nickname: str = Form(...), phone: str = Form(...),
  bank: str = Form(...), account: str = Form(...),
  code: str = Form(...), hobby: str = Form(...),
  food: str = Form(...), mbti: str = Form(...),
  photo1: UploadedFile = File(...),
  photo2: UploadedFile = File(None), 
  photo3: UploadedFile = File(None),
  photo4: UploadedFile = File(None), 
  photo5: UploadedFile = File(None),
  photo6: UploadedFile = File(None), 
  photo7: UploadedFile = File(None),
  photo8: UploadedFile = File(None),
):
  user = IntalkingUser.objects.create(
    email=email, username=email,
    password=make_password(password),
    nickname=nickname, phone=phone,
    bank=bank, account=account, code=code or None,
    hobby=hobby, food=food, mbti=mbti,
    fan='INFL',
  )
  for i, photo in enumerate([photo1, photo2, photo3, photo4, photo5, photo6, photo7, photo8], 1):
    if photo:
      getattr(user, f'photo{i}').save(photo.name, photo)
  user.save()
  return user

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
    "photo1": authuser.photo1.url if authuser.photo1 else None,
    "fan": authuser.fan
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

@router.patch('callmode/', response={200: dict})
def toggleCallmode(request):
  user = request.user
  user.callmode = not user.callmode
  user.save(update_fields=['callmode'])
  return {'callmode': user.callmode}

@router.patch('photos/', response={200: dict})
def updatePhotos(request,
  photo1: UploadedFile = File(None), photo2: UploadedFile = File(None),
  photo3: UploadedFile = File(None), photo4: UploadedFile = File(None),
  photo5: UploadedFile = File(None), photo6: UploadedFile = File(None),
  photo7: UploadedFile = File(None), photo8: UploadedFile = File(None),
  delete_photos: str = Form(''),
):
  user = request.user
  for index in delete_photos.split(','):
    index = index.strip()
    if index.isdigit() and 1 <= int(index) <= 8:
      field = getattr(user, f'photo{index}')
      if field:
        field.delete(save=False)
  for i, photo in enumerate([photo1, photo2, photo3, photo4, photo5, photo6, photo7, photo8], 1):
    if photo:
      getattr(user, f'photo{i}').save(photo.name, photo, save=False)
  user.save()
  return {'message': '사진이 수정되었습니다'}

@router.delete('me/', response={204: str})
def deleteUser(request):
  user = get_object_or_404(IntalkingUser, email=request.user.email)
  DeletedUser.objects.create(
    email=user.email, nickname=user.nickname,
    phone=user.phone, fan=user.fan, point=user.point,
  )
  email = user.email
  user.delete()
  return f"Delete {email}"

@router.post('point/', response={200: dict})
def chargePoint(request, payload: PointChargeSchema):
  user = request.user
  user.point += payload.price
  user.save(update_fields=['point'])
  return {'message': '포인트가 적립되었습니다', 'point': user.point}

@router.get('infl/', response=list[InflSchema])
def getInflUsers(request):
  users = IntalkingUser.objects.filter(fan='INFL')
  return users
