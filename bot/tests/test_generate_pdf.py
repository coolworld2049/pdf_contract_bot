import pytest
from loguru import logger

from bot.__main__ import generate_pdf


@pytest.mark.asyncio
async def test_generate_pdf():
    data = [
        {
            "date": "07.07.2024",
            "contract_number": "990178",
            "first_name": "Людмила",
            "last_name": "Романова",
            "middle_name": "Викторовна",
            "phone": "+7 (900) 788-90-12",
            "address": "г. Москва, ул. Остоженка, д. 90, кв. 78",
            "ordered_item": "Станок Юпитер Гранд 9000 с полным комплектом, 100% оригинал",
            "quantity": "1",
            "cost": "119990",
            "sbp_phone": "+7 (990) 189-90-81",
            "sbp_full_name": "Васильева Ольга Виктровна",
            "sbp_bank": "РОСБАНК",
        },
        {
            "date": "asdf",
            "contract_number": "1234",
            "first_name": "asdf",
            "last_name": "asdf",
            "middle_name": "dsf",
            "phone": "asdf",
            "address": "1234",
            "ordered_item": "Станок Юпитер 7000 с полным комплектом насадок и дополнительным контроллером с массой до 50 кг.",
            "quantity": "2",
            "cost": "122 990",
            "sbp_phone": "1234",
            "sbp_full_name": "Афанасьева Ольга Алексеевна",
            "sbp_bank": "1234",
        },
        {
            "date": "10.07.2024",
            "contract_number": "900812",
            "first_name": "Сергей",
            "last_name": "Михайлов",
            "middle_name": "Иванович",
            "phone": "+7 (999) 999-99-99",
            "address": "г. Москва, ул. Совесткая, д. 11, кв. 11 (вход со двора, через третий подьезд)",
            "ordered_item": "Станок Макита 321321",
            "quantity": "1",
            "cost": "59990",
            "sbp_phone": "+7 (888) 888-88-88",
            "sbp_full_name": "Алексеева Ольга Борисовна",
            "sbp_bank": "РОСБАНК",
        },
    ]
    for i, item in enumerate(data):
        logger.debug(i)
        await generate_pdf(item)
