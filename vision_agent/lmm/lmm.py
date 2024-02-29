import base64
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import requests

logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger(__name__)

_LLAVA_ENDPOINT = "https://cpvlqoxw6vhpdro27uhkvceady0kvvqk.lambda-url.us-east-2.on.aws"


def encode_image(image: Union[str, Path]) -> str:
    with open(image, "rb") as f:
        encoded_image = base64.b64encode(f.read()).decode("utf-8")
    return encoded_image


class LMM(ABC):
    @abstractmethod
    def generate(self, prompt: str, image: Optional[Union[str, Path]] = None) -> str:
        pass


class LLaVALMM(LMM):
    r"""An LMM class for the LLaVA-1.6 34B model."""

    def __init__(self, name: str):
        self.name = name

    def generate(
        self,
        prompt: str,
        image: Optional[Union[str, Path]] = None,
        temperature: float = 0.1,
        max_new_tokens: int = 1500,
    ) -> str:
        data = {"prompt": prompt}
        if image:
            data["image"] = encode_image(image)
        data["temperature"] = temperature  # type: ignore
        data["max_new_tokens"] = max_new_tokens  # type: ignore
        res = requests.post(
            _LLAVA_ENDPOINT,
            headers={"Content-Type": "application/json"},
            json=data,
        )
        resp_json: Dict[str, Any] = res.json()
        if resp_json["statusCode"] != 200:
            _LOGGER.error(f"Request failed: {resp_json['data']}")
        return cast(str, resp_json["data"])


class OpenAILMM(LMM):
    r"""An LMM class for the OpenAI GPT-4 Vision model."""

    def __init__(self, name: str):
        from openai import OpenAI

        self.name = name
        self.client = OpenAI()

    def generate(self, prompt: str, image: Optional[Union[str, Path]] = None) -> str:
        message: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        if image:
            extension = Path(image).suffix
            encoded_image = encode_image(image)
            message[0]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{extension};base64,{encoded_image}",
                        "detail": "low",
                    },
                },
            )

        response = self.client.chat.completions.create(
            model="gpt-4-vision-preview", messages=message  # type: ignore
        )
        return cast(str, response.choices[0].message.content)


def get_lmm(name: str) -> LMM:
    if name == "openai":
        return OpenAILMM(name)
    elif name == "llava":
        return LLaVALMM(name)
    else:
        raise ValueError(f"Unknown LMM: {name}, current support openai, llava")