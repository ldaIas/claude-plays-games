import argparse
import ai_integration.claude_client
import game_interface.game_interface

def main():
    model_input_choices = [
        ['0', "dev", "claude-3.5-haiku"],
        ['1', "stable", "claude-3.5-sonnet"],
        ['2', "prod", "claude-3-opus"]
    ]
    model_choices_flat = [opt for choice_series in model_input_choices for opt in choice_series]
    parser = argparse.ArgumentParser(description='Run the game with a specified model.')
    parser.add_argument('-m', '--model', type=str, choices=model_choices_flat, help='Model to use (0: dev, 1: stable, 2: prod)')
    args = parser.parse_args()

    input_model = args.model
    # if input_model is None:
    #     while True:
    #         input_model = input("Select model (0: dev, 1: stable, 2: prod): ")
    #         if input_model in [model_opt for model_opt in model_input_choices]:
    #             break
    #         else:
    #             print(f"Invalid model selection: {input_model}")

    models = {
       # Claude 3.5 Haiku aliases
       "claude-3.5-haiku": {
           "aliases": ["dev", "0"],
           "model_name": "claude-3.5-haiku"
       },
       
       # Claude 3.5 Sonnet aliases
       "claude-3-5-sonnet": {
           "aliases": ["stable", "1"],
           "model_name": "claude-3-5-sonnet-20241022"
       },
       
       # Claude 3 Opus aliases
       "claude-3-opus": {
           "aliases": ["prod", "2"],
           "model_name": "claude-3-opus"
       }
   }
   
    # Create a reverse lookup dictionary for easier access
    model_lookup = {}
    for model_key, info in models.items():
       model_lookup[model_key] = info["model_name"]
       for alias in info["aliases"]:
           model_lookup[alias] = info["model_name"]
    
    print(f"input model: {input_model}")
    print(f"model lookup: {model_lookup}")
    selected_model = model_lookup.get(input_model)
    print(f"selected model: {selected_model}")
    ai_client = ai_integration.claude_client.ClaudeClient(selected_model)

    print(f"Client model: {ai_client.model}")


if __name__ == "__main__":
    main()
