import pathlib
import tempfile
from typing import Literal

from PIL import Image
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from bot.models import ContractFormData
from bot.settings import company_contract


async def validate_state_data(state: FSMContext, message: Message):
    if message.text.startswith("/"):
        return True
    state_name = await state.get_state()
    ContractFormData.__pydantic_validator__.validate_assignment(
        ContractFormData.model_construct(), state_name.split(":")[1], message.text
    )


async def ask_next_state(
    message: Message, state: FSMContext, next_state: State, prompt: str
):
    await state.set_state(next_state)
    await message.answer(prompt)


async def generate_pdf(
    data: ContractFormData, contract_name: Literal["prostor", "stroytorgcomplect"]
):
    contract = company_contract[contract_name]
    company_data = contract.company
    document_name = f'{company_data.name}. Счет-договор на поставку товара № {data.contract_number}'

    project_path = pathlib.Path(__file__).parent
    contract_path = project_path.joinpath(f"contracts/{contract_name}")
    signatures_path = project_path.joinpath("contracts/signatures")

    stamp_path = contract_path.joinpath("stamp.png")
    qes_path = contract_path.joinpath("qes.png")
    sig_path = signatures_path.joinpath("sig.png")

    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    tmp_file.write(
        project_path.joinpath("contracts/contract_template.pdf").read_bytes()
    )
    tmp_file.seek(0)

    c = canvas.Canvas(filename=tmp_file, pagesize=A4)
    width, height = A4

    # Регистрация шрифта FreeSans для корректной кодировки
    pdfmetrics.registerFont(
        TTFont("FreeSans", project_path.joinpath("font/freesans/FreeSans.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("FreeSansBold", project_path.joinpath("font/freesans/FreeSansBold.ttf"))
    )
    c.setFont("FreeSans", 12)

    # Добавление данных компании
    c.setFont("FreeSansBold", 11)
    c.drawString(10 * mm, height - 20 * mm, company_data.name)
    c.setFont("FreeSans", 9)
    c.drawString(10 * mm, height - 25 * mm, f"ОГРН: {company_data.ogrn}")
    c.drawString(10 * mm, height - 30 * mm, f"ИНН: {company_data.inn}")
    c.drawString(
        10 * mm,
        height - 35 * mm,
        company_data.legal_address,
    )

    # Добавление номера договора и даты
    c.setFont("FreeSans", 9)
    c.drawString(180 * mm, height - 55 * mm, data.date)
    c.drawString(
        10 * mm,
        height - 55 * mm,
        document_name,
    )
    c.drawString(10 * mm, height - 60 * mm, "г. Москва")

    # Добавление таблицы с заказанным товаром
    c.setFont("FreeSans", 9)
    c.drawString(10 * mm, height - 70 * mm, "№")
    c.drawString(20 * mm, height - 70 * mm, "Наименование товара")
    c.drawString(90 * mm, height - 70 * mm, "Единица")
    c.drawString(110 * mm, height - 70 * mm, "Количество")
    c.drawString(130 * mm, height - 70 * mm, "Цена в рублях")
    c.drawString(160 * mm, height - 70 * mm, "Сумма в рублях")

    # Линии таблицы
    table_start_y = height - 72 * mm
    row_height = 10 * mm

    c.line(10 * mm, table_start_y, 200 * mm, table_start_y)
    for i in range(3):  # 3 строки в таблице
        y = table_start_y - (i + 1) * row_height
        c.line(10 * mm, y, 200 * mm, y)
    c.line(
        10 * mm,
        table_start_y - 3 * row_height,
        200 * mm,
        table_start_y - 3 * row_height,
    )

    c.line(10 * mm, table_start_y, 10 * mm, table_start_y - 3 * row_height)
    c.line(20 * mm, table_start_y, 20 * mm, table_start_y - 3 * row_height)
    c.line(90 * mm, table_start_y, 90 * mm, table_start_y - 3 * row_height)
    c.line(110 * mm, table_start_y, 110 * mm, table_start_y - 3 * row_height)
    c.line(130 * mm, table_start_y, 130 * mm, table_start_y - 3 * row_height)
    c.line(160 * mm, table_start_y, 160 * mm, table_start_y - 3 * row_height)
    c.line(200 * mm, table_start_y, 200 * mm, table_start_y - 3 * row_height)

    # Данные в таблице

    ordered_item_lines = split_text(data.ordered_item, 45)
    # Draw the first line of the ordered_item text at the original position
    c.setFont("FreeSans", 8)
    c.drawString(22 * mm, table_start_y - row_height + 6 * mm, ordered_item_lines[0])

    # Draw the remaining lines below the first line
    for i, line in enumerate(ordered_item_lines[1:]):
        c.drawString(
            22 * mm, table_start_y - row_height + 5.5 * mm - (i + 1) * 2.5 * mm, line
        )

    def format_number_with_separators(number):
        return f"{number:,}".replace(",", " ")

    c.drawString(12 * mm, table_start_y - row_height + 2 * mm, "1")
    c.drawString(92 * mm, table_start_y - row_height + 2 * mm, "шт.")
    c.drawString(112 * mm, table_start_y - row_height + 2 * mm, str(data.quantity))

    total_amount = data.quantity * data.cost
    c.drawString(
        132 * mm,
        table_start_y - row_height + 2 * mm,
        str(data.cost),
    )
    c.drawString(
        162 * mm,
        table_start_y - row_height + 2 * mm,
        str(total_amount),
    )

    # Итоговая сумма
    c.drawString(132 * mm, table_start_y - 3 * row_height + 15 * mm, "Сумма")
    c.drawString(
        162 * mm,
        table_start_y - 3 * row_height + 15 * mm,
        str(total_amount),
    )

    c.drawString(132 * mm, table_start_y - 3 * row_height + 5 * mm, "Всего к оплате")
    c.drawString(
        162 * mm,
        table_start_y - 3 * row_height + 5 * mm,
        str(total_amount),
    )

    # Добавление данных покупателя
    # c.drawString(150 * mm, height - 200 * mm, "Покупатель:")
    # c.drawString(150 * mm, height - 205 * mm, data['sbp_full_name'])
    # c.drawString(150 * mm, height - 210 * mm, f"Адрес: {data['address']}")
    # c.drawString(150 * mm, height - 215 * mm, f"Телефон: {data['sbp_phone']}")

    fio = f"{data.last_name} {data.first_name} {data.middle_name}"
    c.setFont("FreeSans", 9)
    c.drawString(130 * mm, height - 192 * mm, "Покупатель:")
    c.drawString(
        130 * mm,
        height - 197 * mm,
        fio,
    )

    address_lines = split_text(data.address, 45)
    c.drawString(130 * mm, height - 202 * mm, f"Адрес: {address_lines[0]}")
    # logger.info(f"address_lines: {height - 202 * mm}")
    # Draw the remaining lines below the first line
    for i, line in enumerate(address_lines[1:]):
        c.drawString(
            130 * mm, height - 565 - row_height + 5.5 * mm - (i + 1) * 2.5 * mm, line
        )

    # c.drawString(130 * mm, height - 202 * mm, f"Адрес: {data['address']}")
    c.drawString(130 * mm, height - 212 * mm, f"Телефон: {data.phone}")
    c.drawString(130 * mm, height - 217 * mm, f"_____________________________")
    c.drawString(
        130 * mm,
        height - 222 * mm,
        f"/{fio}/",
    )

    # c.setFont('FreeSans', 9)
    # Обработка подписи для удаления черного фона
    signature_img = Image.open(sig_path).convert("RGBA")
    datas = signature_img.getdata()

    new_data = []
    for item in datas:
        # Change all black (also shades of black)
        # pixels to transparent
        if item[:3] == (0, 0, 0):
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    signature_img.putdata(new_data)
    signature_img.save(sig_path, "PNG")

    text_object = c.beginText(10 * mm, height - 110 * mm)
    text_object.setFont("FreeSans", 9)
    text_object.textLines(contract.text)
    c.drawText(text_object)

    # footer_text = """\
    # ООО "Простор"
    # ОГРН: 1197746047938
    # ИНН: 7728458381
    # Юр. адрес: 117279, город Москва, Профсоюзная ул., д. 97
    # Центральный склад: 141895, Московская область\nГлазово деревня, 30, «PNK Парк Северное Шереметьево»
    #     """

    c.drawString(10 * mm, 105 * mm, "Поставщик:")

    # c.setFont('FreeSansBold', 12)
    c.drawString(10 * mm, 100 * mm, company_data.name)

    footer_text = f"""\
    ОГРН: {company_data.ogrn}
    ИНН: {company_data.inn}
    Юр. адрес: {company_data.legal_address}
    Центральный склад: {company_data.central_warehouse}


    __________________________/{contract.contract_executor_fio}/
        """

    footer_text_object = c.beginText(10 * mm, 95 * mm)
    footer_text_object.setFont("FreeSans", 9)
    footer_text_object.textLines(footer_text)
    c.drawText(footer_text_object)
    c.drawImage(
        qes_path,
        140 * mm,
        height - 40 * mm,
        width=60 * mm,
        height=30 * mm,
        mask="auto",
    )

    c.drawImage(
        stamp_path, 20 * mm, 20 * mm, width=50 * mm, height=50 * mm, mask="auto"
    )
    c.drawImage(
        sig_path,
        20 * mm,
        60 * mm,
        width=40 * mm,
        height=20 * mm,
        mask="auto",
    )

    # Добавление текста по центру второй страницы
    c.showPage()

    c.setFont("FreeSansBold", 11)
    c.drawString(10 * mm, height - 20 * mm, company_data.name)
    c.setFont("FreeSans", 9)
    c.drawString(10 * mm, height - 25 * mm, f"ОГРН: {company_data.ogrn}")
    c.drawString(10 * mm, height - 30 * mm, f"ИНН: {company_data.inn}")
    c.drawString(
        10 * mm,
        height - 35 * mm,
        f"Юр. адрес: {company_data.legal_address}",
    )

    c.drawImage(
        qes_path,
        140 * mm,
        height - 40 * mm,
        width=60 * mm,
        height=30 * mm,
        mask="auto",
    )

    text_object = c.beginText(width / 2, height / 2)
    text_object.setFont("FreeSans", 9)
    text_object.setTextOrigin(width - 200 * mm, height - 180)

    c.setFont("FreeSans", 11)
    c.drawString(
        10 * mm,
        height - 55 * mm,
        "Реквизиты для оплаты через СБП (Система Быстрых Платежей - сервис Банка России):",
    )
    c.setFont("FreeSans", 9)

    text_object.textLines(
        f"""\
        1. Откройте приложение или личный кабинет Вашего банка.
        2. Выберите: «Платежи» → «СБП» (Система Быстрых Платежей).
        3. Укажите корпоративный номер компании: {data.sbp_phone}
        4. Укажите сумму перевода: {data.quantity * data.cost} руб.
        5. Получатель: ООО «Простор», в лице главного бухгалтера: {data.sbp_full_name}
        6. Выберите банк: {data.sbp_bank}
        7. Выполните перевод.
    """
    )
    c.drawText(text_object)

    text_object = c.beginText(10 * mm, height - 200 * mm)
    text_object.setFont("FreeSans", 9)
    c.drawText(text_object)

    c.drawString(10 * mm, 185 * mm, "Поставщик:")

    # c.setFont('FreeSansBold', 12)
    c.drawString(10 * mm, 180 * mm, company_data.name)

    footer_text = f"""\
    ОГРН: {company_data.ogrn}
    ИНН: {company_data.inn}
    Юр. адрес: {company_data.legal_address}
    Центральный склад: {company_data.central_warehouse}


    __________________________/{contract.contract_executor_fio}/
        """

    footer_text_object = c.beginText(10 * mm, 175 * mm)
    footer_text_object.setFont("FreeSans", 9)
    footer_text_object.textLines(footer_text)
    c.drawText(footer_text_object)

    c.setFont("FreeSans", 9)
    c.drawString(130 * mm, height - 112 * mm, "Покупатель:")
    c.drawString(
        130 * mm,
        height - 117 * mm,
        fio,
    )
    # c.drawString(130 * mm, height - 122 * mm, f"Адрес: {data['address']}")
    address_lines = split_text(data.address, 45)
    c.drawString(130 * mm, height - 122 * mm, f"Адрес: {address_lines[0]}")
    # logger.info(f"address_lines: {height - 202 * mm}")
    # Draw the remaining lines below the first line
    for i, line in enumerate(address_lines[1:]):
        c.drawString(
            130 * mm, height - 340 - row_height + 5.5 * mm - (i + 1) * 2.5 * mm, line
        )

    c.drawString(130 * mm, height - 132 * mm, f"Телефон: {data.phone}")
    c.drawString(130 * mm, height - 137 * mm, f"_____________________________")
    c.drawString(
        130 * mm,
        height - 142 * mm,
        f"/{fio}/",
    )

    c.setFont("FreeSans", 9)
    c.drawImage(
        stamp_path, 20 * mm, 100 * mm, width=50 * mm, height=50 * mm, mask="auto"
    )
    c.drawImage(
        sig_path,
        20 * mm,
        140 * mm,
        width=40 * mm,
        height=20 * mm,
        mask="auto",
    )

    c.showPage()
    c.save()
    return document_name, tmp_file


def split_text(text, length):
    lines = []
    while len(text) > length:
        # Find the last space within the length limit
        space_index = text.rfind(" ", 0, length)
        if space_index == -1:
            # No spaces found, split at the length limit
            lines.append(text[:length])
            text = text[length:]
        else:
            # Split at the last space
            lines.append(text[:space_index])
            text = text[space_index + 1:]
    lines.append(text)
    return lines
