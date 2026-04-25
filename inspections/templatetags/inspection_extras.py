from django import template
from django.utils.safestring import mark_safe

try:
    import arabic_reshaper
except Exception:  # pragma: no cover
    arabic_reshaper = None

try:
    from bidi.algorithm import get_display
except Exception:  # pragma: no cover
    get_display = None

register = template.Library()

_ARABIC_DIGIT_MAP = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def _shape_arabic_text(text):
    if arabic_reshaper and get_display:
        return get_display(arabic_reshaper.reshape(text))
    return text


def _wrap_text_lines(text, max_chars=38):
    paragraphs = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    wrapped_lines = []

    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            wrapped_lines.append('')
            continue

        words = stripped.split()
        current_line = []
        current_length = 0

        for word in words:
            projected_length = current_length + len(word) + (1 if current_line else 0)
            if current_line and projected_length > max_chars:
                wrapped_lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length = projected_length

        if current_line:
            wrapped_lines.append(' '.join(current_line))

    return wrapped_lines


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def arabic_pdf(value):
    if value is None:
        return ''
    text = str(value)
    if arabic_reshaper and get_display:
        try:
            normalized = text.replace('\r\n', '\n').replace('\r', '\n')
            return '\n'.join(
                _shape_arabic_text(line) if line else ''
                for line in normalized.split('\n')
            )
        except Exception:
            return text
    return text


@register.filter
def arabic_pdf_block(value):
    if value in (None, ''):
        return ''

    text = str(value)
    try:
        wrapped_lines = _wrap_text_lines(text)
        return mark_safe('<br/>'.join(
            _shape_arabic_text(line) if line else '&nbsp;'
            for line in wrapped_lines
        ))
    except Exception:
        return arabic_pdf(text)


@register.filter
def arabic_digits(value):
    if value is None:
        return ''
    return str(value).translate(_ARABIC_DIGIT_MAP)
