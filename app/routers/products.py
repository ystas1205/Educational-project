from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.db_depends import get_db, get_async_db

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=ProductList)
async def get_all_products(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает список всех активных товаров.
    """
    total_stmt = select(func.count()).select_from(ProductModel).where(
        ProductModel.is_active == True)
    total = await db.scalar(total_stmt) or 0

    products_stmt = (
        select(ProductModel)
        .where(ProductModel.is_active == True)
        .order_by(ProductModel.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.scalars(products_stmt)).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int,
                                   db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список активных товаров в указанной категории по её ID.
    """
    stmt = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == category_id,
                                    CategoryModel.is_active == True)
    )
    category = stmt.first()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Category not found or inactive")
    stmt_product = await db.scalars(
        select(ProductModel).where(ProductModel.category_id == category_id,
                                   ProductModel.is_active == True)
    )
    products = stmt_product.all()
    return products


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int,
                      db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id,
                                   ProductModel.is_active == True)
    )
    product = stmt.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found or inactive")
    return product


from app.models.users import User as UserModel
from app.auth import get_current_seller


# Импорты и эндпоинты:
#            get_all_products
#            get_products_by_category
#            get_product


@router.post("/", response_model=ProductSchema,
             status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id,
                                    CategoryModel.is_active == True)
    )
    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Category not found or inactive")
    db_product = ProductModel(**product.model_dump(),
                              seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)  # Для получения id и is_active из базы
    return db_product


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
        product_id: int,
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар, если он принадлежит текущему продавцу (только для 'seller').
    """
    result = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id,
                                   ProductModel.is_active == True))
    db_product = result.first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found")
    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only update your own products")
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id,
                                    CategoryModel.is_active == True)
    )
    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Category not found or inactive")
    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(
            **product.model_dump())
    )
    await db.commit()
    await db.refresh(db_product)  # Для консистентности данных
    return db_product


@router.delete("/{product_id}", response_model=ProductSchema)
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """
    result = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id,
                                   ProductModel.is_active == True)
    )
    product = result.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found or inactive")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only delete your own products")
    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(
            is_active=False)
    )
    await db.commit()
    await db.refresh(product)  # Для возврата is_active = False
    return product
