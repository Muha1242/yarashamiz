"""Yarashamiz v3.1 — haqiqiy AI yordamchi (Google Gemini API).

Kutubxona kerak emas (stdlib urllib). GEMINI_API_KEY bo'lmasa yoki API xato
bersa — None qaytaradi; chaqiruvchi shablon (AI_TPL) bilan davom etadi.
API kalitini Google AI Studio'dan oling: https://aistudio.google.com/apikey
"""
import json
import os
import urllib.request

KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
ENDPOINT = (f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{MODEL}:generateContent")

SIT_NAMES = {
    "sorry": "Kechirim so'ramoqchiman (munosabatlarni tiklash)",
    "miss": "Sog'indim (sevgan insonini sog'indirish)",
    "love": "Sevgi izhori (dil izhor qilish)",
    "thank": "Minnatdorchilik (rahmat aytish)",
    "date": "Uchrashuvga taklif",
}

PROMPT = (
    "Sen «Yarashamiz» Telegram botining AI yordamchisan — bir-biridan "
    "arazlagan sevishganlarni yarashtirishda yordam berasan.\n"
    "Vazifa: {sit} maqsadida samimiy, issiq, qisqa xat yoz.\n"
    "Foydalanuvchi kalit so'zlari: {w}\n"
    "Talablar:\n"
    "- faqat O'zbek tilida (lotin yozuvi)\n"
    "- 300 belgidan oshmaydi\n"
    "- tabiiy, ortiqcha gapirmaydigan, yurakdan chiqqan\n"
    "- emoji ishlat, lekin ko'p emas (1-2 ta)\n"
    "- faqat xat matnini qaytar, boshqa hech narsa qo'shma"
)


def _ask(prompt: str, max_tokens: int = 300):
    """Gemini'ga so'rov. Kalit yo'q yoki xato bo'lsa None."""
    if not KEY:
        return None
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.85},
    }).encode()
    req = urllib.request.Request(
        ENDPOINT + f"?key={KEY}", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read())
        return (data["candidates"][0]["content"]["parts"][0]["text"] or "").strip()
    except Exception:  # noqa: BLE001
        return None


def compose(sit: str, words: str):
    """Xat matnini qaytaradi; muammo bo'lsa None."""
    prompt = PROMPT.format(sit=SIT_NAMES.get(sit, sit), w=(words or "yo'q"))
    text = _ask(prompt, 300)
    return text[:400] if text else None


COACH_RULES = (
    "Sen «Yarashamiz» botining munosabat maslahatchisisan. Juftliklarga "
    "arazlarni hal qilishda yordam berasan.\n"
    "Qoidalar:\n"
    "- faqat o'zbek tilida (lotin yozuvi)\n"
    "- 5-7 gap, amaliy va hurmatli\n"
    "- ayblamang, «men» tilidan gapirishni o'rgating\n"
    "- agar zo'ravonlik yoki o'z joniga qasd haqida bo'lsa — xavfsizlikni "
    "birinchi o'ringa qo'y va mutaxassisga murojaat qilishni tavsiya qil\n"
    "- ro'yxat shaklida 2-3 qadam bering\n"
    "- oldingi suhbatni hisobga ol, takrorlamang"
)


def coach(question: str, history=None):
    """Munosabat bo'yicha maslahat; muammo bo'lsa None."""
    parts = [COACH_RULES]
    if history:
        parts.append("Oldingi suhbat:")
        for m in history[-8:]:
            who = "Foydalanuvchi" if m.get("r") == "user" else "Maslahatchi"
            parts.append(f"{who}: {m.get('t')}")
    parts.append(f"Yangi savol: {(question or '')[:400]}")
    text = _ask("\n".join(parts), 500)
    return text[:900] if text else None


def coach_chat(history, question):
    return coach(question, history)
