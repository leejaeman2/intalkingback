from ninja import Router
from notice.models import Notice
from notice.schema import NoticeOutputSchema

router = Router()

@router.get('list/', response=list[NoticeOutputSchema])
def get_notices(request):
  notices = Notice.objects.filter(is_deleted=False)
  return [
    {
      'id': n.id,
      'author': n.author,
      'type': n.type,
      'title': n.title,
      'content': n.content,
      'created_at': str(n.created_at),
    }
    for n in notices
  ]
