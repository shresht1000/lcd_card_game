from machine import ADC, Pin
import time
import random
import lcd

# LCD setup
lcd.Init()

# --- Color Scheme Selection ---
# Initial temporary colors for the selection screen
Green = lcd.RGB(0, 0, 255)  # Default for background, will be overridden
Sky = Green
Red = lcd.RGB(255, 255, 255)  # Default for text, will be overridden
Yellow = lcd.RGB(0, 255, 255) # Default for highlights, will be overridden

used_cards = set()

# Constants
NUM_CARDS = 5 # Maximum cards for player and bot hands
CARD_WIDTH = 50
CARD_HEIGHT = 70
CARD_START_X = 50
CARD_Y = 150

# Inputs
adc_x = ADC(0)  # GP26 ADC0 for joystick X-axis
adc_y = ADC(1)  # GP27 ADC1 for joystick Y-axis (not used here but reserved)
btn_select = Pin(15, Pin.IN, Pin.PULL_UP)  # Select card
btn_drop = Pin(14, Pin.IN, Pin.PULL_UP)    # Drop card

# Game state variables
Hand = []
Value = []
Suit = []

botHand = []
botValue = []
botSuit = []

selected = []
game_over = False
# last_player_drop is no longer strictly needed as a global for display purposes,
# but it could be kept if you intend to show it differently.

# Movement delay to avoid too fast selection moves
MOVE_DELAY = 300
JOYSTICK_THRESHOLD = 20000

# --- Color Scheme Functions ---
def choose_color_scheme():
    """Presents options for color schemes and waits for user input."""
    lcd.Clear(lcd.RGB(0,0,0))  # clear screen to black
    lcd.Text2("Choose Color Scheme:", 60, 50, lcd.RGB(255,255,255), lcd.RGB(0,0,0))
    lcd.Text2("A: Classic", 30, 100, lcd.RGB(255,255,255), lcd.RGB(0,0,0))
    lcd.Text2("B: Camera Friendly", 10, 130, lcd.RGB(255,255,255), lcd.RGB(0,0,0))
    lcd.Text2("Left (A), Right (B)", 20, 180, lcd.RGB(255,255,255), lcd.RGB(0,0,0))
    
    while True:
        if btn_select.value() == 0:  # btn_select = Pin 15 (Left button for Classic)
            time.sleep(0.3)  # debounce
            return 'classic'
        if btn_drop.value() == 0:    # btn_drop = Pin 14 (Right button for Camera Friendly)
            time.sleep(0.3)  # debounce
            return 'camera'

def set_colors(scheme):
    """Sets global color variables based on the chosen scheme."""
    global Green, Sky, Red, Yellow
    if scheme == 'classic':
        Green = lcd.RGB(0,  165, 0)   # Classic Green (darker)
        Sky = Green                   # Sky matches Green for card backgrounds
        Red = lcd.RGB(255, 0, 0)      # Classic Red for text
        Yellow = lcd.RGB(255, 255, 0) # Classic Yellow for highlights
    else:  # camera-friendly
        Green = lcd.RGB(0, 0, 255)    # Bright Blue background
        Sky = Green                   # Sky matches Green for card backgrounds
        Red = lcd.RGB(255, 255, 255)  # Bright White text
        Yellow = lcd.RGB(0, 255, 255) # Bright Cyan for highlights/outline

# --- Game Initialization ---
# Call color scheme selection and setup at boot
color_scheme = choose_color_scheme()
set_colors(color_scheme)

