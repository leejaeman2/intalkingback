from ninja import Router, File, Form
from ninja.files import UploadedFile
from ninja.errors import HttpError
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from account.models import IntalkingUser, DeletedUser, InflCode
from account.schema import (SignupFanSchema, SignupInflSchema, SignupOutputSchema, InflSchema,
  TokenSchema, LoginErrorSchema, SigninSchema, IsLoginSchema, IntalkingUserSchema, FanMeSchema, InflMeSchema, MeSchema,
  EditFanSchema, EditInflSchema,
  PointChargeSchema, InflWithNoticeSchema, VerifyCodeSchema)
from notice.models import Notice
from chat.consumers import online_users
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

@router.post('verify-code/', response={200: dict}, auth=None)
def verifyInflCode(request, payload: VerifyCodeSchema):
  if IntalkingUser.objects.filter(code=payload.code).exists():
    raise HttpError(400, '동일한 코드가 존재합니다')
  if not InflCode.objects.filter(code=payload.code, is_used=False).exists():
    raise HttpError(400, '유효하지 않은 인플루언서 코드입니다')
  return {'valid': True}

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
  code = (code or '').strip()
  infl_code = None
  if code:
    try:
      infl_code = InflCode.objects.get(code=code, is_used=False)
    except InflCode.DoesNotExist:
      raise HttpError(400, '유효하지 않은 인플루언서 코드입니다')

  user = IntalkingUser.objects.create(
    email=email, username=email,
    password=make_password(password),
    nickname=nickname, phone=phone,
    bank=bank, account=account, code=code or None,
    hobby=hobby, food=food, mbti=mbti,
    fan='INFL',
    is_approved=bool(code),   # 코드 있으면 즉시 승인, 없으면 관리자 승인 대기
  )
  for i, photo in enumerate([photo1, photo2, photo3, photo4, photo5, photo6, photo7, photo8], 1):
    if photo:
      getattr(user, f'photo{i}').save(photo.name, photo)
  user.save()

  if infl_code:
    infl_code.delete()

  return user

MAX_LOGIN_FAIL = 5

