from streamlit.testing.v1 import AppTest
import pytest

@pytest.fixture
def app():
    """Fixture to load the app before each test."""
    return AppTest.from_file("streamlit_app.py", default_timeout=10)

def test_app_loads_correctly(app):
    """Verify the app starts and displays the correct title."""
    app.run()
    assert not app.exception
    
    # Check for the Sidebar Title "Duty Planner"
    # st.title() in sidebar usually appears in app.title
    # Note: Streamlit tests capture titles in order.
    titles = [t.value for t in app.title]
    assert "Duty Planner" in titles

def test_grid_generation(app):
    """Simulate clicking 'Load Grid' and verify grid appears."""
    app.run()
    
    # Find the 'Load / Reset Grid' button.
    load_btns = [b for b in app.button if "Load" in b.label]
    assert len(load_btns) > 0
    
    load_btns[0].click().run()
    
    assert not app.exception
    
    # Verify GENERATE FILL button appears (indicating grid loaded)
    all_btn_labels = [b.label for b in app.button]
    assert any("GENERATE FILL" in label for label in all_btn_labels)

def test_settings_modification(app):
    """Test that changing settings in the UI persists."""
    app.run()
    
    # 1. Modify Personnel List (The textarea is in the second tab, but widgets are accessible)
    personnel_areas = [t for t in app.text_area if "Enter names" in t.label]
    if not personnel_areas:
        txt_area = app.text_area[0]
    else:
        txt_area = personnel_areas[0]

    txt_area.input("Zebra, Cobra").run()
    
    # 2. Save
    save_btns = [b for b in app.button if "Save" in b.label]
    assert len(save_btns) > 0
    save_btns[0].click().run()
    
    assert not app.exception
    
    # 3. Verify Success Message
    success_messages = [s.value for s in app.success]
    assert any("saved" in msg.lower() for msg in success_messages)
