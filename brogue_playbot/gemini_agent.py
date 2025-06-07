import json
import traceback

from dotenv import load_dotenv
from google import genai
from google.genai import types, errors
from pydantic import BaseModel
from PIL import Image


class GeminiAPIError(Exception):
    """Base class for Gemini API related errors"""

    pass


class InvalidAPIKeyError(GeminiAPIError):
    pass


class QuotaExceededError(GeminiAPIError):
    pass


class ModelResponseParsingError(GeminiAPIError):
    pass


class GeminiAgent:
    def __init__(self, api_key: str | None = None):
        load_dotenv()
        self.client = genai.Client(api_key=api_key)

    def _parse_json_from_response(self, response_text: str) -> dict | None:
        """Parse JSON object from LLM response."""
        json_text = response_text.strip()
        # 마크다운 코드 블록 제거
        if json_text.startswith("```json"):
            json_text = json_text[len("```json") :]
        if json_text.startswith("```"):  # 가끔 ```json 대신 ```만 오는 경우
            json_text = json_text[len("```") :]
        if json_text.endswith("```"):
            json_text = json_text[: -len("```")]

        json_text = json_text.strip()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            print(
                f"JSON 파싱 오류: {e}\n원본 텍스트: {json_text[:500]}..."
            )  # 너무 길면 잘라서 출력
            return None

    def generate(
        self,
        prompt: str,
        model_name: str = "gemini-1.5-flash-latest",
        image: Image.Image | None = None,
        config=None,
    ) -> str | None:
        """Send text generation request with optional image."""
        try:
            content = [prompt, image] if image else prompt
            response = self.client.models.generate_content(
                model=model_name, contents=content, config=config
            )
            return response.text.strip() if response.text else None
        except errors.APIError as e:
            if e.code == 401:
                raise InvalidAPIKeyError(f"Invalid API key: {e.message}")
            elif e.code == 429:
                raise QuotaExceededError(f"Quota exceeded: {e.message}")
            else:
                raise GeminiAPIError(f"API error: {e.message}")
        except Exception as e:
            raise e
            error_type = "이미지 기반 생성" if image else "텍스트 생성"
            print(f"{error_type} 중 오류 발생: {e}")
            return None

    def generate_json(
        self,
        prompt: str,
        model_name: str = "gemini-1.5-flash-latest",
        image: Image.Image | None = None,
        json_schema=None,
    ) -> dict | None:
        """Generate JSON response. Optionally send request with image."""
        json_config = {"response_mime_type": "application/json"}
        response_text = self.generate(
            prompt, model_name=model_name, image=image, config=json_config
        )
        if response_text:
            return self._parse_json_from_response(response_text)
        return None


class GameState(BaseModel):
    player_health: int
    player_hunger: str
    current_depth: int
    messages: list[str]
    visible_entities: list[str]
    inventory_snippet: list[str]
    map_description: str


