import asyncio
import logging
import pathlib
import tempfile

from PIL import Image
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, BotCommand
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from bot.loguru_logger import configure_logging


class Settings(BaseSettings):
    bot_token: str = None
    use_redis: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    log_level: str = "INFO"
    test_user_id: int | None = None
    model_config = SettingsConfigDict(
        env_file=pathlib.Path(__file__).parent.parent.joinpath(".env"),
        case_sensitive=False,
    )

    @property
    def log_level_number(self):
        return logging.getLevelNamesMapping().get(self.log_level, self.log_level)


settings = Settings()
redis_conn = Redis()
storage = (
    RedisStorage.from_url(url=f"redis://{settings.redis_host}:{settings.redis_port}")
    if settings.use_redis
    else MemoryStorage()
)
bot = Bot(token=settings.bot_token)
dp = Dispatcher(storage=storage)
form_router = Router()


class Form(StatesGroup):
    date = State()
    contract_number = State()
    first_name = State()
    last_name = State()
    middle_name = State()
    phone = State()
    address = State()
    ordered_item = State()
    quantity = State()
    cost = State()
    sbp_phone = State()
    sbp_full_name = State()
    sbp_bank = State()


async def ask_next_state(
    message: Message, state: FSMContext, next_state: State, prompt: str
):
    await state.set_state(next_state)
    await message.answer(prompt)


@form_router.message(Command("start"))
async def start_form(message: Message, state: FSMContext):
    await ask_next_state(message, state, Form.date, "Введите дату договора:")


@form_router.message(Command("clear_context"))
async def start_form(message: Message, state: FSMContext):
    await state.clear()
    await message.reply("Контекст очищен")


@form_router.message(Form.date)
async def process_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await ask_next_state(
        message, state, Form.contract_number, "Введите номер договора:"
    )


@form_router.message(Form.contract_number)
async def process_contract_number(message: Message, state: FSMContext):
    await state.update_data(contract_number=message.text)
    await ask_next_state(message, state, Form.first_name, "Введите имя:")


