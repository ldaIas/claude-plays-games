import anthropic
import game_interface.game_interface
import os

class ToolParameter:
    def __init__(self, name, type, description):
        self.name = name
        self.type = type
        self.description = description

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description
        }

class Tool:
    def __init__(self, name, description, parameters):
        self.name = name
        self.description = description
        self.parameters = parameters

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }    

class ClaudeClient:
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required.")
        self.anthropic = anthropic.Anthropic(api_key=self.api_key)
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
            )
        ]
           

    def execute_tool(self, tool_name, parameters):
        print(f"Executing tool: {tool_name} with parameters: {parameters}")
        if tool_name == "take_screenshot":
            game_interface.take_screenshot(**parameters)
        elif tool_name == "press_key":
            game_interface.press_key(**parameters)
        elif tool_name == "hold_key":
            game_interface.hold_key(**parameters)
        elif tool_name == "move_mouse":
            game_interface.move_mouse(**parameters)
        elif tool_name == "click_mouse":
            game_interface.click_mouse(**parameters)
        else:
            return f"Tool '{tool_name}' not found."
        return "Tool executed successfully."
    
    def get_tool_descriptions(self):
        return [tool.to_dict.__str__ for tool in self.tools]

    def send_prompt_to_claude(self, prompt):
        
        """
        response = self.anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            tools=get_tool_descriptions(self)
        )
        return response
        """


if __name__ == "__main__":
    client = ClaudeClient()
    tool_descriptions = client.get_tool_descriptions()
    print("Available tools:")
    print(tool for tool in tool_descriptions)

    """
    prompt = "Take a screenshot of the current game view and save it as 'initial_view.png'."
    response = claude_client.send_prompt_to_claude(prompt)
    print(f"Claude's response: {response}")
    """