def show_player_drop(card):
    """Displays the last card dropped by the player (currently unused)."""
    x = 240  # adjust as needed
    y = 180  # below player area
    lcd.Solid_Box(x, y, CARD_WIDTH, CARD_HEIGHT, Sky) # Clear previous card
    val = (card % 13) + 1
    suit = (card // 13) + 1
    lcd.Card(val, suit, x, y)

def ask_user_to_pickup(card):
    """
    Asks the player if they want to pick up a given card.
    Displays the card and prompts for Yes/No (Select/Drop buttons).
    Returns True if user chose to pick up, False otherwise.
    """
    val = (card % 13) + 1
    suit = (card // 13) + 1

    # Clear top area and display prompt
    lcd.Solid_Box(0, 0, 480, 80, Green)
    lcd.Text2("Bot Dropped:", 10, 5, Yellow, Green)
    lcd.Card(val, suit, 190, 5)
    lcd.Text2("Yes, No)", 10, 50, Red, Green)

    while True:
        if btn_select.value() == 0:  # GP15 = Yes
            time.sleep(0.3)
            return True
        if btn_drop.value() == 0:    # GP14 = No
            time.sleep(0.3)
            return False

def draw_unique_card():
    """Draws a random card that has not been used yet."""
    while True:
        c = random.randrange(52)
        if c not in used_cards:
            used_cards.add(c)
            return c
        
def shuffle(lst):
    """Shuffles a list using Fisher-Yates algorithm (currently unused)."""
    for i in range(len(lst) - 1, 0, -1):
        j = random.getrandbits(8) % (i + 1)
        lst[i], lst[j] = lst[j], lst[i]

def get_shuffled_cards(num=NUM_CARDS):
    """Returns a list of unique cards up to 'num'."""
    cards = []
    while len(cards) < num:
        c = random.randrange(52)
        if c not in used_cards:
            cards.append(c)
            used_cards.add(c)
    return cards

def init_hand():
    """Initializes the player's hand with NUM_CARDS unique cards."""
    global Hand, Value, Suit
    Hand = get_shuffled_cards()
    Value = [(c % 13) + 1 for c in Hand]
    Suit = [(c // 13) + 1 for c in Hand]

def init_bot():
    """Initializes the bot's hand with NUM_CARDS unique cards."""
    global botHand, botValue, botSuit
    botHand = get_shuffled_cards()
    botValue = [(c % 13) + 1 for c in botHand]
    botSuit = [(c // 13) + 1 for c in botHand]

# --- Drawing Functions ---
def draw_card(index):
    """Draws a single card from the player's hand at a given index."""
    x = CARD_START_X + index * CARD_WIDTH
    lcd.Card(Value[index], Suit[index], x, CARD_Y)

def draw_all_cards():
    """Clears the player's hand area and redraws all cards, including selected outlines."""
    lcd.Solid_Box(0, CARD_Y - 5, 480, CARD_Y + CARD_HEIGHT + 10, Green) # Clear area
    for i in range(len(Hand)):
        draw_card(i)
    # Draw outlines for selected cards
    for idx in selected:
        draw_outline(idx, Yellow)

def draw_outline(index, color=Yellow):
    """Draws a colored outline around a card at a given index."""
    x = CARD_START_X + index * CARD_WIDTH
    y = CARD_Y
    thickness = 4
    for t in range(thickness):
        lcd.Line(x - 2 - t, y - 2 - t, x + CARD_WIDTH + 2 + t, y - 2 - t, color)         # top
        lcd.Line(x - 2 - t, y + CARD_HEIGHT + 2 + t, x + CARD_WIDTH + 2 + t, y + CARD_HEIGHT + 2 + t, color)  # bottom
        lcd.Line(x - 2 - t, y - 2 - t, x - 2 - t, y + CARD_HEIGHT + 2 + t, color)           # left
        lcd.Line(x + CARD_WIDTH + 2 + t, y - 2 - t, x + CARD_WIDTH  + t, y + CARD_HEIGHT + 2 + t, color)  # right

def clear_outline(index):
    """Clears the outline around a card at a given index by redrawing with background color."""
    x = CARD_START_X + index * CARD_WIDTH
    y = CARD_Y
    thickness = 4
    for t in range(thickness):
        lcd.Line(x - 2 - t, y - 2 - t, x + CARD_WIDTH + 2 + t, y - 2 - t, Green)         # top
        lcd.Line(x - 2 - t, y + CARD_HEIGHT + 2 + t, x + CARD_WIDTH + 2 + t, y + CARD_HEIGHT + 2 + t, Green)  # bottom
        lcd.Line(x - 2 - t, y - 2 - t, x - 2 - t, y + CARD_HEIGHT + 2 + t, Green)           # left
        lcd.Line(x + CARD_WIDTH + 2 + t, y - 2 - t, x + CARD_WIDTH  + t, y + CARD_HEIGHT + 2 + t, Green)  # right
    
    draw_card(index) # Redraw the card to ensure it's clean

# --- Game Logic Checks ---
def is_full_sequence(selected_indices, Value, Suit, hand_len):
    """
    Checks if the selected cards form a full consecutive sequence
    of all cards in hand (e.g., for "declare" conditions).
    """
    if len(selected_indices) != hand_len:
        return False

    selected_values = [Value[i] for i in selected_indices]
    selected_values.sort()
    # Check if consecutive ascending sequence
    for i in range(len(selected_values) - 1):
        if selected_values[i] + 1 != selected_values[i + 1]:
            return False
    return True

def is_same_suit_sequence(selected_indices, Value, Suit):
    """
    Checks if selected cards contain at least one group of 3 or more
    cards of the same suit in consecutive sequence.
    """
    if len(selected_indices) < 3:
        return False

    # Group selected cards by suit
    suit_groups = {}
    for i in selected_indices:
        s = Suit[i]
        suit_groups.setdefault(s, []).append(Value[i])

    # Check if any suit group has 3 or more cards in consecutive sequence
    for s, vals in suit_groups.items():
        if len(vals) < 3:
            continue
        vals.sort()
        consecutive = True
        for i in range(len(vals) - 1):
            if vals[i] + 1 != vals[i + 1]:
                consecutive = False
                break
        if consecutive:
            return True
    return False

def drop_cards(indices):
    """
    Removes cards at given indices from the player's hand.
    Does NOT replace them. Returns the first card dropped (for bot pickup logic).
    """
    global Hand, Value, Suit
    dropped_player_card = None
    # Sort indices in reverse to avoid issues when popping elements
    for idx in sorted(indices, reverse=True):
        clear_outline(idx)
        card_to_discard = Hand[idx]
        if dropped_player_card is None: # Store one of the dropped cards for bot consideration
            dropped_player_card = card_to_discard
        used_cards.discard(card_to_discard)  # remove old card from used set
        Hand.pop(idx)
        Value.pop(idx)
        Suit.pop(idx)
    return dropped_player_card # Return one of the dropped cards

def bot_turn(player_dropped_card=None):
    """
    Manages the bot's turn: decides whether to pick up player's card,
    declare, or drop cards.
    Returns ("action_type", dropped_card_by_bot_if_any)
    """
    global botHand, botValue, botSuit

    # 1. Bot picks up player's dropped card if it exists and its value is low (e.g., < 7)
    if player_dropped_card is not None:
        val = (player_dropped_card % 13) + 1
        if val < 7: # Bot strategy: pick up low cards
            botHand.append(player_dropped_card)
            botValue.append(val)
            botSuit.append((player_dropped_card // 13) + 1)
            # If bot picked up a card, it doesn't drop one this turn (for player to pick up)
            return "picked_up_player_card", None

    # 2. Bot declares if its total value is low enough
    if sum(botValue) <= 7: # Bot strategy: declare if hand value is low
        return "declare", None

    dropped_card_by_bot = None
    # Bot strategy: sometimes drops a pair, sometimes just one card
    drop_count = 2 if random.random() < 0.5 else 1 # 50% chance to try to drop a pair

    if drop_count == 2:
        found_pair = False
        # Try to find a pair to drop
        for i in range(len(botValue)):
            for j in range(i + 1, len(botValue)):
                if botValue[i] == botValue[j]:
                    i1, i2 = sorted([i, j]) # Ensure correct order for popping
                    dropped_card_by_bot = botHand[i1] # The card to be checked for player pickup
                    # Remove pair
                    for idx in [i2, i1]: # Pop higher index first to avoid index shift issues
                        used_cards.discard(botHand[idx]) # Card leaves bot's hand, available for player
                        botHand.pop(idx)
                        botValue.pop(idx)
                        botSuit.pop(idx)
                    # Add new cards to bot's hand
                    for _ in range(2):
                        new = draw_unique_card()
                        botHand.append(new)
                        botValue.append((new % 13) + 1)
                        botSuit.append((new // 13) + 1)
                    found_pair = True
                    break
            if found_pair:
                break
        if not found_pair: # If no pair found, revert to dropping one card
            drop_count = 1

    if drop_count == 1:
        # Bot strategy: drop the highest value card
        max_idx = botValue.index(max(botValue))
        dropped_card_by_bot = botHand[max_idx]
        used_cards.discard(dropped_card_by_bot) # Card leaves bot's hand, available for player
        botHand.pop(max_idx)
        botValue.pop(max_idx)
        botSuit.pop(max_idx)
        # Add new card to bot's hand
        new = draw_unique_card()
        botHand.append(new)
        botValue.append((new % 13) + 1)
        botSuit.append((new // 13) + 1)

    return "dropped_card", dropped_card_by_bot

def check_declare():
    """
    Calculates and displays game results (player vs. bot total value)
    and waits for replay input.
    """
    user_total = sum(Value)
    bot_total = sum(botValue)
    
    lcd.Clear(Green)
    lcd.Text2("Game Over!", 140, 100, Red, Green)
    lcd.Text2("Your Total: {}".format(user_total), 120, 150, Yellow, Green)
    lcd.Text2("Bot Total: {}".format(bot_total), 120, 180, Yellow, Green)

    if user_total < bot_total:
        lcd.Text2("You Win!", 160, 220, Red, Green)
    elif user_total > bot_total:
        lcd.Text2("Bot Wins!", 160, 220, Red, Green)
    else:
        lcd.Text2("It's a Tie!", 160, 220, Red, Green)

    lcd.Text2("Left+Right to retry", 5, 260, Yellow, Green)
    # Wait for both buttons pressed to replay
    while True:
        if btn_drop.value() == 0 and btn_select.value() == 0:
            time.sleep(0.5)  # debounce
            return  # exit to main loop to restart
        time.sleep(0.1)

# --- Main Game Loop ---
def main():
    """Main function to run the Declare card game."""
    global selected, Hand, Value, Suit, botHand, botValue, botSuit, game_over
    
    while True: # Outer loop for replaying the game
        used_cards.clear() # Clear used cards for a new game
        selected = []
        game_over = False
        selected_card = 0 # Index of the currently highlighted card
        last_move = 0     # Timestamp for joystick movement debounce

        init_hand() # Deal initial cards to player
        init_bot()  # Deal initial cards to bot

        lcd.Clear(Green) # Clear screen with background color
        lcd.Text2("Declare Game", 20, 10, Red, Green) # Game title
        draw_all_cards() # Draw player's initial hand
        draw_outline(selected_card) # Highlight the first card

        select_pressed = False # Debounce flag for select button
        drop_pressed = False   # Debounce flag for drop button

        while not game_over:
            now = time.ticks_ms()
            delta = adc_x.read_u16() - 32768 # Read joystick X-axis

            # --- Player Input Handling ---
            # Move selection with joystick
            if time.ticks_diff(now, last_move) > MOVE_DELAY:
                if delta > JOYSTICK_THRESHOLD and selected_card < len(Hand) - 1:
                    clear_outline(selected_card)
                    selected_card += 1
                    draw_outline(selected_card)
                    last_move = now
                elif delta < -JOYSTICK_THRESHOLD and selected_card > 0:
                    clear_outline(selected_card)
                    selected_card -= 1
                    draw_outline(selected_card)
                    last_move = now

            # Declare (both buttons pressed simultaneously)
            if btn_drop.value() == 0 and btn_select.value() == 0:
                game_over = True
                check_declare()
                break # Exit inner game loop to restart outer loop

            # Select card
            if btn_select.value() == 0 and not select_pressed:
                select_pressed = True
                if selected_card in selected:
                    selected.remove(selected_card) # Deselect if already selected
                else:
                    # Allow selecting up to NUM_CARDS, even if hand temporarily grows.
                    # The logic below will ensure hand size returns to NUM_CARDS.
                    if len(selected) < NUM_CARDS: 
                        selected.append(selected_card) # Select card
                draw_all_cards() # Redraw to show/hide selection outline
                draw_outline(selected_card) # Re-draw outline on current card

            elif btn_select.value() == 1:
                select_pressed = False # Reset debounce

            # Drop cards
            if btn_drop.value() == 0 and not drop_pressed:
                drop_pressed = True
                
                # Determine cards to be dropped and store one for bot consideration
                cards_to_drop_indices = []
                player_dropped_card_for_bot = None
                num_dropped_by_player = 0

                if len(selected) == 0: # Drop currently highlighted single card
                    cards_to_drop_indices = [selected_card]
                elif len(selected) == 1: # Drop single selected card
                    cards_to_drop_indices = selected
                elif len(selected) == 2: # Attempt to drop a pair
                    i1, i2 = sorted(selected)
                    if Value[i1] == Value[i2]: # Check if they are a pair
                        cards_to_drop_indices = selected
                    else: # Not a valid pair, so drop only the first selected card
                        cards_to_drop_indices = [selected[0]]
                else: # Attempt to drop a sequence (3+ cards)
                    # Check if selected cards form a valid sequence
                    if is_full_sequence(selected, Value, Suit, len(Hand)) or is_same_suit_sequence(selected, Value, Suit):
                        cards_to_drop_indices = selected
                    else: # If not a valid sequence, drop only the first selected card
                        cards_to_drop_indices = [selected[0]]

                # Actually remove cards from player's hand
                # drop_cards will handle clearing outlines and removing from used_cards
                # It returns ONE of the dropped cards for the bot's consideration.
                player_dropped_card_for_bot = drop_cards(cards_to_drop_indices)
                num_dropped_by_player = len(cards_to_drop_indices)

                # Player's hand now has (NUM_CARDS - num_dropped_by_player) cards.
                # Now it's the bot's turn.
                bot_action, dropped_card_by_bot = bot_turn(player_dropped_card_for_bot)
                
                if bot_action == "declare":
                    game_over = True
                    check_declare()
                    break # Exit inner game loop

                # Handle player's hand replenishment
                cards_replenished = 0
                if dropped_card_by_bot and ask_user_to_pickup(dropped_card_by_bot):
                    # Player chose to pick up bot's card
                    Hand.append(dropped_card_by_bot)
                    Value.append((dropped_card_by_bot % 13) + 1)
                    Suit.append((dropped_card_by_bot // 13) + 1)
                    cards_replenished += 1
                else:
                # Draw unique cards to fill remaining slots, if any
                    
                    new = draw_unique_card()
                    Hand.append(new)
                    Value.append((new % 13) + 1)
                    Suit.append((new // 13) + 1)
                    cards_replenished += 1

                # Re-draw hand and reset selection for player's next turn
                selected = [] # Clear selected list
                draw_all_cards()
                selected_card = 0 # Reset selection to first card
                draw_outline(selected_card) # Draw outline on the new first card
                
                # Clear the "Bot Dropped" message from the top of the screen
                lcd.Solid_Box(0, 0, 480, 80, Green)
                lcd.Text2("Declare Game", 20, 10, Red, Green) # Restore game title

            elif btn_drop.value() == 1:
                drop_pressed = False # Reset debounce

            time.sleep(0.01) # Small delay to prevent busy-waiting


