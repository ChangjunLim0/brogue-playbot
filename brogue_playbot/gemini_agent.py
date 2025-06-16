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
            print(f"JSON 파싱 오류: {e}\n원본 텍스트: {json_text[:500]}...")
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
You are an expert AI game analyst. Your task is to analyze the provided screenshot of the roguelike game "Brogue" and extract the game's current state into a structured JSON format.

You must follow these rules precisely:

Analyze the entire game screen to gather all required information.
Output ONLY a valid JSON object. Do not include any other text, explanations, or markdown formatting like ```json.
Here is the required JSON structure and instructions for each field:

JSON Structure:

JSON
{
  "player_status": {
    "health_percent": 0,
    "nutrition_percent": 0,
    "strength": 0,
    "armor": 0,
    "stealth_range": 0
  },
  "game_info": {
    "depth": 0,
    "messages": []
  },
  "relative_grid_9x9": [],
  "crucial_info": [],
  "ground_items": []
}
Instructions for each field:

player_status: Extract the player's stats from the top-left panel.

health_percent, nutrition_percent: Estimate the percentage (0-100) based on the fullness of the 'Health' and 'Nutrition' bars.
strength, armor, stealth_range: Extract the numerical values for 'Str', 'Armor', and 'Stealth range'.
game_info: Extract general game information.

depth: Get the current dungeon depth from the bottom-left of the screen.
messages: Get the last 2-3 messages from the log in the top-right panel. The most recent message should be the first element in the list.
relative_grid_9x9: Create a 9x9 grid of strings, centered on the player character (@).

The grid must represent the area immediately surrounding the player. The player (@) is always at the center [4][4].
Map the game symbols to the following string values:
"#" -> "WALL"
." -> "FLOOR"
"+" -> "DOOR"
"~" -> "WATER"
"@" -> "PLAYER"
Any item symbol (*, [, /, ?, %, )) -> "ITEM"
Any monster symbol (r, k, j, e, etc.) -> "MONSTER"
Unseen/black areas -> "UNSEEN"
Stairs (>, <) -> "STAIRS"
crucial_info: Identify all monsters and stairs anywhere on the visible map, even if they are outside the 9x9 grid. This is a list of objects.

For each found entity, create an object with type, symbol, and position.
type: Can be "MONSTER" or "STAIRS_DOWN".
symbol: The character on the map (e.g., "k", ">").
position: The absolute x, y coordinates of the entity on the map grid. Assume the top-left corner of the map view is (0,0).
ground_items: Extract the list of items at the player's location from the panel to the left of the map. This should be a list of strings, exactly as they appear.
        """
        return self.generate_json(prompt, image=image, json_schema=game_state_schema)


class GeminiPolicyAgent(GeminiAgent):
    def generate_content(self, game_state: dict) -> dict | None:
        game_state_str = json.dumps(game_state, indent=2, ensure_ascii=False)
        prompt = f"""
You are an expert AI player for the roguelike game "Brogue". Your primary goal is to survive and explore the dungeon to find the stairs leading to the next level.

You will be given the current game state as a single JSON object. Your task is to analyze this state and choose the single best action to take next from a strictly limited list of available actions.

Here is the JSON object.
{game_state_str}

Available Actions:

You must choose one of the following six actions:

MOVE_UP
MOVE_DOWN
MOVE_LEFT
MOVE_RIGHT
SEARCH
REST
Your Response:

Your entire response must be a single word from the list above. Do not include any other text, JSON, or explanations.

Strategic Priorities:

To make your decision, follow these priorities in order:

Immediate Survival (Highest Priority):

If your player_status.health_percent is below 70%, your top priority is to heal.
Choose REST only if there are no monsters in your relative_grid_9x9 or crucial_info list. If there are monsters nearby, it is too dangerous to rest. In that case, move away from the threat.
Threat Avoidance:

If there is a monster right next to you (e.g., at [4][3], [4][5], [3][4], or [5][4] in the relative_grid_9x9), you must move away from it to a safe position. Prioritize moving to a tile that is not adjacent to any monster.
Exploration and Objectives:

If you are safe, your goal is to explore.
Check the crucial_info list. If you see "type": "STAIRS_DOWN", your main goal is to move towards its coordinates.
If there are no stairs in sight, check the relative_grid_9x9 for ITEM tiles. Move towards the nearest item.
If no specific objectives are visible, move towards the nearest "FLOOR" tile that is adjacent to an "UNSEEN" tile to uncover more of the map.
Dealing with Dead Ends:

If you are surrounded by WALL or UNSEEN tiles and have no obvious path forward (i.e., you are in a dead end), choose SEARCH. This is useful for finding secret doors.
Default Action:

If none of the above conditions provides a clear choice, simply continue exploring by moving towards the nearest "UNSEEN" area.
Task:

Based on the following game state, what is your next action?
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
