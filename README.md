# AI Agent Experiment

This project is an experimental to develop an AI chatbot that user can define a world and a list of characters, so that user can interactive with characters.

This project is also an experimental initiative to develop an AI agent. It leverages a Large Language Model (LLM) to process inputs and generate commands. These commands are then utilized by Python scripts to make API requests and execute the desired actions.

## Required Installation

### Hardware requirements
- CPU: AMD 3800X
- Memory: 64GB
- Graphic Card: NVIDIA RTX 3070 Ti

### Ollama Windows version
- Download Ollama
- `ollama pull qwen3:8b`

### Python 3.10
- `pip install requests`

## Project structure
```
.
├── models/ (optional: put downloaded models here)
├── sessions/ (store the chat sessions/history)
│   ├── 2025-01-01_demo_world_0001/
│   └── 2025-12-30_235212_demo_world_0001/
├── SimulationProjects/ (for agent mode use)
│   ├── cmd_agent/ (Java backend project to execute the command)
│   └── frontend/ (Angular freontend project to display the result)
└── worlds/ (world description for story mode)
    ├── cmd_agent/ (describe the world to be agent mode)
    |   ├── system_prompt.txt (define system output rules)
    |   └── world.json (world description)
    └── demo_world/ (a demo story world)
        └── characters/ (optional: characters in the story)
        └── system_prompt.txt (define system output rules)
        └── world.json (world description)
```

## Usage
To use the AI agent, you can run the `storyai.py` script with the desired parameters. For example:

[Documentation](https://github.com/dyzhxsl3897/ai-agent/wiki)

### To start a new session for demo_world
```
python storyai.py new demo_world
```

### To chat in the above new session
```
python storyai.py chatloop 2025-12-30_235212_demo_world_0001
```

### To quit the chat
```
/exit
```