@router.post('signin/', response={200: TokenSchema, 401: LoginErrorSchema, 403: LoginErrorSchema, 409: LoginErrorSchema, 423: LoginErrorSchema}, auth=None)
def signin(request, payload: SigninSchema):
  try:
    user = IntalkingUser.objects.get(email=payload.email)
  except IntalkingUser.DoesNotExist:
    return 401, {'code': 'NO_USER', 'message': '회원 정보가 없습니다'}

  # 이미 5회 이상 실패로 잠긴 계정
  if user.login_fail_count >= MAX_LOGIN_FAIL:
    return 423, {'code': 'LOCKED', 'fail_count': user.login_fail_count, 'locked': True,
      'message': '비밀번호가 5회 이상 틀렸습니다. 비밀번호를 재설정 해주세요.'}

  authuser = authenticate(email=payload.email, password=payload.password)
  if authuser is None:
    user.login_fail_count += 1
    user.save(update_fields=['login_fail_count'])
    if user.login_fail_count >= MAX_LOGIN_FAIL:
      return 423, {'code': 'LOCKED', 'fail_count': user.login_fail_count, 'locked': True,
        'message': '비밀번호가 5회 이상 틀렸습니다. 비밀번호를 재설정 해주세요.'}
    return 401, {'code': 'WRONG_PASSWORD', 'fail_count': user.login_fail_count, 'locked': False,
      'message': '비밀번호가 틀립니다. 다시 입력해주세요.'}

  # 비밀번호 정상 → 실패 카운트 초기화
  if authuser.login_fail_count:
    authuser.login_fail_count = 0
    authuser.save(update_fields=['login_fail_count'])

  # 관리자 승인 대기 계정(코드 없이 가입 신청)은 로그인 차단
  if not authuser.is_approved:
    return 403, {'code': 'NOT_APPROVED', 'locked': False,
      'message': '가입 신청이 접수되었습니다. 관리자 승인 후 로그인할 수 있습니다.'}

  # 다른 기기에서 접속 중이면, force 아닌 경우 확인 요청
  if not payload.force and online_users.get(payload.email):
    return 409, {'code': 'ALREADY_LOGGED_IN', 'locked': False,
      'message': '다른 기기에 로그인되어 있습니다. 그래도 로그인하시겠습니까?'}

  # 토큰 발급 (token_version 증가 → 기존 기기 토큰 무효화, WS register 시 force_logout)
  authuser.token_version = (authuser.token_version or 0) + 1
  authuser.save(update_fields=['token_version'])

  refresh = RefreshToken.for_user(authuser)
  refresh['token_version'] = authuser.token_version
  access = refresh.access_token
  access['token_version'] = authuser.token_version
  return 200, {
    "access": str(access),
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
    user_id = refresh['user_id']
    token_version_in_jwt = refresh.payload.get('token_version', 0)
    user = IntalkingUser.objects.get(id=user_id)
    if user.token_version != token_version_in_jwt:
      raise HttpError(401, '다른 기기에서 로그인되었습니다')
    access = refresh.access_token
    access['token_version'] = user.token_version
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

@router.get('me/', response=MeSchema)
def getProfile(request):
  return request.user

@router.patch('fan/', response=FanMeSchema)
def editProfile(request, payload: EditFanSchema):
  user = request.auth
  if payload.nickname is not None: user.nickname = payload.nickname
  if payload.phone is not None: user.phone = payload.phone
  if payload.hobby is not None: user.hobby = payload.hobby
  if payload.food is not None: user.food = payload.food
  if payload.mbti is not None: user.mbti = payload.mbti
  user.save()
  return user

@router.patch('infl/', response=InflMeSchema)
def editInflProfile(request, payload: EditInflSchema):
  user = request.auth
  if payload.nickname is not None: user.nickname = payload.nickname
  if payload.phone is not None: user.phone = payload.phone
  if payload.bank is not None: user.bank = payload.bank
  if payload.account is not None: user.account = payload.account
  if payload.hobby is not None: user.hobby = payload.hobby
  if payload.food is not None: user.food = payload.food
  if payload.mbti is not None: user.mbti = payload.mbti
  if payload.info is not None: user.info = payload.info
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

CALL_POINT = 16000   # 통화 연결 시 차감 포인트 (20분 단위)

@router.post('call-charge/', response={200: dict, 400: dict})
def callCharge(request):
  user = request.user
  if user.point < CALL_POINT:
    return 400, {'message': '포인트가 부족합니다', 'point': user.point}
  user.point -= CALL_POINT
  user.save(update_fields=['point'])
  return {'message': '통화 포인트가 차감되었습니다', 'point': user.point}

@router.get('infl/', response=list[InflWithNoticeSchema])
def getInflUsers(request):
  users = IntalkingUser.objects.filter(fan='INFL')
  result = []
  for user in users:
    data = {
      'email': user.email, 'username': user.username,
      'nickname': user.nickname, 'fan': user.fan,
      'hobby': user.hobby, 'food': user.food,
      'mbti': user.mbti, 'info': user.info, 'callmode': user.callmode,
      'has_fanmeeting': Notice.objects.filter(infl=user, type='FANMEETING', is_deleted=False).exists(),
      'has_party': Notice.objects.filter(infl=user, type='PARTY', is_deleted=False).exists(),
      'fanmeeting_id': getattr(Notice.objects.filter(infl=user, type='FANMEETING', is_deleted=False).first(), 'id', None),
      'party_id': getattr(Notice.objects.filter(infl=user, type='PARTY', is_deleted=False).first(), 'id', None),
    }
    for i in range(1, 9):
      photo = getattr(user, f'photo{i}')
      data[f'photo{i}'] = photo.url if photo else None
    result.append(data)
  return result
