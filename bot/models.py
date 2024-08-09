from dataclasses import dataclass

from pydantic import BaseModel, constr, conint


class ContractFormData(BaseModel):
    date: constr(strip_whitespace=True)
    contract_number: constr(strip_whitespace=True)
    first_name: constr(strip_whitespace=True)
    last_name: constr(strip_whitespace=True)
    middle_name: constr(strip_whitespace=True)
    phone: constr(
        strip_whitespace=True,
    )  # Example regex for phone numbers
    address: constr(strip_whitespace=True)
    ordered_item: constr(strip_whitespace=True)
    quantity: conint(ge=1)  # Must be at least 1
    cost: conint(ge=0)  # Cost must be non-negative
    sbp_phone: constr(
        strip_whitespace=True,
    )  # Same regex as phone
    sbp_full_name: constr(strip_whitespace=True)
    sbp_bank: constr(strip_whitespace=True)


@dataclass
class Company:
    name: str
    ogrn: str
    inn: str
    central_warehouse: str
    legal_address: str


@dataclass
class Contract:
    text: str
    company: Company
    contract_executor_fio: str
