from pydantic import BaseModel, Field
from typing import List, Optional

# PUBLIC_INTERFACE
class StartGameRequest(BaseModel):
    player_x: str = Field(..., description="Name or identifier of player X")
    player_o: Optional[str] = Field(None, description="Name or identifier of player O (optional for single player)")

# PUBLIC_INTERFACE
class GameState(BaseModel):
    game_id: str
    board: List[List[str]]
    next_player: str
    winner: Optional[str]
    game_over: bool

# PUBLIC_INTERFACE
class MoveRequest(BaseModel):
    player: str = Field(..., description="Player making the move, 'X' or 'O'")
    row: int = Field(..., ge=0, le=2, description="Row index (0-2)")
    col: int = Field(..., ge=0, le=2, description="Column index (0-2)")

# PUBLIC_INTERFACE
class GameHistoryEntry(BaseModel):
    game_id: str
    player_x: str
    player_o: str
    winner: Optional[str]
    game_over: bool
