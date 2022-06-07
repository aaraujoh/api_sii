from sqlalchemy import func, and_, or_
from lib.models.database.db_users import User
from lib.models.database.context import Session

class AuthenticationService:
	def get_user_id_by_api_key(self, api_key:str) -> int:
		with Session() as s:
			return s.query(User.id).filter(User.api_key == api_key).scalar()