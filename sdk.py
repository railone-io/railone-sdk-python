
import time
import hashlib
import hmac
import base64
import logging
import json
import requests

class RailoneClient(object):
    REQUEST_OK = 0
    ORG_BALANCE_INSUFFICIENT = 111011
    CARD_FROZEN = 111015

    KYC_PENDING = 0
    KYC_SUCCEED = 1
    KYC_FAILED = 2

    RAILONE_HOST = "railone_host"
    RAILONE_PASSWORD = "password"
    RAILONE_API_KEY = "api_key"
    RAILONE_API_SECRET = "api_secret"

    @classmethod
    def _generate_signature_headers(cls, method, url, body=None):

        # change this
        password = cls.RAILONE_PASSWORD
        api_key = cls.RAILONE_API_KEY
        api_secret = cls.RAILONE_API_SECRET

        # format payload
        current_time = int(time.time() * 1000)
        payload = {
            "timestamp": current_time,
            "method": method,
            "api_key": api_key,
            "url": url,
        }

        if body:
            params = [f"{k}={v}" for k, v in body.items()]
            params.sort()
            body_string = "&".join(params)
            payload.update({"body": body_string})

        payload_string = "".join(str(x) for x in payload.values())
        signature = str(
            base64.b64encode(
                hmac.new(
                    api_secret.encode(), payload_string.encode(), hashlib.sha256
                ).digest()
            ),
            "utf-8",
        )

        authorization = ":".join(
            str(x) for x in ["Railone", api_key, current_time, signature]
        )
        return {
            "Authorization": authorization,
            "Access-Passphrase": password,
            "Content-Type": "application/json",
        }

    @classmethod
    def _requests(cls, method, path, data=None):
        method = method.upper()
        host = cls.RAILONE_HOST
        signature_headers = cls._generate_signature_headers(
            method=method, url=path, body=data
        )

        resp = None
        if method == "GET":
            resp = requests.get(
                url=f"{host}{path}", data=json.dumps(data), headers=signature_headers
            )
        elif method == "POST":
            resp = requests.post(
                url=f"{host}{path}", data=json.dumps(data), headers=signature_headers
            )
        elif method == "PUT":
            resp = requests.put(
                url=f"{host}{path}", data=json.dumps(data), headers=signature_headers
            )

        if resp.status_code != 200:
            raise Exception(
                f"call railone open api error: {resp.status_code}, {resp.text}, "
                f"sig: {signature_headers}, "
                f"method: {method}, "
                f"path: {path}, "
                f"data: {json.dumps(data)}"
            )

        result = resp.json()
        return result["result"]

    # ********************** 用户KYC相关的API ******************** #
    @classmethod
    def send_kyc_by_account(
            cls,
            account_no,
            account_name,
            first_name,
            last_name,
            maiden_name,
            gender,
            birthday,
            nationality,
            country,
            country_code,
            city,
            state,
            zipcode,
            doc_type,
            doc_no,
            mobile,
            mail,
            address,
            front_doc,
            back_doc,
            mix_doc,
            card_type_id,
            extra_info="",
    ):
        path = "/api/v1/customers/accounts"
        data = {
            "acct_no": account_no,
            "acct_name": account_name,
            "first_name": first_name,
            "last_name": last_name,
            "maiden_name": maiden_name,
            "gender": gender,
            "birthday": birthday,
            "nationality": nationality,
            "country": country,
            "country_code": country_code,
            "city": city,
            "state": state,
            "zipcode": zipcode,
            "doc_no": doc_no,
            "doc_type": doc_type,
            "front_doc": front_doc,
            "back_doc": back_doc,
            "mix_doc": mix_doc,
            "area_code": country_code,
            "mobile": mobile,
            "mail": mail,
            "address": address,
            "card_type_id": card_type_id,
            "kyc_info": extra_info,
        }
        is_complete = cls._requests(method="POST", path=path, data=data)
        return is_complete

    @classmethod
    def get_kyc_status_by_account(cls, account_no):
        path = f"/api/v1/customers/accounts"
        query = f"?acct_no={account_no}"
        result = cls._requests(method="GET", path=path + query, data=None)
        res = result["records"][0]
        return res["status"], res["reason"]

    # ********************** 用户银行卡相关的API ******************** #
    @classmethod
    def get_debit_card_type(cls):
        path = "/api/v1/card/type"
        data = None
        result = cls._requests(method="GET", path=path, data=data)
        return result["records"]

    @classmethod
    def get_fee_rate(cls, card_type_id):
        path = f"/api/v1/rates?card_type_id={card_type_id}"
        data = None
        result = cls._requests(method="GET", path=path, data=data)
        return result

    @classmethod
    def create_debit_card_by_account(cls, acct_no, card_type_id):
        path = "/api/v1/debit-cards"
        data = {"acct_no": acct_no, "card_type_id": card_type_id, "expose": "true"}
        result = cls._requests(method="POST", path=path, data=data)
        return result

    @classmethod
    def bank_active_status(cls, card_no):
        path = "/api/v1/bank/account-status"
        data = {"card_no": card_no}
        is_active = cls._requests(method="POST", path=path, data=data)
        return is_active

    @classmethod
    def activation_debit_card_by_account(cls, account_no, card_no):
        path = "/api/v1/debit-cards/status"
        data = {"acct_no": account_no, "card_no": card_no}
        is_active = cls._requests(method="PUT", path=path, data=data)
        return is_active

    @classmethod
    def get_debit_cards_by_account(
            cls, account_no, page_num=0, page_size=20, former_time=None, latter_time=None
    ):
        path = f"/api/v1/debit-cards?acct_no={account_no}"
        data = {"account_no": account_no, "page_num": page_num, "page_size": page_size}
        if former_time and latter_time:
            data.update({"former_time": former_time, "latter_time": latter_time})
        return cls._requests(method="GET", path=path, data=data)

    @classmethod
    def recharge_debit_card_by_account(
            cls, account_no, card_no, amount, coin_type, cust_tx_id, remark=""
    ):
        coin_obj = get_coin_by_code(coin_type)
        path = "/api/v1/deposit-transactions"
        data = {
            "acct_no": account_no,
            "card_no": card_no,
            "amount": amount,
            "coin_type": coin_obj.get_display_code(),
            "cust_tx_id": cust_tx_id,
            "remark": remark,
        }
        resp = cls._requests(method="POST", path=path, data=data)
        return resp

    @classmethod
    def get_recharge_records_by_tx_id(cls, tx_id):
        path = f"/api/v1/deposit-transactions/{tx_id}/status"
        data = None
        resp = cls._requests(method="GET", path=path, data=data)
        return resp

    @classmethod
    def get_transaction_records_by_card_no(
            cls, card_no, former_time=None, latter_time=None
    ):
        path = f"/api/v1/bank/transaction-record"
        data = {
            "card_no": card_no,
            "former_time": former_time,
            "latter_time": latter_time,
        }
        return cls._requests(method="GET", path=path, data=data)

    @classmethod
    # TODO to be done
    def get_balance_by_card(cls, card_no):
        path = f"/api/v1/bank/balance"
        data = {"card_no": card_no}
        result = cls._requests(method="POST", path=path, data=data)
        return result["result"]
