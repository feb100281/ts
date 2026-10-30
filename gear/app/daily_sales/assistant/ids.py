# gear/app/daily_sales/assistant/ids.py
ASSISTANT_FAB_ID = "assistant-fab"
ASSISTANT_PANEL_ID = "assistant-panel"
ASSISTANT_CLOSE_BTN_ID = "assistant-close-btn"
ASSISTANT_CLEAR_BTN_ID = "assistant-clear-btn"
ASSISTANT_HISTORY_STORE_ID = "assistant-history-store"
ASSISTANT_SEEN_STORE_ID = "assistant-seen-store"
ASSISTANT_UI_STORE_ID = "assistant-ui-store"
ASSISTANT_MESSAGES_ID = "assistant-messages"
ASSISTANT_CHIPS_ID = "assistant-chips"
ASSISTANT_INPUT_ID = "assistant-input"
ASSISTANT_SEND_BTN_ID = "assistant-send-btn"


def chip_id(i: int) -> str:
    return f"assistant-chip-{i}"
