from ninja import Schema

class InquiryCreateSchema(Schema):
  title: str
  content: str

class InquiryUpdateSchema(Schema):
  title: str | None = None
  content: str | None = None

class InquiryReplyCreateSchema(Schema):
  content: str

class InquiryReplySchema(Schema):
  id: int
  is_admin: bool
  content: str
  created_at: str

class InquiryOutputSchema(Schema):
  id: int
  fan_email: str
  title: str
  status: str
  created_at: str

class InquiryDetailSchema(Schema):
  id: int
  fan_email: str
  title: str
  status: str
  replies: list[InquiryReplySchema]
  created_at: str
