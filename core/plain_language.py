"""Plain-language descriptions of the analytes that appear in the organizer corpus.

The problem statement requires the assistant to say what each test measures and what a
low or high value can mean, at about a class-8 reading level. The organizer glossary
supplies aliases only, so this wording is written by the team and kept here, apart from
the classification code. It is reference wording, not a data source: nothing in this
module can set a status, pick a range, or convert a unit, and every sentence is written
to describe a possibility rather than to diagnose a person.
"""

from __future__ import annotations

ATTRIBUTION = (
    "Plain-language wording written by the project team for readability. The organizer "
    "files supply the ranges, aliases, and urgent limits; they do not define the tests."
)

_UNKNOWN = {
    "en": "The supplied files do not say what this test measures.",
    "ur": "فائلوں میں یہ نہیں بتایا گیا کہ یہ ٹیسٹ کیا ناپتا ہے۔",
}

# measures / low / high per analyte, matching the canonical names in the range sheets.
_ANALYTES: dict[str, dict[str, dict[str, str]]] = {
    "Hemoglobin": {
        "en": {
            "measures": "Hemoglobin is the part of your red blood cells that carries oxygen from your lungs to the rest of your body.",
            "low": "A lower result can mean the blood is carrying less oxygen than usual, which some people feel as tiredness or shortness of breath. Many different things can cause it.",
            "high": "A higher result can mean the blood holds more hemoglobin than usual. Living at high altitude, smoking, and low body water are some of the reasons this happens.",
        },
        "ur": {
            "measures": "ہیموگلوبن خون کے سرخ خلیوں کا وہ حصہ ہے جو پھیپھڑوں سے آکسیجن جسم کے باقی حصوں تک پہنچاتا ہے۔",
        },
    },
    "White Blood Cell Count": {
        "en": {
            "measures": "White blood cells are the cells your body uses to fight germs. This test counts how many are in a small amount of blood.",
            "low": "A lower count can mean the body has fewer of these germ-fighting cells than usual.",
            "high": "A higher count often happens when the body is responding to an infection or to stress on the body. It can also follow some medicines.",
        },
        "ur": {
            "measures": "سفید خون کے خلیے جسم کو جراثیم سے لڑنے میں مدد دیتے ہیں۔ یہ ٹیسٹ خون کے ایک چھوٹے نمونے میں ان کی تعداد گنتا ہے۔",
        },
    },
    "Platelet Count": {
        "en": {
            "measures": "Platelets are tiny pieces in your blood that stick together to stop bleeding when you get a cut.",
            "low": "A lower count can mean the blood clots more slowly than usual, so bruises or bleeding may last longer.",
            "high": "A higher count can mean the body is making more platelets than usual.",
        },
        "ur": {
            "measures": "پلیٹلیٹس خون کے وہ ننھے اجزا ہیں جو زخم لگنے پر خون بہنا روکنے کے لیے جڑ جاتے ہیں۔",
        },
    },
    "Red Blood Cell Count": {
        "en": {
            "measures": "Red blood cells carry oxygen around your body. This test counts how many are in a small amount of blood.",
            "low": "A lower count can mean fewer cells are available to carry oxygen.",
            "high": "A higher count can mean the body is making more of these cells than usual.",
        },
        "ur": {
            "measures": "سرخ خون کے خلیے جسم میں آکسیجن پہنچاتے ہیں۔ یہ ٹیسٹ ان کی تعداد گنتا ہے۔",
        },
    },
    "Fasting Blood Sugar": {
        "en": {
            "measures": "This test measures the amount of sugar (glucose) in your blood after several hours without food. Your body uses that sugar for energy.",
            "low": "A lower result can mean blood sugar dropped further than usual while fasting, which some people feel as shakiness or dizziness.",
            "high": "A higher result can mean the body is having trouble keeping fasting blood sugar in the usual range. A doctor decides what that means and whether to repeat the test.",
        },
        "ur": {
            "measures": "یہ ٹیسٹ کئی گھنٹے کچھ نہ کھانے کے بعد خون میں شوگر (گلوکوز) کی مقدار ناپتا ہے، جسے جسم توانائی کے لیے استعمال کرتا ہے۔",
        },
    },
    "ALT": {
        "en": {
            "measures": "ALT (also written SGPT) is an enzyme found mostly in the liver. A blood test shows how much of it has leaked into the blood.",
            "low": "A lower result is not usually the part of this test that doctors watch.",
            "high": "A higher result can mean liver cells have released more of this enzyme than usual. Medicines, infections, and other causes can all raise it, so a doctor interprets it with the rest of the picture.",
        },
        "ur": {
            "measures": "اے ایل ٹی (جسے ایس جی پی ٹی بھی لکھا جاتا ہے) ایک انزائم ہے جو زیادہ تر جگر میں ہوتا ہے۔ خون کا ٹیسٹ بتاتا ہے کہ اس کی کتنی مقدار خون میں آئی ہے۔",
        },
    },
    "AST": {
        "en": {
            "measures": "AST (also written SGOT) is an enzyme found in the liver and in muscle. A blood test shows how much of it is in the blood.",
            "low": "A lower result is not usually the part of this test that doctors watch.",
            "high": "A higher result can mean liver or muscle cells have released more of this enzyme than usual, including after hard exercise.",
        },
        "ur": {
            "measures": "اے ایس ٹی (جسے ایس جی او ٹی بھی لکھا جاتا ہے) ایک انزائم ہے جو جگر اور پٹھوں میں پایا جاتا ہے۔",
        },
    },
    "Cholesterol": {
        "en": {
            "measures": "Cholesterol is a fatty substance your body needs to build cells. This test measures how much of it is in your blood.",
            "low": "A lower result means less cholesterol in the blood than the listed range.",
            "high": "A higher result can mean more of this fatty substance is in the blood than the usual range. Diet, exercise, weight, and family history all affect it.",
        },
        "ur": {
            "measures": "کولیسٹرول ایک چکنائی والا مادہ ہے جو جسم کو خلیے بنانے کے لیے درکار ہوتا ہے۔ یہ ٹیسٹ خون میں اس کی مقدار ناپتا ہے۔",
        },
    },
    "TSH": {
        "en": {
            "measures": "TSH is a hormone from a gland in your brain that tells the thyroid gland in your neck how much thyroid hormone to make.",
            "low": "A lower result can mean the brain is sending less of this signal than usual.",
            "high": "A higher result can mean the brain is sending a stronger signal because the thyroid is not keeping up.",
        },
        "ur": {
            "measures": "ٹی ایس ایچ ایک ہارمون ہے جو دماغ کے ایک غدود سے نکلتا ہے اور گردن میں تھائرائیڈ کو بتاتا ہے کہ کتنا ہارمون بنانا ہے۔",
        },
    },
    "Urine pH": {
        "en": {
            "measures": "This test measures how acidic or alkaline your urine is. Food, drinks, and how much water you drink can all change it.",
            "low": "A lower result means the urine is more acidic than the listed range.",
            "high": "A higher result means the urine is more alkaline than the listed range.",
        },
        "ur": {
            "measures": "یہ ٹیسٹ بتاتا ہے کہ پیشاب کتنا تیزابی یا قلوی ہے۔ خوراک، مشروبات اور پانی کی مقدار اس پر اثر ڈالتی ہے۔",
        },
    },
    "Urine Protein": {
        "en": {
            "measures": "This test checks whether protein is leaking into your urine. Healthy kidneys normally keep protein in the blood.",
            "low": "The files list only a single expected value for this test, so there is no low result to describe.",
            "high": "A result other than the expected one can mean protein was found in the urine, which a doctor would want to look into.",
        },
        "ur": {
            "measures": "یہ ٹیسٹ دیکھتا ہے کہ پیشاب میں پروٹین آ رہا ہے یا نہیں۔ صحت مند گردے پروٹین کو خون میں روکے رکھتے ہیں۔",
        },
    },
}

