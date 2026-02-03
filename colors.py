#!/bin/python3
"""
Methods for setting text output color. Can change the text color or effect,
like bold, blinking, or reversed.
"""

def set_color(color: str):
    """
    sets the text color/effect for stdout text to the given color.
    The list of accepted strings is limited. I.E. 'maroon' or 'violet' will
    NOT work, but 'black' or 'purple' will.
    :param color: A string representing the color or effect to set. Not
    case-sensitive. Must contain only one color/effect. No leading or trailing
    spaces. No hyphens or underscores.
    """
    color = color.lower()
    if color == "black":
        print("\033[30m", end='')
    elif color == "red":
        print("\033[31m", end='')
    elif color == "green":
        print("\033[32m", end='')
    elif color == "brown":
        print("\033[33m", end='')
    elif color == "blue":
        print("\033[34m", end='')
    elif color == "purple":
        print("\033[35m", end='')
    elif color == "cyan":
        print("\033[36m", end='')
    elif color == "light grey" or color == "light gray":
        print("\033[37m", end='')
    elif (color == "dark grey" or color == "dark gray"
          or color == "grey" or color == "gray"):
        print("\033[1;30m", end='')
    elif color == "light red":
        print("\033[1;31m", end='')
    elif color == "light green":
        print("\033[1;32m", end='')
    elif color == "yellow":
        print("\033[1;33m", end='')
    elif color == "light blue":
        print("\033[1;34m", end='')
    elif color == "light purple":
        print("\033[1;35m", end='')
    elif color == "light cyan":
        print("\033[1;36m", end='')
    elif color == "white":
        print("\033[1;37m", end='')
    elif color == "reset" or color == "default":
        print("\033[0m", end='')
    elif color == "bold":
        print("\033[1m", end='')
    elif color == "underline":
        print("\033[4m", end='')
    elif color == "blink" or color == "blinking":
        print("\033[5m", end='')
    elif color == "reverse":
        print("\033[7m", end='')
    elif color == "italic":
        print("\033[3m", end='')
    elif color == "concealed" or color == "conceal":
        print("\033[8m", end='')
    elif color == "revealed" or color == "reveal":
        print("\033[28m", end='')

def reset_color():
    """
    Resets the text color for stdout text to the default color.
    """
    print("\033[0m", end='')
