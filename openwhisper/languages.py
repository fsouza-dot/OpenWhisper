"""Whisper-supported languages for speech-to-text.

This list covers all 99 languages supported by OpenAI Whisper large-v3,
which is the model used by Groq's whisper-large-v3-turbo endpoint.

Languages are ordered by transcription quality (most training data first).
"""

# (code, english_name, native_name)
WHISPER_LANGUAGES: list[tuple[str, str, str]] = [
    # Tier 1: Best quality (~5% WER or better)
    ("en", "English", "English"),
    ("es", "Spanish", "Espanol"),
    ("fr", "French", "Francais"),
    ("de", "German", "Deutsch"),
    ("it", "Italian", "Italiano"),
    ("pt", "Portuguese", "Portugues"),
    ("nl", "Dutch", "Nederlands"),
    ("pl", "Polish", "Polski"),
    ("ru", "Russian", "Russkiy"),
    ("uk", "Ukrainian", "Ukrayinska"),
    ("ja", "Japanese", "Nihongo"),
    ("ko", "Korean", "Hangugeo"),
    ("zh", "Chinese", "Zhongwen"),

    # Tier 2: Good quality (~10-15% WER)
    ("ar", "Arabic", "Al-Arabiyyah"),
    ("cs", "Czech", "Cestina"),
    ("da", "Danish", "Dansk"),
    ("el", "Greek", "Ellinika"),
    ("fi", "Finnish", "Suomi"),
    ("he", "Hebrew", "Ivrit"),
    ("hi", "Hindi", "Hindi"),
    ("hu", "Hungarian", "Magyar"),
    ("id", "Indonesian", "Bahasa Indonesia"),
    ("ms", "Malay", "Bahasa Melayu"),
    ("no", "Norwegian", "Norsk"),
    ("ro", "Romanian", "Romana"),
    ("sk", "Slovak", "Slovencina"),
    ("sv", "Swedish", "Svenska"),
    ("th", "Thai", "Phasa Thai"),
    ("tr", "Turkish", "Turkce"),
    ("vi", "Vietnamese", "Tieng Viet"),

    # Tier 3: Usable quality (~15-25% WER)
    ("af", "Afrikaans", "Afrikaans"),
    ("az", "Azerbaijani", "Azerbaycan"),
    ("be", "Belarusian", "Belaruskaya"),
    ("bg", "Bulgarian", "Balgarski"),
    ("bn", "Bengali", "Bangla"),
    ("bs", "Bosnian", "Bosanski"),
    ("ca", "Catalan", "Catala"),
    ("cy", "Welsh", "Cymraeg"),
    ("et", "Estonian", "Eesti"),
    ("eu", "Basque", "Euskara"),
    ("fa", "Persian", "Farsi"),
    ("gl", "Galician", "Galego"),
    ("gu", "Gujarati", "Gujarati"),
    ("hr", "Croatian", "Hrvatski"),
    ("hy", "Armenian", "Hayeren"),
    ("is", "Icelandic", "Islenska"),
    ("ka", "Georgian", "Kartuli"),
    ("kk", "Kazakh", "Qazaq"),
    ("kn", "Kannada", "Kannada"),
    ("lt", "Lithuanian", "Lietuviu"),
    ("lv", "Latvian", "Latviesu"),
    ("mk", "Macedonian", "Makedonski"),
    ("ml", "Malayalam", "Malayalam"),
    ("mn", "Mongolian", "Mongol"),
    ("mr", "Marathi", "Marathi"),
    ("mt", "Maltese", "Malti"),
    ("ne", "Nepali", "Nepali"),
    ("pa", "Punjabi", "Punjabi"),
    ("si", "Sinhala", "Sinhala"),
    ("sl", "Slovenian", "Slovenscina"),
    ("sq", "Albanian", "Shqip"),
    ("sr", "Serbian", "Srpski"),
    ("sw", "Swahili", "Kiswahili"),
    ("ta", "Tamil", "Tamil"),
    ("te", "Telugu", "Telugu"),
    ("tl", "Tagalog", "Tagalog"),
    ("ur", "Urdu", "Urdu"),

    # Tier 4: Limited quality (>25% WER, but functional)
    ("am", "Amharic", "Amarigna"),
    ("as", "Assamese", "Asomiya"),
    ("ba", "Bashkir", "Bashqort"),
    ("bo", "Tibetan", "Bod skad"),
    ("br", "Breton", "Brezhoneg"),
    ("fo", "Faroese", "Foroyskt"),
    ("ha", "Hausa", "Hausa"),
    ("haw", "Hawaiian", "Olelo Hawaii"),
    ("jw", "Javanese", "Basa Jawa"),
    ("km", "Khmer", "Phasa Khmer"),
    ("la", "Latin", "Latina"),
    ("lb", "Luxembourgish", "Letzebuergesch"),
    ("ln", "Lingala", "Lingala"),
    ("lo", "Lao", "Phasa Lao"),
    ("mg", "Malagasy", "Malagasy"),
    ("mi", "Maori", "Te Reo Maori"),
    ("my", "Myanmar", "Myanma"),
    ("nn", "Nynorsk", "Nynorsk"),
    ("oc", "Occitan", "Occitan"),
    ("ps", "Pashto", "Pashto"),
    ("sa", "Sanskrit", "Samskrtam"),
    ("sd", "Sindhi", "Sindhi"),
    ("sn", "Shona", "chiShona"),
    ("so", "Somali", "Soomaali"),
    ("su", "Sundanese", "Basa Sunda"),
    ("tk", "Turkmen", "Turkmen"),
    ("tt", "Tatar", "Tatar"),
    ("uz", "Uzbek", "Ozbek"),
    ("yi", "Yiddish", "Yidish"),
    ("yo", "Yoruba", "Yoruba"),
]

# Quick lookup by code
LANGUAGE_BY_CODE: dict[str, tuple[str, str]] = {
    code: (english, native) for code, english, native in WHISPER_LANGUAGES
}

# All valid codes for validation
VALID_LANGUAGE_CODES: set[str] = {code for code, _, _ in WHISPER_LANGUAGES}


def get_language_display(code: str) -> str:
    """Return 'English Name (Native)' for display in UI."""
    if code not in LANGUAGE_BY_CODE:
        return code
    english, native = LANGUAGE_BY_CODE[code]
    if english == native:
        return english
    return f"{english} ({native})"


def get_language_name(code: str) -> str:
    """Return just the English name."""
    if code not in LANGUAGE_BY_CODE:
        return code
    return LANGUAGE_BY_CODE[code][0]
