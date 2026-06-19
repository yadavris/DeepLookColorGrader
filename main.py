"""
DeepLook Color Grader
Desktop overlay tool for real-time color grading analysis.

Usage:
    python main.py

Controls:
    Tab          - Cycle through detected regions
    Escape       - Deselect current region
    I            - Toggle interactive/click-through mode (overlay)
    Ctrl+Shift+I - Toggle interactive mode (global)
    Ctrl+Shift+Q - Quit application
"""

from src.app_controller import main

if __name__ == "__main__":
    main()
