#!/user/bin/python3

from sqlalchemy import Column, String, DateTime, Date, Integer, Enum, Float, Index, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid


Base = declarative_base()
time = "%d-%m-%YT%H:%M:%S.%f"

class BaseModel:
    """Defines the base class to be inherited by other models"""
    id = Column(String(100), primary_key=True)
    created_at = Column(DateTime, default=datetime.now())

    def __init__(self, *args, **kwargs):
        """This is the class constructor"""
        if kwargs:
            for key, value in kwargs.items():
                if key != "__class__":
                    setattr(self, key, value)
            if kwargs.get("created_at", None) and type(self.created_at) is str:
                self.created_at = datetime.strptime(kwargs["created_at"], time)
            else:
                self.created_at = datetime.now()
            if kwargs.get("id", None) is None:
                self.id = str(uuid.uuid4())

        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()

    def __str__(self):
        """String representation of an object of this class"""
        return "[{}.{}]=>{}".format(self.__class__.__name__, self.id, self.__dict__)


class User(BaseModel, Base):
    """Defines the User class"""
    __tablename__ = "users"

    user_name = Column(String(100), nullable=False)
    password = Column(String(500), nullable=False)

    # Relationships
    comments = relationship('Comment', backref='user')


    def __init__(self, **kwargs):
        """Initializes a User instance
        """
        super().__init__(**kwargs)


class Design(BaseModel, Base):
    """Defines the Design class"""
    __tablename__ = "designs"

    image_url = Column(String(250), nullable=False)
    votes = Column(Integer, nullable=True, default=0)
    designer_email_address = Column(String(100), nullable=True)

    def __init__(self, **kwargs):
        """Initializes a Design instance
        """
        super().__init__(**kwargs)
    

class Comment(BaseModel, Base):
    """Defines the Comment class"""
    __tablename__ = 'comments'

    design_id = Column(String(100), ForeignKey('designs.id'))
    user_id = Column(String(100), ForeignKey('users.id'))
    parent_id = Column(String(100), ForeignKey('comments.id'), nullable=True)
    comment = Column(String(1024), nullable=False)
    likes = Column(Integer, default=0)

    # Self-referencing relationship for replies
    replies = relationship('Comment')

    def __init__(self, **kwargs):
        """Class constructor
        """
        super().__init__(**kwargs)
    
    