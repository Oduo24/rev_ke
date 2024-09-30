#!/usr/bin/python3
"""Defines the db storage methods. ie interacts with the database to create, delete, modify, query objects"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, desc, and_
from sqlalchemy.orm import sessionmaker, scoped_session

from models.main_models import Base
from models.main_models import *

# Load environment variables from .env file
load_dotenv()

MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PWD = os.getenv('MYSQL_PWD')
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_DB = os.getenv('MYSQL_DB')

engine = create_engine('mysql+mysqldb://{}:{}@{}/{}'.format(MYSQL_USER, MYSQL_PWD, MYSQL_HOST, MYSQL_DB),
    pool_size=100, max_overflow=0)

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


class DBStorage:
    """Defines a db storage object"""

    def __init__(self, session=None):
        """Class constructor, instantiates a DBStorage object
        """
        self.session = session
        self.engine = engine

    def new(self, instance):
        """Adds a new object to the current db session
        """
        self.session.add(instance)

    def save(self):
        """Commits all changes of the current db session
        """
        try:  
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e # Will be caught by the calling function

    def rollback(self):
        """Rolls back the changes in a particular session
        """
        self.session.rollback()

    def initialize_storage(self):
        """Initializes the DB
        """
        Base.metadata.create_all(self.engine)

    def get_user(self, username):
        """Retrieve single object"""
        obj = self.session.query(User).filter_by(user_name=username).first()
        return obj
    
    def get_object_by_id(self, object_class, object_id):
        """Retrieve single object"""
        obj = self.session.query(object_class).filter_by(id=object_id).first()
        return obj
    
    def all_designs(self):
        """Get all designs from the db"""
        designs = self.session.query(Design).all()
        return [{'id': design.id, 'image_url': design.image_url, 'votes': design.votes} for design in designs]
    
    def get_comments(self, design_id, page, page_size):
        """Retrieve the top-level comments for a particular design with pagination"""
        # Fetch top-level comments for the design
        top_level_comments = self.session.query(Comment)\
            .filter_by(design_id=design_id, parent_id=None)\
            .order_by(Comment.created_at.desc())\
            .limit(page_size)\
            .offset((page - 1) * page_size).all()

        def serialize_top_level_comments(comment):
            """Serialize top-level comments without replies"""
            return {
                "id": comment.id,
                "created_at": comment.created_at.isoformat(),
                "design_id": comment.design_id,
                "user_id": comment.user_id,
                "parent_id": comment.parent_id,
                "comment": comment.comment,
                "likes": comment.likes
            }

        # Serialize each top-level comment
        serialized_comments = [serialize_top_level_comments(comment) for comment in top_level_comments]

        # Check if there are more comments beyond the current page
        total_comments = self.session.query(Comment)\
            .filter_by(design_id=design_id, parent_id=None).count()
        has_more_comments = (page * page_size) < total_comments

        return {
            "comments": serialized_comments,
            "total_comments": total_comments,
            "current_page": page,
            "page_size": page_size,
            "has_more_comments": has_more_comments
        }

    
    def get_paginated_replies(self, comment_id, page, page_size):
        """Retrieve paginated replies for a specific top-level comment"""
        # Fetch the replies for the given comment, with pagination
        replies = self.session.query(Comment)\
            .filter_by(parent_id=comment_id)\
            .order_by(Comment.created_at.desc())\
            .limit(page_size)\
            .offset((page - 1) * page_size).all()

        # Serialize replies
        serialized_replies = [{
            "id": reply.id,
            "created_at": reply.created_at.isoformat(),
            "design_id": reply.design_id,
            "user_id": reply.user_id,
            "parent_id": reply.parent_id,
            "comment": reply.comment,
            "likes": reply.likes
        } for reply in replies]

        # Check if there are more replies beyond the current page
        total_replies = self.session.query(Comment)\
            .filter_by(parent_id=comment_id).count()
        has_more_replies = (page * page_size) < total_replies

        return {
            "replies": serialized_replies,
            "total_replies": total_replies,
            "current_page": page,
            "page_size": page_size,
            "has_more_replies": has_more_replies
        }
    
    

        
    
        
