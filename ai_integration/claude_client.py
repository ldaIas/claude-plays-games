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

        self.current_situation = {}

        self.total_input_tokens = 0
        self.total_output_tokens = 0

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
                - Up - pan camera up
                - Down - pan camera down
                - Left - pan camera left
                - Right - pan camera right
                - LMB - select. This can be used on units, provinces, or actions in menus.
                - RMB - (With unit selected: move to location) / open diplomacy of nation clicked over
                - Space - Pause/unpase (good to do when you need info)
                - F1 - Opens country menu (tabs for court, economy, trade, military, etc). Note: When you press F1, the last open view pops up. You then press any of the following buttons. \
                If you press F1 + 1 then F1 + 2, you will actually open then close the menu. Instead you should do F1 + 1, then 2, then press F1 or Esc to close.\
                - F1 + 1 - Opens the courtly view
                - F1 + 2 - Opens the government view
                - F1 + 3 - Opens diplomacy of last interacted country. In this view, z will take you to your own country. If on your own country, z will take you to the `release subject` view.
                - F1 + 4 - Opens the economy view
                - F1 + 5 - Opens the trade view
                - F1 + 6 - Opens technology view. From here, `n` will take you to Insitutions.
                - F1 + 7 - Opens idea groups view
                - F1 + 8 - Opens missions view
                - F1 + 9 - Opens decisions and policies (where you form nations or take special decisions)
                - F1 + 0 - Opens stability and expansion.
                - F1 + , - Opens Religion
                - F1 + . - Opens Military
                - F1 + ' - Opens subjects view
                - F1 + k - opens the estates view
                - b - opens productions interface
                - b + 1 - land units
                - b + 1 + a - recruit regiments from country manpower pool
                - b + 1 + s - recruit mercanary groups
                - b + 2 - naval units
                - b + 3 - uncored territories
                - b + 4 - send missionary
                - b + 5 - autonomy of owned provinces
                - b + 6 - show provinces of different and allow conversion (for diplo/bird points)
                - b + 7 - buildings mega viewer.
                - b + 8 - development and production of owned provinces
                - b + 9 - owned states view
                - b + 9 + a - owned states
                - b + 9 + s - state edicts
                - b + 9 + d - trade company investments
                - b + 0 - diplomacy
                - b + 0 + a - improve relations. Clicking the `+` or `-` assigns or removes a diplomat from improving with the specified country group target.
                - b + 0 + s - available alliances and interact with current allies
                - b + 0 + d - influence actions. offer vassalization and interact with subjects
                - b + 0 + g - dynastic actions. Available royal marriages and throne claims
                - b + 0 + z - economy actions. Interactions with other countries like embargos or subsidies
                - F7 - Sejm view. This is where we can interact with our internal government
                - Enter - accept current pop-up. Note: Only works for diplomatic pop ups, not events or flavor (pop ups with a drawing and flavor text)
                - c - confirm action. Used when making allies, declaring wars, etc.
                - z - cancel action. Used when making allies, wars, etc.
                - Esc - closes any view open. If pressed while none open, opens menu. Esc again to close menu.
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
                Moves the mouse cursor to specific coordinates on the screen. This is relative to the top left of the screen, so an input of (0,0) would point the mouse at the top left corner. \
                The width of the screen is 1920 pixels and the height is 1080 pixels, so the maximum and minimum values are (0, 1920) and (0, 1080) respectively.\
                Note: Moving the mouse to the edge of the screen will start panning the camera in that direction. You probably shouldn't go to the screen limits when moving the mouse. \
                """,
                [
                    ToolParameter("x", "integer", "The x-coordinate to move the mouse to."),
                    ToolParameter("y", "integer", "The y-coordinate to move the mouse to."),
                    ToolParameter("duration", "number", "The duration over which to move the mouse. Optional, defaults to 0.1.")
                ]
            ),
            Tool(
                "stop_game",
                "Stops the game. Should be used when there is no action left to take in the game/mission.",
                []
            ),
            Tool(
                "no_op",
                "Does nothing. Used when no action is required, usually when the game has ended or there is nothing currently to do. Explain your reasoning for using this tool when chosen.",
                []
            )
        ]

    def to_continue_flying(self):
        return self.continue_flying
           
    def stop_game(self):
        self.continue_flying = False

        LOGGER.debug(f"Stopping game.")

        return {
            "type": "tool_result",
            "content": "stopped game."
        }
    
    def no_op(self):
        return {
            "type": "tool_result",
            "content": "no-op"
        }
    
    def updateAndGetSituation(self, input={}):
        """
        Updates the situation log as seen fit by the model.
        """
        if input != {}:
            for (k, v) in input:
                self.current_situation[k] = v

        return {
            "type": "text",
            "text": f"New situation log: {self.getSituationAsContent()}"
        }
    
    def getSituationAsContent(self):
        situation_prompt = ""
        for (key, value) in self.current_situation:
            situation_prompt += f"{key}: {value}\n"
        return situation_prompt    

    def execute_tools(self):
        tool_map = {
            "take_screenshot": interface.take_screenshot,
            "press_key": interface.press_key,
            "hold_key": interface.hold_key,
            "move_mouse": interface.move_mouse,
            "stop_game": self.stop_game,
            "no_op": self.no_op,
            "updateAndGetSituation": self.updateAndGetSituation
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

        # Add the situation log to the prompt in a new list to send up. Don't want want to cache the sit log every time
        prompt_to_send = previous_messages + [{ "role": "user", "content": [{"type": "text", "text": f"Situation log: {self.getSituationAsContent()}"}]}]        

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=1024,
            system=
                """\
                You are a grand strategist in the game Europa Univseralis IV. \
                You are taking control of the Kingdom of Poland. You must lead the country to greatness. \
                You can click around on different countries to open the diplomacy view, and from there you can form alliances and declare wars. \
                You should ensure the survival and longevity of your nation. You can build buildings and armies and forge alliances to accomplish your goals. \
                You have the agency to make all decisions; do NOT ask for input. \
                You should be methodical with your actions and analysis of screenshots. You have unlimited time so you can take your time. \
                
                Units you have control over are marked with your flag and a green marker with the unit strength.
                Ally/friendly units are marked in blue, enemy units are marked in red, and neutral units in gray.
                The game starts paused. If you press space, it will unpause and being playing.

                You are given access to a "situation log" which represents a key-value pair of information you would like to store about the situation. \
                You should use this to store info about the current game state so that you do not need to repetitively check information. \
                An example log would be: {"military": "I have about 22k units and no generals. My military tech is level 3."}
                You will then recieve info as: "Situation log: "military": "I have about 22k units and no generals. My military tech is level 3.", ... \
                When attempting to click on a country, you should try to pan the camera to get it in the center of the screen so you can just move the mouse \
                to the center and click.

                When taking screenshots, it is a good idea to do so independently of other tools and wait for the result to process. If you are working with a screenshot \
                that you don't think represents what you asked for, wait a second (no_op) before trying again. \
                """,
            messages=prompt_to_send,
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

        claude_ui_output = ""
        for thought in self.tool_thoughts:
            claude_ui_output += thought['text'] + "\n"

        # Track and print token usage
        before_input_token = self.total_input_tokens
        before_output_token = self.total_output_tokens
        model_token_input = response.usage.input_tokens
        model_token_output = response.usage.output_tokens
        self.total_input_tokens += model_token_input
        self.total_output_tokens += model_token_output
        input_tk_diff = self.total_input_tokens - before_input_token
        output_tk_diff = self.total_output_tokens - before_output_token

        claude_ui_output += f"(↑ {self.total_input_tokens} (+{input_tk_diff}) ↓ {self.total_output_tokens} (+{output_tk_diff}))"
        
        print_claude_response(claude_ui_output)

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
