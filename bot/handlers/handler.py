from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from loguru import logger

from bot.decorators import message_process_error
from bot.models import ContractFormData
from bot.settings import bot, settings
from bot.utils import ask_next_state, generate_pdf, validate_state_data

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


@form_router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    commands = [f"{x.command} - {x.description}" for x in settings.bot_commands]
    commands_text = '\n'.join(commands)
    await message.answer(f"Меню\n{commands_text}")


@form_router.message(Command("company_prostor"))
@form_router.message(Command("company_stroytorgcomplect"))
async def create_contract(message: Message, state: FSMContext):
    if "/company_" not in message.text:
        return
    company_name = message.text.replace("/company_", "")
    await state.update_data({"company_name": company_name})
    await message.reply(f"Выбрана компания: {company_name}")
    await ask_next_state(message, state, Form.date, "Введите дату договора:")


@form_router.message(Command("clear_context"))
async def clear_context(message: Message, state: FSMContext):
    await state.clear()
    await message.reply("Контекст очищен")


@form_router.message(Form.date)
async def process_date(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(date=message.text)
    await ask_next_state(
        message, state, Form.contract_number, "Введите номер договора:"
    )


@form_router.message(Form.contract_number)
async def process_contract_number(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(contract_number=message.text)
    await ask_next_state(message, state, Form.first_name, "Введите имя:")


@form_router.message(Form.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(first_name=message.text)
    await ask_next_state(message, state, Form.last_name, "Введите фамилию:")


@form_router.message(Form.last_name)
async def process_last_name(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(last_name=message.text)
    await ask_next_state(
        message, state, Form.middle_name, "Введите отчество (если нет, напишите '-'):"
    )


@form_router.message(Form.middle_name)
async def process_middle_name(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(middle_name=message.text)
    await ask_next_state(message, state, Form.phone, "Введите телефон:")


@form_router.message(Form.phone)
@message_process_error
async def process_phone(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(phone=message.text)
    await ask_next_state(message, state, Form.address, "Введите адрес:")


@form_router.message(Form.address)
async def process_address(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(address=message.text)
    await ask_next_state(message, state, Form.ordered_item, "Введите заказанный товар:")


@form_router.message(Form.ordered_item)
async def process_ordered_item(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(ordered_item=message.text)
    await ask_next_state(message, state, Form.quantity, "Введите количество:")


@form_router.message(Form.quantity)
@message_process_error
async def process_quantity(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(quantity=message.text)
    await ask_next_state(message, state, Form.cost, "Введите стоимость:")


@form_router.message(Form.cost)
@message_process_error
async def process_cost(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(cost=message.text)
    await ask_next_state(
        message, state, Form.sbp_phone, "Введите номер телефона (СБП):"
    )


@form_router.message(Form.sbp_phone)
@message_process_error
async def process_sbp_phone(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(sbp_phone=message.text)
    await ask_next_state(message, state, Form.sbp_full_name, "Введите ФИО (СБП):")


@form_router.message(Form.sbp_full_name)
async def process_sbp_full_name(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(sbp_full_name=message.text)
    await ask_next_state(message, state, Form.sbp_bank, "Введите банк (СБП):")


@form_router.message(Form.sbp_bank)
@form_router.message(Command("retry"))
async def process_sbp_bank(message: Message, state: FSMContext):
    await validate_state_data(state, message)
    await state.update_data(sbp_bank=message.text)
    data = await state.get_data()
    error_msg = f"Произошла ошибка. Попробуйте еще раз /retry.\nСбросить текущее состояние /start"
    try:
        contract_data = ContractFormData(**data)
        await bot.send_message(message.chat.id, "Пожалуйста, ожидайте...")
        try:
            doc_name, file = await generate_pdf(contract_data, data.get("company_name"))
            file_buffered = types.FSInputFile(file.name, filename=f"{doc_name}.pdf")
            await message.answer_document(file_buffered)
            await state.clear()
        except Exception as e:
            logger.error(e)
            await bot.send_message(message.chat.id, error_msg)
        else:
            await bot.send_message(
                message.chat.id, "Для генерации нового файла нажмите /start"
            )
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(error_msg)
