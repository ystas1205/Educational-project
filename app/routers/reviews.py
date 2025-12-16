from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, Path
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.auth import get_current_buyer, get_current_admin
from app.db_depends import get_async_db
from app.models import Review as ReviewModel, User as UserModel, \
    Product as ProductModel
from app.schemas import Review as ReviewSchema, ReviewCreate

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/", response_model=list[ReviewSchema])
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов.
    """
    stmt = await db.scalars(
        select(ReviewModel).where(ReviewModel.is_active == True)
    )

    reviews = stmt.all()
    return reviews


@router.get("/products/{product_id}", response_model=list[ReviewSchema])
async def get_reviews_by_product_id(
        product_id: Annotated[int, Path(..., description="ID продукта")],
        db: AsyncSession = Depends(get_async_db)):
    """
    Получение отзывов о конкретном товаре.
    """

    stmt = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == product_id,
                                  ReviewModel.is_active == True)
    )
    review = stmt.all()

    if review is None:
        raise HTTPException(status_code=404, detail="review not found")

    return review


async def update_product_rating(db: AsyncSession, product_id: int):
    """
    Обновление рейтинга продукта.
    """
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()


@router.post("/", response_model=ReviewSchema)
async def create_review(review: ReviewCreate,
                        db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_buyer)):
    """
    Добавление отзыва.
    """
    stmt = await db.scalars(
        select(ProductModel).where(ProductModel.id == review.product_id,
                                   ProductModel.is_active == True)
    )

    result = stmt.first()
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Проверка оставил ли уже отзыв покупатель товару.
    stmt_rev = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == review.product_id,
                                  ReviewModel.user_id == current_user.id)
    )

    user_review = stmt_rev.first()

    if user_review:
        raise HTTPException(status_code=409,
                            detail="You have already left a review for this product")

    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)

    # Вызов функции обновления рейтинга товара.
    await update_product_rating(db=db, product_id=review.product_id)

    return db_review


@router.delete("/{review_id}")
async def remove_review(
        review_id: Annotated[int, Path(..., description="ID отзывы")],
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_admin)):


    """
    Удаление отзыва.
    """
    stmt = await db.scalars(
        select(ReviewModel).where(ReviewModel.id == review_id,
                                  ReviewModel.is_active == True)
    )

    review = stmt.first()

    if review is None:
        raise HTTPException(status_code=404, detail="review not found")

    await db.execute(
        update(ReviewModel).where(ReviewModel.id == review_id).values(
            is_active=False))

    await db.commit()

    # Вызов функции обновление рейтинга товара.
    await update_product_rating(db=db, product_id=review.product_id)

    return {"message": "Review deleted"}
