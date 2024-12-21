## Purpose
We are building an application that uses the Claude tools/computer use APIs to play the game War Thunder.
This application will be made of the following components:
- The AI Integration Layer
    - Handles the calls to the claude api
    - Defines the tools claude can use
    - provides our domain api
- The user input layer
    - Where the user (me and you) can interact with the application
    - This will be a terminal/console interface
- The Game Interface
    - The API between the claude responses and War Thunder
    - Takes screenshots of the game and sends the info to claude
    - Interprets claude's responses and performs actions in game

NOTE: Claude will provide the tools to use, but we must provide the actual functionality. For example, if we have the tool `get_metrics`, then claude
will tell use to use this tool, but we must in the Game Layer take a screenshot of the vehicle's metrics and send it back.

We will be trying to allow claude to fly a jet aircraft in War Thunder as if it had access to a joystick controller.

For more info on claude tool use see:
https://docs.anthropic.com/en/docs/build-with-claude/tool-use

## Task
Our task is to design, develop, and publish this application. We should use good practice and
well defined design patterns to develop the APIs.