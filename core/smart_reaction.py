"""
Smart Reaction: Tự động phân tích ngữ cảnh tin nhắn của Học sinh & Phụ huynh
để thả biểu cảm Zalo (Reactions) phù hợp với phong thái 'Gia Sư Nghiêm Khắc'.
"""

def pick_smart_reaction(content: str, is_photo: bool = False, is_homework_done: bool = False) -> str:
    """
    Trả về loại reaction Zalo phù hợp:
    'heart' | 'like' | 'haha' | 'wow' | 'cry' | 'angry'
    """
    if not content and not is_photo:
        return "like"

    text = content.lower()

    # 1. Phụ huynh xác nhận xem báo cáo / cảm ơn
    if any(k in text for k in ["được rồi", "da xem", "đã xem", "ok", "oke", "cảm ơn", "cam on", "tuyệt vời"]):
        return "heart"

    # 2. Học sinh hoàn thành bài tập đúng hạn
    if is_homework_done or any(k in text for k in ["hoàn thành", "làm xong", "nộp bài", "xong rồi"]):
        return "like"

    # 3. Học sinh than thở, lười biếng, đòi trốn học (Gia sư nghiêm khắc cảnh báo)
    if any(k in text for k in ["mệt quá", "lười", "chán", "không làm đâu", "mai làm", "khó quá bỏ qua", "giải hộ"]):
        return "angry"

    # 4. Học sinh thắc mắc, hỏi bài, cầu tiến
    if any(k in text for k in ["hướng dẫn", "tại sao", "câu này", "công thức", "bài 1", "bài 2", "bài 3", "jerryhg", "jerryhg ơi", "thầy ơi", "thư ơi", "cô ơi"]):
        return "wow"

    # 5. Tin nhắn có ảnh nộp bài
    if is_photo:
        return "like"

    return "like"
