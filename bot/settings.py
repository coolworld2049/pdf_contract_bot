import logging
import pathlib
from typing import Dict

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.models import Contract, Company


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

    @property
    def bot_commands(self):
        return [
            BotCommand(command="/start", description="Меню. Сбросить состояние"),
            # BotCommand(command="/company_prostor", description="ООО 'Простор'"),
            BotCommand(
                command="/company_stroytorgcomplect", description="ООО 'Стройторгкомплект'"
            ),
            BotCommand(
                command="/retry", description="Еще раз"
            ),
        ]


settings = Settings()

bot = Bot(token=settings.bot_token)
storage = (
    RedisStorage.from_url(url=f"redis://{settings.redis_host}:{settings.redis_port}")
    if settings.use_redis
    else MemoryStorage()
)
dp = Dispatcher(storage=storage)

company_contract: Dict[str, Contract] = {
    "prostor": Contract(
        text="""\
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
    """,
        contract_executor_fio="Любовский Алексей Михайлович",
        company=Company(
            name='ООО "Простор"',
            ogrn="1197746047938",
            inn="7728458381",
            central_warehouse="141895, Московская область\nГлазово деревня, 30, «PNK Парк Северное Шереметьево»",
            legal_address="117279, город Москва, Профсоюзная ул., д. 97",
        ),
    ),
    "stroytorgcomplect": Contract(
        text="""\
    1. Предметом настоящего Счет-договора является поставка Товара с вышеуказанным перечнем.
    2. Поставщик обязан передать Товар Покупателю в срок от 15 до 25 рабочих дней с момента зачисления оплаты.
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
    """,
        contract_executor_fio="Шишкин Александр Сергеевич",
        company=Company(
            name='ООО "Стройторгкомплект" ',
            ogrn="1157746053046",
            inn="7728188093",
            central_warehouse="108811, г. Москва, Киевское ш., д. 4, БП “Румянцево”",
            legal_address="108817, г. Москва, п. Внуковское, ул. Лётчика Ульянина, д. 6",
        ),
    ),
}
