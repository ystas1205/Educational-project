from datetime import datetime
from sqlalchemy import ForeignKey, Text, DateTime, Integer, Boolean, \
    UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Review(Base):
    __tablename__ = 'reviews'

    __table_args__ = (UniqueConstraint("user_id", "product_id"),)

    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer,ForeignKey('users.id'))
    product_id: Mapped[int] = mapped_column(Integer,ForeignKey('products.id'))
    comments: Mapped[str] = mapped_column(Text)
    comment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                   default=datetime.now())
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean,default=True)

    user: Mapped["User"] = relationship("User", back_populates="reviews")

    product: Mapped["Product"] = relationship("Product",
                                              back_populates="reviews")