@form_router.message(Form.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await ask_next_state(message, state, Form.last_name, "Введите фамилию:")


@form_router.message(Form.last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await ask_next_state(
        message, state, Form.middle_name, "Введите отчество (если нет, напишите '-'):"
    )


@form_router.message(Form.middle_name)
async def process_middle_name(message: Message, state: FSMContext):
    await state.update_data(middle_name=message.text)
    await ask_next_state(message, state, Form.phone, "Введите телефон:")


@form_router.message(Form.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await ask_next_state(message, state, Form.address, "Введите адрес:")


@form_router.message(Form.address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await ask_next_state(message, state, Form.ordered_item, "Введите заказанный товар:")


@form_router.message(Form.ordered_item)
async def process_ordered_item(message: Message, state: FSMContext):
    await state.update_data(ordered_item=message.text)
    await ask_next_state(message, state, Form.quantity, "Введите количество:")


@form_router.message(Form.quantity)
async def process_quantity(message: Message, state: FSMContext):
    await state.update_data(quantity=message.text)
    await ask_next_state(message, state, Form.cost, "Введите стоимость:")


@form_router.message(Form.cost)
async def process_cost(message: Message, state: FSMContext):
    await state.update_data(cost=message.text)
    await ask_next_state(
        message, state, Form.sbp_phone, "Введите номер телефона (СБП):"
    )


@form_router.message(Form.sbp_phone)
async def process_sbp_phone(message: Message, state: FSMContext):
    await state.update_data(sbp_phone=message.text)
    await ask_next_state(message, state, Form.sbp_full_name, "Введите ФИО (СБП):")


@form_router.message(Form.sbp_full_name)
async def process_sbp_full_name(message: Message, state: FSMContext):
    await state.update_data(sbp_full_name=message.text)
    await ask_next_state(message, state, Form.sbp_bank, "Введите банк (СБП):")


@form_router.message(Form.sbp_bank)
async def process_sbp_bank(message: Message, state: FSMContext):
    await state.update_data(sbp_bank=message.text)
    data = await state.get_data()
    logger.debug(data)
    await bot.send_message(message.chat.id, "Пожалуйста, ожидайте...")
    try:
        doc_name, file = await generate_pdf(data)
        file_buffered = types.FSInputFile(file.name, filename=f"{doc_name}.pdf")
        await message.answer_document(file_buffered)
    except Exception as e:
        logger.error(e)
        await bot.send_message(message.chat.id, "Произошла ошибка")
    else:
        await bot.send_message(
            message.chat.id, "Для генерации нового файла нажмите /start"
        )
    finally:
        await state.clear()


async def generate_pdf(data):
    logger.info(f"data: {data}")

    project_path = pathlib.Path(__file__).parent
    document_name = f"Счет-договор на поставку товара № {data['contract_number']}"
    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    tmp_file.write(project_path.joinpath("pdf/invoice_28955336.pdf").read_bytes())
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
    # pdfmetrics.registerFont(TTFont('FreeSans', '/Users/levniz/Desktop/40k_bots/pdf_bot/font/freesans/FreeSans.ttf'))
    # pdfmetrics.registerFont(TTFont('FreeSansBold', '/Users/levniz/Desktop/40k_bots/pdf_bot/font/freesans/FreeSansBold.ttf'))
    c.setFont("FreeSans", 12)

    # Путь к изображениям
    logo_path = project_path.joinpath("assets/logo.png")
    signature_path = project_path.joinpath("assets/sig.png")
    stamp_path = project_path.joinpath("assets/stamp_mockup.png")
    electronic_signature_path = project_path.joinpath(
        "assets/electronic_signature_badge.png"
    )

    # Добавление данных компании
    c.setFont("FreeSansBold", 11)
    c.drawString(10 * mm, height - 20 * mm, 'ООО "Простор"')
    c.setFont("FreeSans", 9)
    c.drawString(10 * mm, height - 25 * mm, "ОГРН: 1197746047938")
    c.drawString(10 * mm, height - 30 * mm, "ИНН: 7728458381")
    c.drawString(
        10 * mm,
        height - 35 * mm,
        "Юр. адрес: 117279, город Москва, Профсоюзная ул., д. 97",
    )

    # Добавление номера договора и даты
    c.setFont("FreeSans", 9)
    c.drawString(180 * mm, height - 55 * mm, data["date"])
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

    ordered_item_lines = split_text(data["ordered_item"], 45)
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
    c.drawString(112 * mm, table_start_y - row_height + 2 * mm, data["quantity"])
    c.drawString(
        132 * mm,
        table_start_y - row_height + 2 * mm,
        format_number_with_separators(int(data["cost"].replace(" ", ""))),
    )
    c.drawString(
        162 * mm,
        table_start_y - row_height + 2 * mm,
        format_number_with_separators(
            int(data["quantity"].replace(" ", "")) * int(data["cost"].replace(" ", ""))
        ),
    )

    # Итоговая сумма
    c.drawString(132 * mm, table_start_y - 3 * row_height + 15 * mm, "Сумма")
    c.drawString(
        162 * mm,
        table_start_y - 3 * row_height + 15 * mm,
        format_number_with_separators(
            int(data["quantity"].replace(" ", "")) * int(data["cost"].replace(" ", ""))
        ),
    )

    c.drawString(132 * mm, table_start_y - 3 * row_height + 5 * mm, "Всего к оплате")
    c.drawString(
        162 * mm,
        table_start_y - 3 * row_height + 5 * mm,
        format_number_with_separators(
            int(data["quantity"].replace(" ", "")) * int(data["cost"].replace(" ", ""))
        ),
    )

    # Добавление данных покупателя
    # c.drawString(150 * mm, height - 200 * mm, "Покупатель:")
    # c.drawString(150 * mm, height - 205 * mm, data['sbp_full_name'])
    # c.drawString(150 * mm, height - 210 * mm, f"Адрес: {data['address']}")
    # c.drawString(150 * mm, height - 215 * mm, f"Телефон: {data['sbp_phone']}")

    c.setFont("FreeSans", 9)
    c.drawString(130 * mm, height - 192 * mm, "Покупатель:")
    c.drawString(
        130 * mm,
        height - 197 * mm,
        f"{data['last_name']} {data['first_name']} {data['middle_name']}",
    )

    address_lines = split_text(data["address"], 45)
    c.drawString(130 * mm, height - 202 * mm, f"Адрес: {address_lines[0]}")
    logger.info(f"address_lines: {height - 202 * mm}")
    # Draw the remaining lines below the first line
    for i, line in enumerate(address_lines[1:]):
        c.drawString(
            130 * mm, height - 565 - row_height + 5.5 * mm - (i + 1) * 2.5 * mm, line
        )

    # c.drawString(130 * mm, height - 202 * mm, f"Адрес: {data['address']}")
    c.drawString(130 * mm, height - 212 * mm, f"Телефон: {data['phone']}")
    c.drawString(130 * mm, height - 217 * mm, f"_____________________________")
    c.drawString(
        130 * mm,
        height - 222 * mm,
        f"/{data['last_name']} {data['first_name']} {data['middle_name']}/",
    )

    # c.setFont('FreeSans', 9)
    # Обработка подписи для удаления черного фона
    signature_img = Image.open(signature_path).convert("RGBA")
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
    signature_img.save(project_path.joinpath("assets/signature_no_bg.png"), "PNG")

    text = """\
    1. Предметом настоящего Счет-договора является поставка Товара с вышеуказанным перечнем.
    2. Поставщик обязан передать Товар Покупателю в срок от 15 до 25 календарных дней с момента зачисления оплаты.
    3. Оплаченный Товар доставляется Покупателю силами Поставщика с использованием услуг транспортных
    компаний и обязательным страхованием на полную сумму заказа.
    4. Поставщик гарантирует доставку Товара Покупателю по ценам и в сроки, указанные в настоящем Счет-договоре.
    5. Поставщик гарантирует, что данный Товар новый, в заводской упаковке, надлежащего качества,
    соответствует своим техническим характеристикам, назначению и всем требованиям ГОСТа.
    6. В случае просрочки поставки Товара Поставщиком в срок, указанный в Счет-договоре, Поставщик
    уплачивает Покупателю неустойку в размере 0,5% от цены не поставленного Товара за каждый день просрочки
    поставки до фактического исполнения обязательства по настоящему Счет-договору.
    7. При приемке Товара Покупатель проверяет комплектность, отсутствие видимых дефектов и механических
    повреждений. В случае обнаружения дефектов и/или некомплектности Товара, Покупатель составляет Акт
    совместно с представителем транспортной компании, где указывает соответствующие недостатки. Поставщик
    обязуется заменить Товар или вернуть денежные средства в полном объеме в течении 3 (трех) рабочих дней.
    8. Претензии по качеству товара принимаются в течении 30 дней с момента принятия товара Покупателем.
    9. Гарантийный срок (установленный заводом-изготовителем) исчисляется с момента передачи товара
    Покупателю.
    10. Поставка осуществляется на условиях 100% (полной) предоплаты товара по настоящему Счет-договору.
    11. Настоящий Счет-договор действителен в течении 1 (одного) дня от даты его составления. При отсутствии
    оплаты в указанный срок настоящий Счет-договор признается недействительным.
    """

    text_object = c.beginText(10 * mm, height - 110 * mm)
    text_object.setFont("FreeSans", 9)
    text_object.textLines(text)
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
    c.drawString(10 * mm, 100 * mm, 'ООО "Простор"')

    footer_text = """\
    ОГРН: 1197746047938
    ИНН: 7728458381
    Юр. адрес: 117279, город Москва, Профсоюзная ул., д. 97
    Центральный склад: 141895, Московская область\nГлазово деревня, 30, «PNK Парк Северное Шереметьево»


    __________________________/Любовский Алексей Михайлович/
        """

    footer_text_object = c.beginText(10 * mm, 95 * mm)
    footer_text_object.setFont("FreeSans", 9)
    footer_text_object.textLines(footer_text)
    c.drawText(footer_text_object)
    c.drawImage(
        electronic_signature_path,
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
        project_path.joinpath("assets/signature_no_bg.png"),
        20 * mm,
        60 * mm,
        width=40 * mm,
        height=20 * mm,
        mask="auto",
    )

    # Добавление текста по центру второй страницы
    c.showPage()

    c.setFont("FreeSansBold", 11)
    c.drawString(10 * mm, height - 20 * mm, 'ООО "Простор"')
    c.setFont("FreeSans", 9)
    c.drawString(10 * mm, height - 25 * mm, "ОГРН: 1197746047938")
    c.drawString(10 * mm, height - 30 * mm, "ИНН: 7728458381")
    c.drawString(
        10 * mm,
        height - 35 * mm,
        "Юр. адрес: 117279, город Москва, Профсоюзная ул., д. 97",
    )

    c.drawImage(
        electronic_signature_path,
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
        3. Укажите корпоративный номер компании: {data['sbp_phone']}
        4. Укажите сумму перевода: {format_number_with_separators(int(data['quantity'].replace(" ", "")) * int(data['cost'].replace(" ", "")))} руб.
        5. Получатель: ООО «Простор», в лице главного бухгалтера: {data['sbp_full_name']}
        6. Выберите банк: {data['sbp_bank']}
        7. Выполните перевод.
    """
    )
    c.drawText(text_object)

    text_object = c.beginText(10 * mm, height - 200 * mm)
    text_object.setFont("FreeSans", 9)
    c.drawText(text_object)

    c.drawString(10 * mm, 185 * mm, "Поставщик:")

    # c.setFont('FreeSansBold', 12)
    c.drawString(10 * mm, 180 * mm, 'ООО "Простор"')

    footer_text = """\
    ОГРН: 1197746047938
    ИНН: 7728458381
    Юр. адрес: 117279, город Москва, Профсоюзная ул., д. 97
    Центральный склад: 141895, Московская область\nГлазово деревня, 30, «PNK Парк Северное Шереметьево»


    __________________________/Любовский Алексей Михайлович/
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
        f"{data['last_name']} {data['first_name']} {data['middle_name']}",
    )
    # c.drawString(130 * mm, height - 122 * mm, f"Адрес: {data['address']}")
    address_lines = split_text(data["address"], 45)
    c.drawString(130 * mm, height - 122 * mm, f"Адрес: {address_lines[0]}")
    logger.info(f"address_lines: {height - 202 * mm}")
    # Draw the remaining lines below the first line
    for i, line in enumerate(address_lines[1:]):
        c.drawString(
            130 * mm, height - 340 - row_height + 5.5 * mm - (i + 1) * 2.5 * mm, line
        )

    c.drawString(130 * mm, height - 132 * mm, f"Телефон: {data['phone']}")
    c.drawString(130 * mm, height - 137 * mm, f"_____________________________")
    c.drawString(
        130 * mm,
        height - 142 * mm,
        f"/{data['last_name']} {data['first_name']} {data['middle_name']}/",
    )

    c.setFont("FreeSans", 9)
    c.drawImage(
        stamp_path, 20 * mm, 100 * mm, width=50 * mm, height=50 * mm, mask="auto"
    )
    c.drawImage(
        project_path.joinpath("assets/signature_no_bg.png"),
        20 * mm,
        140 * mm,
        width=40 * mm,
        height=20 * mm,
        mask="auto",
    )

    # Сохранение PDF
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


async def main():
    dp.include_router(form_router)
    await bot.set_my_commands(
        commands=[
            BotCommand(command="/start", description="Start the bot"),
            BotCommand(command="/clear_context", description="Cleat current context"),
        ]
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    configure_logging(settings.log_level_number, access_log_path="logs/access.log")
    asyncio.run(main())
