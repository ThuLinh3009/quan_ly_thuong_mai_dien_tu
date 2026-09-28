from app.core.text import slugify, strip_html_tags


def test_slugify_removes_vietnamese_diacritics():
    assert slugify("Số Đỏ") == "so-do"
    assert slugify("Đắc Nhân Tâm") == "dac-nhan-tam"


def test_slugify_collapses_punctuation():
    assert slugify("  Hello,   World!!  ") == "hello-world"


def test_slugify_empty_falls_back_to_item():
    assert slugify("***") == "item"


def test_strip_html_tags_removes_tags():
    assert strip_html_tags("<script>alert(1)</script>Hello") == "alert(1)Hello"
    assert strip_html_tags("<b>bold</b> text") == "bold text"


def test_strip_html_tags_leaves_plain_text_untouched():
    assert strip_html_tags("Sách rất hay, đáng đọc!") == "Sách rất hay, đáng đọc!"
