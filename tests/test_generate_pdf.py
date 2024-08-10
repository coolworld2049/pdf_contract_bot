import pytest
from aiogram import types
from loguru import logger

from bot.models import ContractFormData
from bot.settings import settings, bot
from bot.utils import generate_pdf


@pytest.mark.asyncio
async def test_generate_pdf():
    data = [
        {
            "contract_name": "prostor",
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
            "contract_name": "stroytorgcomplect",
            "date": "asdf",
            "contract_number": "1234",
            "first_name": "asdf",
            "last_name": "asdf",
            "middle_name": "dsf",
            "phone": "asdf",
            "address": "1234",
            "ordered_item": "Станок Юпитер 7000 с полным комплектом насадок и дополнительным контроллером с массой до 50 кг.",
            "quantity": "2",
            "cost": "122990",
            "sbp_phone": "1234",
            "sbp_full_name": "Афанасьева Ольга Алексеевна",
            "sbp_bank": "1234",
        },
    ]
    for i, item in enumerate(data):
        doc_name, file = await generate_pdf(ContractFormData(**item), contract_name=item["contract_name"])
        file_buffered = types.FSInputFile(file.name, filename=f"{doc_name}.pdf")
        await bot.send_document(settings.test_user_id, file_buffered)
        logger.debug(i)
