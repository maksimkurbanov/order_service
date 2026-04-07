from http import HTTPStatus
from uuid import UUID

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends

from app.application.container import ApplicationContainer
from app.application.create_order import OrderDTO, CreateOrderUseCase
from app.application.get_order import GetOrderUseCase
from app.application.process_payment_callback import (
    PaymentDTO,
    ProcessPaymentCallbackUseCase,
)
from app.domain.models import Order

router = APIRouter()


class OrderCreateRequest(OrderDTO):
    pass


class OrderResponse(Order):
    pass


class PaymentCallbackRequest(PaymentDTO):
    pass


@router.post(
    "/api/orders", status_code=HTTPStatus.CREATED, response_model=OrderResponse
)
@inject
async def create_order(
    order: OrderCreateRequest,
    create_order_use_case: CreateOrderUseCase = Depends(
        Provide[ApplicationContainer.create_order_use_case]
    ),
):
    return await create_order_use_case(order)


@router.get("/api/orders/{order_id}", response_model=OrderResponse)
@inject
async def get_order(
    order_id: UUID,
    get_order_use_case: GetOrderUseCase = Depends(
        Provide[ApplicationContainer.get_order_use_case]
    ),
):
    return await get_order_use_case(order_id)


@router.post("/api/orders/payment-callback", status_code=HTTPStatus.OK)
@inject
async def payment_callback(
    callback: PaymentCallbackRequest,
    process_payment_callback_use_case: ProcessPaymentCallbackUseCase = Depends(
        Provide[ApplicationContainer.process_payment_callback_use_case]
    ),
):
    return await process_payment_callback_use_case(callback)
