import pytest
import os
import tempfile
from src.user_state import UserState

@pytest.fixture
def temp_state_file():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        filepath = tmp.name
    yield filepath
    os.remove(filepath)

def test_user_state_creation(temp_state_file):
    state = UserState(temp_state_file)
    assert state.state["watched"] == []
    assert state.state["ratings"] == {}

def test_user_state_mark_as(temp_state_file):
    state = UserState(temp_state_file)
    
    # Mark as my_list
    state.mark_as("Dune", "my_list")
    assert "Dune" in state.state["my_list"]
    
    # Move to watched
    state.mark_as("Dune", "watched")
    assert "Dune" in state.state["watched"]
    assert "Dune" not in state.state["my_list"] # Should be mutually exclusive

def test_user_state_rating(temp_state_file):
    state = UserState(temp_state_file)
    
    state.rate_movie("Dune", 9)
    assert state.get_rating("Dune") == 9
    
    # Invalid rating
    with pytest.raises(ValueError):
        state.rate_movie("Dune", 11)
