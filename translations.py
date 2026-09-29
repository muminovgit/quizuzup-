"""Minimal i18n layer: uz / ru / en text for every user-facing bot message."""

DEFAULT_LANGUAGE = "uz"

LANGUAGE_NAMES = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

TEXTS: dict[str, dict[str, str]] = {
    "choose_language": {
        "uz": "🌐 Tilni tanlang:",
        "ru": "🌐 Выберите язык:",
        "en": "🌐 Choose your language:",
    },
    "language_changed": {
        "uz": "✅ Til o'zbekchaga o'zgartirildi.",
        "ru": "✅ Язык изменён на русский.",
        "en": "✅ Language switched to English.",
    },
    "welcome": {
        "uz": (
            "👋 Quiz Botga xush kelibsiz!\n\n"
            "📤 /newquiz — .xlsx fayl yuklab yangi test yaratish\n"
            "📚 /myquizzes — saqlangan testlaringiz ro'yxati\n"
            "▶️ /startquiz [nomi] — testni shu chatda boshlash\n"
            "⏸ /stop — ishlab turgan testni pauza qilish\n"
            "🗑 /deletequiz [nomi] — testni o'chirish\n"
            "🏆 /leaderboard — shu chatdagi reyting\n"
            "🌟 /upgrade — Telegram Stars orqali Pro tarifga o'tish\n"
            "🌐 /language — tilni o'zgartirish\n\n"
            "🆓 Bepul tarif: {max_quizzes} ta test, har birida {max_questions} tagacha savol."
        ),
        "ru": (
            "👋 Добро пожаловать в Quiz Bot!\n\n"
            "📤 /newquiz — загрузить .xlsx файл и создать тест\n"
            "📚 /myquizzes — список сохранённых тестов\n"
            "▶️ /startquiz [название] — запустить тест в этом чате\n"
            "⏸ /stop — поставить текущий тест на паузу\n"
            "🗑 /deletequiz [название] — удалить тест\n"
            "🏆 /leaderboard — рейтинг в этом чате\n"
            "🌟 /upgrade — перейти на Pro через Telegram Stars\n"
            "🌐 /language — сменить язык\n\n"
            "🆓 Бесплатный тариф: {max_quizzes} теста, до {max_questions} вопросов в каждом."
        ),
        "en": (
            "👋 Welcome to Quiz Bot!\n\n"
            "📤 /newquiz — upload an .xlsx file to create a quiz\n"
            "📚 /myquizzes — list your saved quizzes\n"
            "▶️ /startquiz [name] — run a quiz in this chat\n"
            "⏸ /stop — pause the quiz that's currently running\n"
            "🗑 /deletequiz [name] — remove one of your quizzes\n"
            "🏆 /leaderboard — top scorers in this chat\n"
            "🌟 /upgrade — go Pro with Telegram Stars\n"
            "🌐 /language — change language\n\n"
            "🆓 Free tier: {max_quizzes} quizzes, up to {max_questions} questions each."
        ),
    },
    "template_caption": {
        "uz": (
            "📎 Mana shu shablonni to'ldirib, /newquiz buyrug'i orqali yuboring:\n"
            "Question | Option A | Option B | Option C | Option D | Correct Answer (A/B/C/D) | Explanation"
        ),
        "ru": (
            "📎 Заполните этот шаблон и отправьте его командой /newquiz:\n"
            "Question | Option A | Option B | Option C | Option D | Correct Answer (A/B/C/D) | Explanation"
        ),
        "en": (
            "📎 Fill in this template and send it via /newquiz:\n"
            "Question | Option A | Option B | Option C | Option D | Correct Answer (A/B/C/D) | Explanation"
        ),
    },
    "limit_quizzes": {
        "uz": "⚠️ Bepul tarifda {max_quizzes} tagacha test yaratish mumkin.\n/deletequiz bilan birini o'chiring yoki /upgrade orqali Pro tarifga o'ting.",
        "ru": "⚠️ На бесплатном тарифе можно создать максимум {max_quizzes} теста.\nУдалите один через /deletequiz или перейдите на Pro через /upgrade.",
        "en": "⚠️ Free tier allows up to {max_quizzes} quizzes.\nUse /deletequiz to remove one, or /upgrade to go Pro.",
    },
    "send_file": {
        "uz": "📤 Yangi test uchun .xlsx faylni yuboring (shablon: /start orqali oling).",
        "ru": "📤 Отправьте .xlsx файл для нового теста (шаблон можно получить через /start).",
        "en": "📤 Send me the .xlsx file for your new quiz (get the template via /start).",
    },
    "send_valid_file": {
        "uz": "⚠️ Iltimos, .xlsx faylni hujjat sifatida yuboring yoki bekor qilish uchun /cancel bosing.",
        "ru": "⚠️ Пожалуйста, отправьте .xlsx файл как документ, или /cancel для отмены.",
        "en": "⚠️ Please upload the .xlsx file as a document, or /cancel to stop.",
    },
    "not_xlsx": {
        "uz": "⚠️ Bu .xlsx fayl emas. Iltimos, to'g'ri Excel fayl yuboring.",
        "ru": "⚠️ Это не .xlsx файл. Пожалуйста, отправьте корректный Excel-файл.",
        "en": "⚠️ That doesn't look like an .xlsx file. Please send a valid Excel file.",
    },
    "parse_error": {
        "uz": "⚠️ Faylni o'qib bo'lmadi: {error}\nIltimos, tuzatib qayta yuboring.",
        "ru": "⚠️ Не удалось прочитать файл: {error}\nИсправьте и отправьте снова.",
        "en": "⚠️ Couldn't parse that file: {error}\nPlease fix it and send it again.",
    },
    "question_limit": {
        "uz": "⚠️ Bepul tarifda har bir testda {max_questions} tagacha savol bo'lishi mumkin (faylda {got} ta). Qisqartiring yoki /upgrade qiling.",
        "ru": "⚠️ На бесплатном тарифе допускается до {max_questions} вопросов в тесте (в файле {got}). Сократите или сделайте /upgrade.",
        "en": "⚠️ Free tier quizzes can have at most {max_questions} questions (this file has {got}). Trim it or /upgrade.",
    },
    "parsed_ok": {
        "uz": "✅ {count} ta savol o'qildi!\nTest uchun qisqa nom yozing, yoki \"{default_name}\" nomini ishlatish uchun /skip bosing.",
        "ru": "✅ Распознано {count} вопросов!\nОтправьте короткое название теста или /skip, чтобы использовать \"{default_name}\".",
        "en": "✅ Parsed {count} questions!\nSend a short name for this quiz, or /skip to use \"{default_name}\".",
    },
    "quiz_saved": {
        "uz": "✅ \"{name}\" testi {count} ta savol bilan saqlandi.\nBoshlash uchun: /startquiz {name}",
        "ru": "✅ Тест \"{name}\" сохранён ({count} вопросов).\nЗапустить: /startquiz {name}",
        "en": "✅ Saved quiz \"{name}\" with {count} questions.\nRun it with /startquiz {name}",
    },
    "cancelled": {
        "uz": "❌ Bekor qilindi.",
        "ru": "❌ Отменено.",
        "en": "❌ Cancelled.",
    },
    "myquizzes_empty": {
        "uz": "📭 Sizda hali saqlangan testlar yo'q. /newquiz orqali yarating.",
        "ru": "📭 У вас пока нет сохранённых тестов. Создайте через /newquiz.",
        "en": "📭 You don't have any saved quizzes yet. Use /newquiz to create one.",
    },
    "myquizzes_header": {
        "uz": "📚 Sizning testlaringiz:",
        "ru": "📚 Ваши тесты:",
        "en": "📚 Your quizzes:",
    },
    "questions_suffix": {
        "uz": "savol",
        "ru": "вопросов",
        "en": "questions",
    },
    "pick_quiz_start": {
        "uz": "▶️ Boshlash uchun testni tanlang:",
        "ru": "▶️ Выберите тест для запуска:",
        "en": "▶️ Pick a quiz to start:",
    },
    "pick_quiz_delete": {
        "uz": "🗑 O'chirish uchun testni tanlang:",
        "ru": "🗑 Выберите тест для удаления:",
        "en": "🗑 Pick a quiz to delete:",
    },
    "quiz_not_found": {
        "uz": "❌ Bunday nomli test topilmadi. /myquizzes bilan tekshiring.",
        "ru": "❌ Тест с таким названием не найден. Проверьте через /myquizzes.",
        "en": "❌ I couldn't find a quiz with that name. Check /myquizzes.",
    },
    "not_owner_start": {
        "uz": "🚫 Testni faqat uni yuklagan admin boshlashi mumkin.",
        "ru": "🚫 Запустить тест может только тот, кто его загрузил.",
        "en": "🚫 Only the admin who uploaded this quiz can start it.",
    },
    "not_owner_delete": {
        "uz": "🚫 Testni faqat uni yuklagan admin o'chirishi mumkin.",
        "ru": "🚫 Удалить тест может только тот, кто его загрузил.",
        "en": "🚫 Only the admin who uploaded this quiz can delete it.",
    },
    "not_owner_stop": {
        "uz": "🚫 Testni faqat uni boshlagan admin pauza qila oladi.",
        "ru": "🚫 Поставить тест на паузу может только тот, кто его запустил.",
        "en": "🚫 Only the admin who started this quiz can pause it.",
    },
    "not_owner_resume": {
        "uz": "🚫 Faqat testni boshlagan admin davom ettira oladi.",
        "ru": "🚫 Продолжить тест может только тот, кто его запустил.",
        "en": "🚫 Only the admin who started this quiz can resume it.",
    },
    "deleted_quiz": {
        "uz": "🗑 \"{name}\" testi o'chirildi.",
        "ru": "🗑 Тест \"{name}\" удалён.",
        "en": "🗑 Deleted quiz \"{name}\".",
    },
    "quiz_already_running": {
        "uz": "⚠️ Bu chatda test allaqachon ishlamoqda. Avval /stop bilan to'xtating.",
        "ru": "⚠️ В этом чате тест уже запущен. Сначала остановите его через /stop.",
        "en": "⚠️ A quiz is already running in this chat. Stop it with /stop first.",
    },
    "quiz_no_questions": {
        "uz": "⚠️ Bu testda savollar yo'q.",
        "ru": "⚠️ В этом тесте нет вопросов.",
        "en": "⚠️ This quiz has no questions.",
    },
    "quiz_starting": {
        "uz": "🧠 Test boshlanmoqda: {name} ({count} ta savol)",
        "ru": "🧠 Начинаем тест: {name} ({count} вопросов)",
        "en": "🧠 Starting quiz: {name} ({count} questions)",
    },
    "quiz_finished": {
        "uz": "🏁 Test tugadi! Natijalarni ko'rish uchun /leaderboard bosing.",
        "ru": "🏁 Тест завершён! Смотрите /leaderboard для результатов.",
        "en": "🏁 Quiz finished! Check /leaderboard for the top scorers.",
    },
    "quiz_paused_auto": {
        "uz": "⏸ Test avtomatik pauza qilindi — ketma-ket {streak} ta savolga hech kim javob bermadi.",
        "ru": "⏸ Тест автоматически поставлен на паузу — {streak} вопроса подряд остались без ответа.",
        "en": "⏸ Quiz auto-paused — {streak} questions in a row got no answers.",
    },
    "quiz_paused_manual": {
        "uz": "⏸ Test pauza qilindi.",
        "ru": "⏸ Тест поставлен на паузу.",
        "en": "⏸ Quiz paused.",
    },
    "quiz_resumed": {
        "uz": "▶️ Test davom etmoqda...",
        "ru": "▶️ Тест продолжается...",
        "en": "▶️ Resuming the quiz...",
    },
    "resume_button": {
        "uz": "▶️ Davom ettirish",
        "ru": "▶️ Продолжить",
        "en": "▶️ Resume",
    },
    "stop_button": {
        "uz": "⏸ To'xtatish",
        "ru": "⏸ Остановить",
        "en": "⏸ Stop",
    },
    "quiz_error": {
        "uz": "⚠️ Nimadir xato ketdi, test to'xtatildi. Qaytadan /startquiz qiling.",
        "ru": "⚠️ Что-то пошло не так, тест остановлен. Запустите заново через /startquiz.",
        "en": "⚠️ Something went wrong and the quiz was stopped. Try /startquiz again.",
    },
    "add_to_group": {
        "uz": "➕ Guruhga qo'shish",
        "ru": "➕ Добавить в группу",
        "en": "➕ Add me to a group",
    },
    "no_active_quiz": {
        "uz": "ℹ️ Bu chatda hozir ishlab turgan test yo'q.",
        "ru": "ℹ️ В этом чате сейчас нет активного теста.",
        "en": "ℹ️ There's no quiz running in this chat right now.",
    },
    "leaderboard_empty": {
        "uz": "📭 Bu chatda hali javoblar yo'q. /startquiz bilan testni boshlang!",
        "ru": "📭 В этом чате пока нет ответов. Запустите тест через /startquiz!",
        "en": "📭 No answers recorded in this chat yet. Run a quiz with /startquiz!",
    },
    "leaderboard_header": {
        "uz": "🏆 Reyting",
        "ru": "🏆 Рейтинг",
        "en": "🏆 Leaderboard",
    },
    "correct_suffix": {
        "uz": "to'g'ri",
        "ru": "верно",
        "en": "correct",
    },
    "already_pro": {
        "uz": "🌟 Siz allaqachon Pro tarifdasiz. Qo'llab-quvvatlaganingiz uchun rahmat!",
        "ru": "🌟 Вы уже на тарифе Pro. Спасибо за поддержку!",
        "en": "🌟 You're already on the Pro tier. Thanks for your support!",
    },
    "pro_title": {
        "uz": "Quiz Bot Pro",
        "ru": "Quiz Bot Pro",
        "en": "Quiz Bot Pro",
    },
    "pro_description": {
        "uz": "Cheksiz testlar va cheksiz savollarni oching ({stars} Stars).",
        "ru": "Откройте неограниченные тесты и вопросы ({stars} Stars).",
        "en": "Unlock unlimited quizzes and unlimited questions per quiz ({stars} Stars).",
    },
    "payment_success": {
        "uz": "🌟 To'lov qabul qilindi! Endi siz Pro tarifdasiz — cheksiz test va savollar.",
        "ru": "🌟 Оплата получена! Теперь у вас тариф Pro — неограниченные тесты и вопросы.",
        "en": "🌟 Payment received! You're now on the Pro tier — unlimited quizzes and questions.",
    },
    "upgrade_alt_payment": {
        "uz": (
            "💳 Stars orqali to'lay olmasangiz: administratorga murojaat qiling — @{admin}.\n"
            "ID raqamingizni /myid orqali oling va shu raqamni administratorga yuboring — "
            "u sizga qo'lda Pro tarifni faollashtiradi."
        ),
        "ru": (
            "💳 Если не можете оплатить через Stars: напишите администратору — @{admin}.\n"
            "Получите свой ID командой /myid и отправьте его администратору — "
            "он вручную активирует вам тариф Pro."
        ),
        "en": (
            "💳 Can't pay with Stars? Contact the admin — @{admin}.\n"
            "Get your ID with /myid and send it to them — they'll activate Pro manually."
        ),
    },
    "myid_reply": {
        "uz": "🆔 Sizning Telegram ID: `{id}`",
        "ru": "🆔 Ваш Telegram ID: `{id}`",
        "en": "🆔 Your Telegram ID: `{id}`",
    },
    "grantpro_usage": {
        "uz": (
            "Foydalanish: /grantpro <user_id yoki @username>\n"
            "Yoki foydalanuvchining xabariga javob (reply) qilib /grantpro deb yozing."
        ),
        "ru": (
            "Использование: /grantpro <user_id или @username>\n"
            "Либо ответьте (reply) на сообщение пользователя командой /grantpro."
        ),
        "en": (
            "Usage: /grantpro <user_id or @username>\n"
            "Or reply to the user's message with /grantpro."
        ),
    },
    "grantpro_not_found": {
        "uz": "❌ Bu foydalanuvchi topilmadi. U botga hech bo'lmasa bir marta /start yozgan bo'lishi kerak.",
        "ru": "❌ Пользователь не найден. Он должен был хотя бы раз написать боту /start.",
        "en": "❌ User not found. They need to have sent /start to the bot at least once.",
    },
    "grantpro_done": {
        "uz": "✅ {target} uchun Pro tarif faollashtirildi.",
        "ru": "✅ Тариф Pro активирован для {target}.",
        "en": "✅ Pro tier activated for {target}.",
    },
    "revokepro_done": {
        "uz": "❌ {target} uchun Pro tarif bekor qilindi.",
        "ru": "❌ Тариф Pro отключён для {target}.",
        "en": "❌ Pro tier revoked for {target}.",
    },
    "web_login_issued": {
        "uz": (
            "🌐 Veb-sayt orqali ham testlarni yechishingiz mumkin!\n\n"
            "🔗 Sayt: {url}\n"
            "👤 Login: `{username}`\n"
            "🔑 Parol: `{password}`\n\n"
            "Saytda xato javob bergan savollaringiz \"Xatolarim\" bo'limida saqlanadi va qayta yechishingiz mumkin."
        ),
        "ru": (
            "🌐 Тесты можно проходить и на сайте!\n\n"
            "🔗 Сайт: {url}\n"
            "👤 Логин: `{username}`\n"
            "🔑 Пароль: `{password}`\n\n"
            "Вопросы, на которые вы ответили неправильно, сохраняются в разделе \"Мои ошибки\" — их можно пересдать."
        ),
        "en": (
            "🌐 You can also take quizzes on the website!\n\n"
            "🔗 Site: {url}\n"
            "👤 Login: `{username}`\n"
            "🔑 Password: `{password}`\n\n"
            "Questions you get wrong are saved in \"My Mistakes\" so you can review and retry them."
        ),
    },
    "webportal_not_premium": {
        "uz": "🌐 Veb-portal faqat Pro foydalanuvchilar uchun. /upgrade orqali Pro oling.",
        "ru": "🌐 Веб-портал доступен только для Pro. Оформите /upgrade.",
        "en": "🌐 The web portal is Pro-only. Get Pro with /upgrade.",
    },
}


def t(key: str, lang: str | None, **kwargs: object) -> str:
    lang = lang if lang in LANGUAGE_NAMES else DEFAULT_LANGUAGE
    text = TEXTS[key].get(lang, TEXTS[key][DEFAULT_LANGUAGE])
    return text.format(**kwargs) if kwargs else text
