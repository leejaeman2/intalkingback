from ninja import Router
from django.shortcuts import get_object_or_404
from inquiry.models import Inquiry, InquiryReply
from inquiry.schema import InquiryCreateSchema, InquiryUpdateSchema, InquiryReplyCreateSchema, InquiryOutputSchema, InquiryDetailSchema

router = Router()

@router.get('list/', response=list[InquiryOutputSchema])
def get_inquiries(request):
  Inquiry.check_all_answering()
  inquiries = Inquiry.objects.filter(fan=request.user)
  return [
    {
      'id': i.id,
      'fan_email': i.fan.email,
      'title': i.title,
      'status': i.status,
      'created_at': str(i.created_at),
    }
    for i in inquiries
  ]

@router.get('{int:inquiry_id}/', response=InquiryDetailSchema)
def get_inquiry(request, inquiry_id: int):
  inquiry = get_object_or_404(Inquiry, id=inquiry_id, fan=request.user)
  inquiry.check_completed()
  return {
    'id': inquiry.id,
    'fan_email': inquiry.fan.email,
    'title': inquiry.title,
    'status': inquiry.status,
    'replies': [
      {
        'id': r.id,
        'is_admin': r.is_admin,
        'content': r.content,
        'created_at': str(r.created_at),
      }
      for r in inquiry.replies.all()
    ],
    'created_at': str(inquiry.created_at),
  }

@router.post('create/', response={200: dict})
def create_inquiry(request, payload: InquiryCreateSchema):
  inquiry = Inquiry.objects.create(fan=request.user, title=payload.title)
  InquiryReply.objects.create(inquiry=inquiry, author=request.user, is_admin=False, content=payload.content)
  return {'message': '문의가 등록되었습니다'}

@router.patch('{int:inquiry_id}/', response={200: dict})
def update_inquiry(request, inquiry_id: int, payload: InquiryUpdateSchema):
  inquiry = get_object_or_404(Inquiry, id=inquiry_id, fan=request.user)
  if payload.title is not None:
    inquiry.title = payload.title
    inquiry.save(update_fields=['title'])
  if payload.content is not None:
    first_reply = inquiry.replies.filter(is_admin=False).order_by('created_at').first()
    if first_reply:
      first_reply.content = payload.content
      first_reply.save(update_fields=['content'])
  return {'message': '문의가 수정되었습니다'}

@router.delete('{int:inquiry_id}/', response={200: dict})
def delete_inquiry(request, inquiry_id: int):
  inquiry = get_object_or_404(Inquiry, id=inquiry_id, fan=request.user)
  inquiry.delete()
  return {'message': '문의가 삭제되었습니다'}

@router.post('{int:inquiry_id}/reply/', response={200: dict})
def reply_inquiry(request, inquiry_id: int, payload: InquiryReplyCreateSchema):
  inquiry = get_object_or_404(Inquiry, id=inquiry_id, fan=request.user)
  InquiryReply.objects.create(inquiry=inquiry, author=request.user, is_admin=False, content=payload.content)
  return {'message': '답글이 등록되었습니다'}
