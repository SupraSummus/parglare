S_ATTENTION = {'fg': 'red', 'bold': True}
S_HEADER = {'fg': 'green'}
S_EMPH = {'fg': 'yellow'}


def prints(message, s={}):
    print(style(message, s))


def style_message(message, style):
    return message


def s_header(message):
    return style_message(message, S_HEADER)


def s_attention(message):
    return style_message(message, S_ATTENTION)


def s_emph(message):
    return style_message(message, S_EMPH)


def style(header, content, level=0, new_line=False, header_style=S_HEADER,
          width=120):
    if content:
        content_start = level * 8 + len(header) + 1
        content_width = width - content_start
        content = str(content)
        content = [content[start:start+content_width]
                   for start in range(0, len(content), content_width)]
        content = ('\n' + ' ' * content_start).join(content)
    new_line = "\n" if new_line else ""
    level = ("\t" * level) if level else ""
    return new_line + level + style_message(str(header), header_style) \
        + ((" " + str(content)) if content else "")


def styled_print(header, content, level=0, new_line=False,
                 header_style=S_HEADER, width=120):
    prints(style(header, content, level, new_line, header_style, width))


def h_print(header, content="", level=0, new_line=False):
    styled_print(header, content, level, new_line, S_HEADER)


def a_print(header, content="", level=0, new_line=False):
    styled_print(header, content, level, new_line, S_ATTENTION)
