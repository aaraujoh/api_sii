from sqlalchemy import *
from sqlalchemy.ext.declarative import declared_attr
from lib.models.database.db_users import User
from sqlalchemy.orm import relationship

class Owned:
    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('DTE_User.id'))

    @declared_attr
    def user(cls):
        return relationship("User", lazy="joined")