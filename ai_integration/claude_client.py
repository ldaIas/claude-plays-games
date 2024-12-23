import threading
import anthropic
import game_interface.game_interface as interface
import os
import json
from simple_logger.logger import SimpleLogger
from ai_integration.conversation_cache import ConversationCache
from user_interface.user_interface import print_claude_response


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
                """Presses and releases a specified keyboard key or mouse button. The available keys are:
                - W - Pitch down
                - S - Pitch up
                - A - roll counter-clockwise
                - D - roll clockwise
                - Q - yaw counter clockwise
                - E - yaw clockwise
                - LMB - fire main guns
                - MMB - visual lock onto target closest to cursor (this is not an AAM lock)
                - RMB - lock/fire missile. The first press engages the missile, the second press launches the missile.
                - Alt - Switches between secondary armamemnts. When used, you should always take a screenshot to determine which armament is selected.
                - Space - Drop bomb salvo
                - G - gear up/down
                - H - airbrake
                - Ctrl - Countermeasures (Flares/Chaff)
                - 9 - Switch between radar modes
                - [ - Switch between selected target on radar. Note: The radar identifies foes as targets like this: |o|
                - + - increase thrust
                - - - decrease thrust
                - M - Open map. Only stays open as long as you hold it
                """,
                [
                    ToolParameter("key", "string", "The key to press (e.g., 'w', 's', 'a', 'd', 'Space').")
                ]
            ),
            Tool(
                "hold_key",
                """\
                Holds down a specified keyboard key for a certain duration. Same parameters as `press_key`.\
                Note: Because each tool is ran in a thread, the maximum effective duration is 10 seconds. This is the timeout given to threads.
                """,
                [
                    ToolParameter("key", "string", "The key to hold down (e.g., 'w', 's')."),
                    ToolParameter("duration", "number", "The duration in seconds to hold the key down.")
                ]
            ),
            Tool(
                "move_mouse",
                """\
                Moves the mouse cursor to specific coordinates on the screen. This is relative to the center of the screen, so an input of (0,0) would keep the aircraft straight. \
                The width of the screen is 1920 pixels and the height is 1080 pixels, so the maximum and minimum values are (-960, 960) and (-540, 540) respectively.\
                An input of (960, 0) leads to a sharp 90 degree turn to the right. This does not need to be combined with keyboard input to be effective.\
                """,
                [
                    ToolParameter("x", "integer", "The x-coordinate to move the mouse to."),
                    ToolParameter("y", "integer", "The y-coordinate to move the mouse to."),
                    ToolParameter("duration", "number", "The duration over which to move the mouse. Longer durations mean more controlled turns, short durations are sharp. Optional, defaults to 0.1.")
                ]
            ),
            Tool(
                "stop_game",
                "Stops the game. Should be used when there is no action left to take in the game/mission.",
                []
            ),
            Tool(
                "no_op",
                "Does nothing. Used when no action is required, usually when the game has ended or there is nothing currently to do (you will fly straight) Explain your reasoning for using this tool when chosen.",
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
    
    def no_op(self):
        return {
            "type": "tool_result",
            "content": "no-op"
        }
        

    def execute_tools(self):
        tool_map = {
            "take_screenshot": interface.take_screenshot,
            "press_key": interface.press_key,
            "hold_key": interface.hold_key,
            "move_mouse": interface.move_mouse,
            "stop_game": self.stop_flying,
            "no_op": self.no_op
        }

        threads = []
        for tool in self.next_toolset:
            tool_name = tool['name']
            parameters = tool['input']
            tooluse_id = tool['id']
            LOGGER.info(f"Executing tool {tooluse_id}: {tool_name} with parameters: {parameters}")
            
            if tool_name not in tool_map:
                self.next_toolset = []
                return {
                    "type": "tool_result",
                    "tool_use_id": tooluse_id,
                    "content": {
                        "type": "text", 
                        "text": f"Error: Tool {tool_name} not found."
                    }
                }

            def execute_tool(tool_name, parameters, tooluse_id):
                tool_res = tool_map[tool_name](**parameters)
                LOGGER.debug(f"Tool {tool_name} result: {tool_res}")
                return_schema = {
                    "type": tool_res["type"],
                    "tool_use_id": tooluse_id,
                    "content": tool_res["content"]
                }
                self.toolset_results.append(return_schema)

            thread = threading.Thread(target=execute_tool, args=(tool_name, parameters, tooluse_id))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

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
                """\
                You are a pilot in the French Airforce in the game War Thunder. You have an array of aircraft at your disposal, \
                from the Mirage F1 to the Mirage 2000 and even the Mirage 4000. You are given the tools needed to fly the aircraft. \
                Your responsibility is to complete the mission objective, which is to eleminate enemies. Enemies are marked by red markers \
                and names while allies are marked in blue. You will fly until the mission is over at which point you will stop. \
                You will recieve images of the game and you will need to respond to them as necessary. Outline a brief description of your thoughts \
                after each image you recieve. \
                Do NOT ask for user input for your next actions or decisions. You are free to decide any course of action to complete the objective. \
                It is highly recommended to queue up a screenshot tool with other tools so that you may see the result in action. \
                Additionally, you may perform multiple actions at once.
                
                All tool requests are executed in a thread, and all threads joined before returning the result.

                Note: When engaging with any AAM, the target seeker will be white until it has a lock. Then it will turn red and will be following the target. \
                If the screen still has large and small white circles, then no target is locked by AAM. It is only when there are solid red circles around the target that we have a lock.\
                There are several radar modes. Here are some common ones along with acronyms:
                - SRC: Search mode (active radar)
                - PD: Standard Pulse Doppler, sorting by range
                - HDN: Head-on (good for incoming targets, unperformant for targets flying away)
                - TWS: Track while scan (passive radar)
                - PDV: Pulse Doppler (Velocity), sorting by velocity first
                Modes (in order):
                - SRC PD/ HDN (default)
                - TWS HDN (2nd)
                - SRC PDV HDN (3rd)
                - SRC (4th)
                - repeat
                """,
            messages=previous_messages,
            tool_choice={"type": "auto", "disable_parallel_tool_use": False},
            tools=self.get_tool_descriptions()
        )

        LOGGER.debug(f"Claude Response: {response}")

        response_as_msg_dict = {"role": response.role, "content": response.content}
        self.conversation_cache.add_message(response_as_msg_dict)
        LOGGER.info(f"Adding claude response to message cache: {response_as_msg_dict}")

        self.next_toolset = [cont.model_dump() for cont in response.content if cont.model_dump()['type'] == 'tool_use']
        self.tool_thoughts = [cont.model_dump() for cont in response.content if cont.model_dump()['type'] == 'text']
        if (len(self.tool_thoughts)) == 0:
            self.tool_thoughts = [{"text": "<no thoughts for this action>"}]
        print_claude_response(self.tool_thoughts[0]['text'])

        LOGGER.debug(f"Next toolset: {self.next_toolset}")
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
