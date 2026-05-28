⚔️ Wumpus World AI Game

An advanced AI-powered implementation of the classic Wumpus World environment built using Python and Pygame.

This project combines:

🎮 Interactive Game Design
🧠 Artificial Intelligence
🔍 Knowledge-Based Reasoning
🤖 Autonomous AI Agent
📊 Probabilistic Inference
🎨 Modern Visual Effects
🔊 Procedural Sound Synthesis

The game features both manual gameplay and an intelligent AI Solver Agent capable of navigating the dangerous cave using logical reasoning and probabilistic decision-making.

🌟 Features
Fully playable Wumpus World game
AI-powered autonomous agent
Knowledge Base reasoning system
Probabilistic danger estimation
BFS pathfinding
Intelligent arrow shooting
Dynamic world generation
Animated particle effects
Procedural sound generation
Modern glowing UI
Fog-of-war system
Heatmap danger visualization
Real-time AI path highlighting
Score tracking system
🧠 AI Concepts Used
1. Knowledge-Based Agent

The AI agent stores observations and infers safe/dangerous locations.

The agent reasons using:

Breeze detection
Stench detection
Safe cell inference
Frontier exploration
Risk estimation
AI Processing Cycle
Observe → Infer → Plan → Act
2. Probabilistic Reasoning

The AI calculates danger probabilities for unknown cells.

Pit Probability

The probability increases when nearby visited cells contain breezes.

Wumpus Probability

The probability increases when nearby visited cells contain stenches.

This allows the AI to:

Estimate risks
Choose safer paths
Avoid dangerous exploration
3. Breadth-First Search (BFS)

BFS is used for:

Safe pathfinding
Navigation planning
Finding nearest safe cells

The AI computes optimal movement paths dynamically.

4. Autonomous Decision Making

The AI agent can:

Explore the cave automatically
Detect possible Wumpus location
Shoot arrows intelligently
Collect gold
Escape safely
🎮 Gameplay

The player explores a dangerous cave searching for gold while avoiding:

🕳️ Pits
👹 Wumpus monster

The cave provides clues:

Clue	Meaning
💨 Breeze	Pit nearby
🦨 Stench	Wumpus nearby

The objective is:

Find the gold
Survive the cave
Escape through the start cell
🏗️ Project Structure
├── wumpus.py
📂 Main Components
KnowledgeBase

Handles:

Environment observations
Logical inference
Safe cell detection
Danger estimation
AI planning
Stored Information
- Visited cells
- Safe cells
- Breeze locations
- Stench locations
- Pit probabilities
- Wumpus probabilities
ParticleSystem

Creates visual effects:

Explosions
Glow effects
Gold collection particles
Death animations
World Generation

The cave world is generated randomly:

Wumpus placement
Pit placement
Gold placement
Clue propagation
AI Solver

The AI can play automatically using:

Knowledge inference
BFS navigation
Risk analysis
Goal planning

Toggle AI using:

TAB
🎨 Graphics & UI

The game includes:

Animated glowing effects
Dynamic fog-of-war
Heatmap danger visualization
Animated breeze & stench effects
Smooth player movement
Endgame overlays
Interactive side panel
🔊 Audio System

The game generates procedural sound effects dynamically using pure Python.

No external audio files are required.

Generated sounds include:

Movement
Gold collection
Arrow shooting
Danger alerts
Victory sounds
Death sounds
🕹️ Controls
Key	Action
WASD / Arrow Keys	Move
G	Grab Gold
E	Escape Cave
F + Arrow Key	Shoot Arrow
TAB	Toggle AI Solver
R	Restart Game
ESC	Return to Menu
📊 Game Mechanics
Scoring System
Action	Score
Step movement	-1
Shoot arrow	-10
Kill Wumpus	+500
Collect Gold	+1000
Escape with Gold	+500
Death	-1000
🧠 AI Knowledge Representation

The AI maintains:

Safe Cells
Dangerous Cells
Frontier Cells
Pit Probabilities
Wumpus Probabilities
Visited States

This allows intelligent exploration and survival planning.

🔄 AI Decision Workflow
Observe Environment
        ↓
Update Knowledge Base
        ↓
Infer Safe/Dangerous Cells
        ↓
Find Best Path (BFS)
        ↓
Take Action
🚀 Installation
1. Clone Repository
git clone https://github.com/your-username/wumpus-world-ai.git
cd wumpus-world-ai
2. Install Dependencies
pip install pygame
3. Run the Game
python wumpus.py
🌟 Technologies Used
Python
Pygame
Artificial Intelligence
Breadth-First Search (BFS)
Knowledge-Based Systems
Procedural Audio Synthesis
Probability-Based Inference
🎯 Learning Outcomes

This project demonstrates concepts from:

Artificial Intelligence
Intelligent Agents
Search Algorithms
Knowledge Representation
Game Development
Human-Computer Interaction
Procedural Generation
🔥 Advanced Features
Fog of War

Unknown cells remain hidden until explored.

Heatmap Visualization

Danger probabilities are visualized using colored overlays.

Intelligent Wumpus Detection

The AI can infer the exact Wumpus location using stench patterns.

Smooth Animation System

Player movement and effects are animated smoothly for better gameplay experience.

📸 Gameplay Preview
Cave Exploration
🟦 Player explores unknown cave
💨 Breeze warns about pits
🦨 Stench warns about Wumpus
✨ Gold must be collected
AI Solver
AI observes clues
↓
Infers safe cells
↓
Calculates risks
↓
Navigates safely
↓
Finds gold & escapes
⚠️ Requirements
Python 3.9+
Pygame
🔮 Future Improvements
Multiplayer support
Reinforcement Learning AI
Minimax-based Wumpus hunting
Procedural dungeon expansion
Difficulty modes
Save/Load system
Mobile version
Neural-network-based agent
3D graphics version
👨‍💻 Author

Developed by Devansh Varma
