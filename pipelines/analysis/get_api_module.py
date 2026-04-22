from dotenv import load_dotenv
import json
import os

import requests


DEFAULT_API_KEY_ENV = "OPEN_GOVERMENT_API_KEY"


class GET_API:
    def __init__(self, api_key_env: str = DEFAULT_API_KEY_ENV):
        load_dotenv()
        self.key = os.getenv(api_key_env)

    def get_response(self, url, params):
        """
        api 요청을 보내는 코드
        """
        params = params.copy()
        params["KEY"] = self.key
        response = requests.get(url=url, params=params)
        if response.status_code == 200:
            return response

        print(response.text)
        return None

    def response_to_json(self, file_path, response):
        """
        api 응답을 json으로 저장하는 코드
        """
        try:
            with open(file_path, "w") as f:
                json.dump(response.json(), f)
        except Exception as e:
            print(f"json으로 저장이 안 되었습니다 {e}")