_STATUS_MEANING = {
    "en": {
        "normal": "This result sits inside the range the lab's sheet lists for someone of this age and sex.",
        "urgent": "This result passes a limit the lab marks as needing urgent care, so please see a doctor today.",
        "cannot_classify": "The supplied files do not contain what is needed to compare this result, so it is left unclassified rather than guessed.",
        "needs_clarification": "The right range cannot be chosen until the missing details in the report are filled in.",
    },
    "ur": {
        "normal": "یہ نتیجہ اس عمر اور جنس کے لیے فائل میں دی گئی حد کے اندر ہے۔",
        "low": "یہ نتیجہ فائل میں دی گئی حد سے کم ہے۔ اس کی کئی وجوہات ہو سکتی ہیں اور صرف ڈاکٹر ہی بتا سکتا ہے۔",
        "high": "یہ نتیجہ فائل میں دی گئی حد سے زیادہ ہے۔ اس کی کئی وجوہات ہو سکتی ہیں اور صرف ڈاکٹر ہی بتا سکتا ہے۔",
        "urgent": "یہ نتیجہ اس حد سے گزر گیا ہے جسے فائل فوری توجہ کے لیے نشان زد کرتی ہے۔ آج ہی ڈاکٹر سے رابطہ کریں۔",
        "cannot_classify": "فائلوں میں اس نتیجے کا موازنہ کرنے کے لیے کافی معلومات موجود نہیں، اس لیے اندازہ لگانے کے بجائے اسے غیر درجہ بند رکھا گیا ہے۔",
        "needs_clarification": "رپورٹ میں کمی پوری ہونے تک درست حد منتخب نہیں کی جا سکتی۔",
    },
}