class GeminiVLMAgent(GeminiAgent):
    def generate_content(self, image: Image.Image) -> dict | None:
        game_state_schema = {
            "type": "object",
            "properties": {
                "player_health": {
                    "type": "object",
                    "description": "Player's current and maximum health.",
                    "properties": {
                        "current": {"type": "integer"},
                        "max": {"type": "integer"},
                    },
                    "required": ["current", "max"],
                },
                "player_hunger": {
                    "type": "string",
                    "description": "The player's hunger status.",
                    "enum": [
                        "Satiated",
                        "Normal",
                        "Hungry",
                        "Weak",
                        "Fainting",
                        "Starving",
                        "Unknown",
                    ],
                },
                "current_depth": {
                    "type": "integer",
                    "description": "The current dungeon depth level.",
                },
                "messages": {
                    "type": "array",
                    "description": "Recent messages from the game log.",
                    "items": {"type": "string"},
                },
                "visible_entities": {
                    "type": "array",
                    "description": "A list of all visible enemies and items on the map.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": ["enemy", "item", "stairway", "other"],
                            },
                            "location_desc": {"type": "string"},
                        },
                        "required": ["name", "type", "location_desc"],
                    },
                },
                "inventory_snippet": {
                    "type": "array",
                    "description": "A list of notable items in the player's inventory.",
                    "items": {"type": "string"},
                },
                "map_description": {
                    "type": "string",
                    "description": "A textual summary of the player's immediate surroundings.",
                },
            },
            "required": [
                "player_health",
                "player_hunger",
                "current_depth",
                "messages",
                "visible_entities",
                "inventory_snippet",
                "map_description",
            ],
        }

        prompt = """
        당신은 Brogue 게임 화면 분석 전문가입니다. 다음 이미지에서 게임 상태를 분석하여 JSON 형식으로 알려주세요.
        JSON에는 다음 키들이 포함되어야 합니다:
        - "player_health": 플레이어의 현재 체력 (예: "25/30" 또는 숫자)
        - "player_hunger": 플레이어의 허기 상태 (예: "Normal", "Hungry", "Starving")
        - "current_depth": 현재 깊이 (예: "Depth: 3")
        - "messages": 최근 게임 메시지 (화면 하단 등, 배열 형태)
        - "visible_enemies": 보이는 적들의 목록. 각 적은 이름, 상대적 위치(예: "북동쪽 고블린")를 포함. (예: [{"name": "goblin", "location_desc": "2시 방향"}])
        - "visible_items": 바닥에 보이는 아이템 목록. 각 아이템은 이름, 상대적 위치를 포함. (예: [{"name": "dagger", "location_desc": "발 밑"}])
        - "inventory_snippet": 인벤토리의 주요 아이템 몇 가지 (예: ["healing potion", "dagger", "scroll of identify?"])
        - "map_description": 플레이어 주변 지형에 대한 간략한 설명 (예: "좁은 복도, 북쪽에 문이 보임")

        최대한 정확하고 간결하게, 요청한 JSON 형식으로만 답변해주세요.
        만약 특정 정보를 읽을 수 없다면, 해당 키의 값으로 null 또는 빈 배열/문자열을 사용하세요.
        """
        return self.generate_json(prompt, image=image, json_schema=game_state_schema)


class GeminiPolicyAgent(GeminiAgent):
    def generate_content(self, game_state: dict) -> dict | None:
        game_state_str = json.dumps(game_state, indent=2, ensure_ascii=False)
        # Policy 프롬프트: 이전과 동일하게 유지, 필요시 수정
        prompt = f"""
        당신은 Brogue 게임을 아주 잘하는 AI 에이전트입니다.
        현재 게임 상태는 다음과 같습니다:
        {game_state_str}

        다음 중 가장 적절한 행동 하나를 선택하여 그 명령어를 반환해주세요.
        가능한 행동 명령어 형식 (Brogue 기본 키 기준, 실제 키에 맞게 수정 필요):
        - 이동: "move k" (북), "move j" (남), "move h" (서), "move l" (동), "move y", "move u", "move b", "move n" (대각선)
        - 공격: "attack <방향키>" (예: "attack h" - 왼쪽에 있는 적 공격. 실제로는 'f' 누르고 방향키)
        - 아이템 줍기: "pickup" (,)
        - 인벤토리 열기: "inventory" (i)
        - 아이템 사용/읽기/마시기: "quaff <아이템문자>", "read <아이템문자>", "zap <아이템문자>" (q, r, z)
        - 계단 내려가기: "go_down" (>)
        - 대기: "wait" (.)

        최우선 순위:
        1. 체력이 30% 미만이고 회복 아이템이 있다면 사용하세요. (예: "quaff a" - a가 힐링포션일 경우)
        2. 배고픔 상태(Hungry, Starving)이고 음식이 있다면 먹으세요.
        3. 바로 옆에 적이 있다면 공격하세요. 위험하면 도망가세요.
        4. 유용한 아이템이 바닥에 있다면 주우세요.
        5. 주변을 탐험하세요. 아직 가지 않은 곳으로 이동하거나, 문이 있으면 열어보세요.
        6. 위험한 상황이거나 뚜렷한 할 일이 없으면 "wait" 하세요.

        가장 적절한 행동 명령어 하나만 반환해주세요. (예: "move k")
        """
        try:
            print("Policy 모델에 행동 결정 요청 중...")
            response = self.generate(prompt)
            print(f"response: {response}")
            action = response.strip()
            print(f"Policy 결정된 행동: {action}")
            return action
        except Exception as e:
            traceback.print_exc()
            print(f"Policy 처리 중 오류 발생: {e}")
            if "response" in locals() and hasattr(response, "prompt_feedback"):
                print(f"Policy 프롬프트 피드백 (오류 시): {response.prompt_feedback}")
            return "wait"  # 오류 발생 시 기본 행동
