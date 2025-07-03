from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import uuid4

app = FastAPI(
    title="Tic Tac Toe API",
    description="Backend API for managing Tic Tac Toe games, moves, and history (MVP - in-memory storage).",
    version="0.1.0",
    openapi_tags=[
        {"name": "Games", "description": "Endpoints for creating and playing games"},
        {"name": "History", "description": "Endpoints for viewing game history"},
        {"name": "Health", "description": "Service health check"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models and Storage ----------

class StartGameRequest(BaseModel):
    player_x: str = Field(..., description="Name or identifier of player X")
    player_o: Optional[str] = Field(None, description="Name or identifier of player O (optional for single player)")

class GameState(BaseModel):
    game_id: str
    board: List[List[str]]
    next_player: str
    winner: Optional[str]
    game_over: bool

class MoveRequest(BaseModel):
    player: str = Field(..., description="Player making the move, 'X' or 'O'")
    row: int = Field(..., ge=0, le=2, description="Row index (0-2)")
    col: int = Field(..., ge=0, le=2, description="Column index (0-2)")

class GameHistoryEntry(BaseModel):
    game_id: str
    player_x: str
    player_o: str
    winner: Optional[str]
    game_over: bool

# Simple in-memory storage for MVP
games: Dict[str, Dict] = {}  # game_id -> dict with board, next_player, winner, over, player_x, player_o
game_history: List[GameHistoryEntry] = []

# ---------- Game Logic ----------

def create_new_board():
    return [["" for _ in range(3)] for _ in range(3)]

def check_winner(board) -> Optional[str]:
    """Returns 'X', 'O' if there is a winner, or None."""
    lines = []
    # Rows and columns
    for i in range(3):
        lines.append(board[i])  # rows
        lines.append([board[0][i], board[1][i], board[2][i]])  # cols
    # Diagonals
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])
    for line in lines:
        if line[0] and all(cell == line[0] for cell in line):
            return line[0]
    return None

def board_is_full(board) -> bool:
    return all(cell for row in board for cell in row)

def get_next_player(current: str) -> str:
    return 'O' if current == 'X' else 'X'

def game_to_state(game_id: str, game: dict) -> GameState:
    return GameState(
        game_id=game_id,
        board=game["board"],
        next_player=game["next_player"],
        winner=game["winner"],
        game_over=game["over"]
    )

# ---------- API Routes ----------

# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health check for the backend API")
def health_check():
    """Simple health check endpoint."""
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.post("/games", response_model=GameState, tags=["Games"], status_code=status.HTTP_201_CREATED, summary="Create a new Tic Tac Toe game")
def create_game(req: StartGameRequest):
    """
    Create a new Tic Tac Toe game session.
    - **player_x**: Name or ID for 'X'
    - **player_o**: Name or ID for 'O' (optional, can be empty for single device play)
    Returns game state including assigned game_id.
    """
    game_id = str(uuid4())
    board = create_new_board()
    game = {
        "board": board,
        "next_player": "X",
        "winner": None,
        "over": False,
        "player_x": req.player_x,
        "player_o": req.player_o or "",
    }
    games[game_id] = game
    return game_to_state(game_id, game)

# PUBLIC_INTERFACE
@app.post("/games/{game_id}/move", response_model=GameState, tags=["Games"], summary="Submit a move to an existing game")
def make_move(game_id: str, move: MoveRequest):
    """
    Submit a player's move for an existing game.
    - **player**: 'X' or 'O'
    - **row**, **col**: indices (0..2)
    Validates move, updates game, checks for win/draw, and returns updated state.
    """
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    game = games[game_id]
    if game["over"]:
        raise HTTPException(status_code=400, detail="Game is already over")
    if move.player != game["next_player"]:
        raise HTTPException(status_code=400, detail=f"It is not {move.player}'s turn")
    if not (0 <= move.row < 3 and 0 <= move.col < 3):
        raise HTTPException(status_code=400, detail="Invalid board coordinates")
    if game["board"][move.row][move.col]:
        raise HTTPException(status_code=400, detail="Cell already occupied")

    # Apply move
    game["board"][move.row][move.col] = move.player

    winner = check_winner(game["board"])
    game["winner"] = winner
    if winner or board_is_full(game["board"]):
        game["over"] = True
        # Add to game history only if not already present
        existing = any(entry.game_id == game_id for entry in game_history)
        if not existing:
            game_history.append(GameHistoryEntry(
                game_id=game_id,
                player_x=game["player_x"],
                player_o=game["player_o"],
                winner=winner,
                game_over=True
            ))
    if not game["over"]:
        game["next_player"] = get_next_player(move.player)

    return game_to_state(game_id, game)

# PUBLIC_INTERFACE
@app.get("/games/{game_id}", response_model=GameState, tags=["Games"], summary="Get game state")
def get_game_state(game_id: str):
    """
    Retrieve the current state of the specified game, including the board, whose turn it is, and any winner.
    """
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    game = games[game_id]
    return game_to_state(game_id, game)

# PUBLIC_INTERFACE
@app.get("/games/history", response_model=List[GameHistoryEntry], tags=["History"], summary="Fetch history of finished games (MVP)")
def get_game_history():
    """
    Returns a list of completed game sessions with their outcomes.
    """
    return game_history
