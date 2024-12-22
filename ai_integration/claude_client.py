import anthropic
import game_interface.game_interface as interface
import os
import json
from simple_logger.logger import SimpleLogger
from ai_integration.conversation_cache import ConversationCache


LOGGER = SimpleLogger(__name__, log_file="claude_client.log")

class ToolParameter:
    """
    
    One object in the input_schema value for describing tools

    "type": "the type of input (eg object, string, integer)",
    "description": "the properties of the input (useful for objects)",
    
    """
    def __init__(self, name, type, description):
        self.name = name
        self.type = type
        self.description = description

    def to_dict(self):
        return {
            # "name": self.name,
            "type": self.type,
            "description": self.description
        }
    
    def to_json(self):
        return json.dumps({
            "name": self.name,
            "type": self.type, 
            "description": self.description 
        }, indent=2)

class Tool:
    """

    As specified by the anthropic docs: https://docs.anthropic.com/en/docs/build-with-claude/tool-use

    {
    "name": "The name of the tool. Must match the regex ^[a-zA-Z0-9_-]{1,64}$",
    "description": "A detailed plaintext description of what the tool does, when it should be used, and how it behaves.",
    "input_schema": "A JSON Schema object defining the expected parameters for the tool."
    }

    """
    def __init__(self, name, description, parameters):
        self.name = name
        self.description = description

        if not isinstance(parameters, list):
            raise ValueError("Parameters must be a list of ToolParameter objects. Got: " + str(parameters))
        if len(parameters) > 0 and not isinstance(parameters[0], ToolParameter):
            raise ValueError("Parameters must be a list of ToolParameter objects. Got: " + str(parameters))

        self.parameters = parameters

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    param.name: param.to_dict() for param in self.parameters
                },
                "required": [param.name for param in self.parameters]
            }
        }

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

class ClaudeClient:

    def __init__(self, model):

        if model == "gemini-2.0-flash":
            raise ValueError("Gemini 2.0 Flash is not supported by this client yet.")
        
        self.next_toolset = []
        self.toolset_results = []
        self.continue_flying = True

        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required.")
        self.anthropic = anthropic.Anthropic(api_key=self.api_key)
        self.conversation_cache = ConversationCache()
        self.tools = [
            Tool(
                "take_screenshot",
                "Takes a screenshot of the current game view.",
                [
                    ToolParameter("filename", "string", "The name to save the screenshot as (e.g., 'metrics.png'). Optional, defaults to 'screenshot.png'.")
                ]
            ),
            Tool(
                "press_key",
                "Presses and releases a specified keyboard key.",
                [
                    ToolParameter("key", "string", "The key to press (e.g., 'w', 's', 'a', 'd', 'Space').")
                ]
            ),
            Tool(
                "hold_key",
                "Holds down a specified keyboard key for a certain duration.",
                [
                    ToolParameter("key", "string", "The key to hold down (e.g., 'w', 's')."),
                    ToolParameter("duration", "number", "The duration in seconds to hold the key down.")
                ]
            ),
            Tool(
                "move_mouse",
                "Moves the mouse cursor to specific coordinates on the screen.",
                [
                    ToolParameter("x", "integer", "The x-coordinate to move the mouse to."),
                    ToolParameter("y", "integer", "The y-coordinate to move the mouse to.")
                ]
            ),
            Tool(
                "click_mouse",
                "Clicks a mouse button.",
                [
                    ToolParameter("button", "string", "The mouse button to click ('left', 'right', or 'middle'). Optional, defaults to 'left'.")
                ]
            ),
            Tool(
                "stop_game",
                "Stops the game. Should be used when there is no action left to take.",
                []
            )
        ]

    def to_continue_flying(self):
        return self.continue_flying
           
    def stop_flying(self):
        self.continue_flying = False

        LOGGER.debug(f"Stopping flight.")

        return {
            "type": "tool_result",
            "content": "stopped flying."
        }
        

    def execute_tools(self):
        tool_map = {
            "take_screenshot": interface.take_screenshot,
            "press_key": interface.press_key,
            "hold_key": interface.hold_key,
            "move_mouse": interface.move_mouse,
            "click_mouse": interface.click_mouse,
            "stop_game": self.stop_flying
        }

        for tool in self.next_toolset:
            tool_name = tool.name
            parameters = tool.input
            tooluse_id = tool.id
            LOGGER.info(f"Executing tool {tooluse_id}: {tool_name} with parameters: {parameters}")
            
            if tool_name not in tool_map:
                self.next_toolset = []
                raise ValueError(f"Tool '{tool_name}' not found.")

            tool_res = tool_map[tool_name](**parameters)
            return_schema = {
                "type": tool_res["type"], 
                "tool_use_id": tooluse_id, 
                "content": tool_res["content"]
            }
            self.toolset_results.append(return_schema)
            
        self.next_toolset = []    
        LOGGER.debug(f"Toolset results: {self.toolset_results}")
        return self.toolset_results
    
    def get_tool_descriptions(self):
        return [tool.to_dict() for tool in self.tools]

    def send_prompt_to_claude(self, prompt):
        """
        Sends the given prompt as input to Claude and returns the response.

        Sets the next set of tools to execute on the instance
        Resets the results from the last tools execution

        :param prompt: The prompt to send to Claude.
        :return: The response from Claude.
        """

        new_message = { "role": "user", "content": prompt }
        LOGGER.debug(f"Sending prompt to cache: {new_message}")
        self.conversation_cache.add_message(new_message)
        previous_messages = self.conversation_cache.get_messages()

        LOGGER.info(f"Prompting claude with messages: {previous_messages}")

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=1024,
            system=
                """
                You are a pilot in the French Airforce in the game War Thunder. You have an array of aircraft at your disposal, 
                from the Mirage F1 to the Mirage 2000and even the Mirage 4000. You are given the tools needed to fly the aircraft. 
                Your responsibility is to complete the missionobjective, which is to eleminate enemies. Enemies are marked by red markers 
                and names while allies are marked in blue. You will fly until the mission is over at which point you will stop.
                """,
            messages=previous_messages,
            tool_choice={"type": "any"},
            tools=self.get_tool_descriptions()
        )

        LOGGER.debug(f"Claude Response: {response}")

        response_as_msg_dict = {"role": response.role, "content": response.content}
        self.conversation_cache.add_message(response_as_msg_dict)
        LOGGER.info(f"Adding claude response to message cache: {response_as_msg_dict}")

        self.next_toolset = response.content
        return self.next_toolset
    
    def clear_results(self):
        self.toolset_results = []
    
def fetchModels():
    client = anthropic.Anthropic()
    all_models = client.models.list(limit=20)
    
    sonnet = next((model for model in all_models.data if "sonnet" in model.id.lower()), None)
    haiku = next((model for model in all_models.data if "haiku" in model.id.lower()), None)
    opus = next((model for model in all_models.data if "opus" in model.id.lower()), None)
    
    if not all([sonnet, haiku, opus]):
        missing = []
        if not sonnet: missing.append("Sonnet")
        if not haiku: missing.append("Haiku")
        if not opus: missing.append("Opus")
        raise ValueError(f"Could not find models: {', '.join(missing)}")
    
    return (sonnet, haiku, opus)