def describes(canonical: str | None, language: str = "en") -> str:
    """What the test measures, in simple words."""
    entry = _ANALYTES.get(canonical or "")
    if not entry:
        return _UNKNOWN.get(language, _UNKNOWN["en"])
    wording = entry.get(language) or entry["en"]
    return wording.get("measures") or entry["en"]["measures"]


def result_meaning(canonical: str | None, status: str, language: str = "en") -> str:
    """What a result of this status can mean, without naming a disease."""
    fixed = _STATUS_MEANING.get(language, _STATUS_MEANING["en"]).get(status)
    if fixed:
        return fixed
    entry = _ANALYTES.get(canonical or "")
    if entry and status in {"low", "high"}:
        wording = entry.get(language) or entry["en"]
        text = wording.get(status) or entry["en"].get(status)
        if text:
            return text
    return _STATUS_MEANING["en"].get(status, _STATUS_MEANING["en"]["cannot_classify"])


_QUESTION_TEMPLATES = {
    "en": {
        "urgent": "My {name} result passed a critical limit in the lab's urgent-values list. Do I need to be seen today, and what happens next?",
        "high": "My {name} came out above the normal range for my age and sex. What can cause that, and should it be repeated?",
        "low": "My {name} came out below the normal range for my age and sex. What can cause that, and should it be repeated?",
        "cannot_classify": "My {name} could not be compared with the lab's reference sheets. Which range applies to me for this test?",
        "needs_clarification": "The report is missing the details needed to pick the right range for my {name}. Can the lab confirm them and reissue it?",
    },
    "ur": {
        "urgent": "میرا {name} فائل میں درج اہم حد سے گزر گیا ہے۔ کیا مجھے آج ہی ملنا چاہیے اور اس کے بعد کیا ہوگا؟",
        "high": "میرا {name} میری عمر اور جنس کے لیے دی گئی حد سے زیادہ ہے۔ اس کی کیا وجوہات ہو سکتی ہیں اور کیا ٹیسٹ دوبارہ کرانا چاہیے؟",
        "low": "میرا {name} میری عمر اور جنس کے لیے دی گئی حد سے کم ہے۔ اس کی کیا وجوہات ہو سکتی ہیں اور کیا ٹیسٹ دوبارہ کرانا چاہیے؟",
        "cannot_classify": "میرے {name} کا موازنہ لیب کی فائلوں سے نہیں ہو سکا۔ اس ٹیسٹ کے لیے میرے لیے کون سی حد لاگو ہوتی ہے؟",
        "needs_clarification": "رپورٹ میں {name} کی درست حد چننے کے لیے ضروری تفصیل موجود نہیں۔ کیا لیب اس کی تصدیق کر کے رپورٹ دوبارہ جاری کر سکتی ہے؟",
    },
}

_GENERAL_QUESTIONS = {
    "en": [
        "Looking at this report as a whole, is there anything here you want to recheck or follow up on?",
        "Do any of these results change the medicines, food, or activity you would recommend for me?",
        "When should I have these tests done again?",
    ],
    "ur": [
        "پوری رپورٹ دیکھ کر، کیا کوئی چیز ہے جسے آپ دوبارہ دیکھنا یا جانچنا چاہیں گے؟",
        "کیا ان نتائج کی وجہ سے میری دوا، خوراک یا سرگرمی کے بارے میں آپ کا مشورہ بدلتا ہے؟",
        "مجھے یہ ٹیسٹ دوبارہ کب کرانے چاہیے؟",
    ],
}

_PRIORITY = {"urgent": 0, "cannot_classify": 1, "high": 2, "low": 2, "needs_clarification": 3}


def doctor_questions(rows: list[dict], language: str = "en") -> list[str]:
    """Build 3 to 5 questions for the doctor, led by the results that are not normal."""
    templates = _QUESTION_TEMPLATES.get(language, _QUESTION_TEMPLATES["en"])
    general = _GENERAL_QUESTIONS.get(language, _GENERAL_QUESTIONS["en"])
    flagged = [row for row in rows if row.get("status") in _PRIORITY]
    if not flagged:
        return []
    flagged.sort(key=lambda row: _PRIORITY[row["status"]])

    questions: list[str] = []
    for row in flagged:
        template = templates.get(row["status"])
        if not template:
            continue
        name = row.get("canonical_name") or row.get("original_name") or ""
        question = template.format(name=name)
        if question not in questions:
            questions.append(question)
        if len(questions) == 5:
            return questions
    for extra in general:
        if len(questions) >= 3:
            break
        if extra not in questions:
            questions.append(extra)
    return questions[:5]
