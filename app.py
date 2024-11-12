from flask import Flask, render_template, request, jsonify
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# إعدادات البريد الإلكتروني
SMTP_SERVER = "smtp.gmail.com"      # خادم SMTP (مثل Gmail)
SMTP_PORT = 587                     # المنفذ الخاص بـ SMTP (587 لـ Gmail)
SENDER_EMAIL = "your_email@gmail.com"  # بريد المرسل
SENDER_PASSWORD = "your_email_password"  # كلمة مرور بريد المرسل

# قائمة الألغاز الموسعة
puzzles = [
    {"question": "شيء كلما أخذت منه كبر، ما هو؟", "answer": "الحفرة", "choices": ["الحفرة", "البحر", "الجبال"]},
    {"question": "ما هو الشيء الذي يمشي بلا قدمين ويبكي بلا عينين؟", "answer": "السحاب", "choices": ["السحاب", "النهر", "الرياح"]},
    {"question": "ما هو الشيء الذي يتكلم جميع لغات العالم؟", "answer": "الصدى", "choices": ["الصدى", "الكتاب", "التلفاز"]},
    {"question": "له رأس ولا عين له، ما هو؟", "answer": "الدبوس", "choices": ["الدبوس", "العصا", "القلم"]},
    {"question": "شيء يحملك وتحمله، نصفه ناشف ونصفه مبلول، ما هو؟", "answer": "السفينة", "choices": ["السفينة", "القارب", "الجسر"]},
    {"question": "شيء يسمع بلا أذن ويتكلم بلا لسان، ما هو؟", "answer": "الهاتف", "choices": ["الهاتف", "الراديو", "التلفاز"]},
    {"question": "له أوراق وما هو بنبات، له جلد وما هو بحيوان، وعلم وما هو بإنسان، ما هو؟", "answer": "الكتاب", "choices": ["الكتاب", "الدفتر", "اللوحة"]},
    {"question": "ما هو البيت الذي ليس فيه أبواب ولا نوافذ؟", "answer": "بيت الشعر", "choices": ["بيت الشعر", "بيت النمل", "بيت الحشرات"]},
    {"question": "ما هو الشيء الذي يقرصك ولا تراه؟", "answer": "الجوع", "choices": ["الجوع", "العطش", "البرد"]},
    {"question": "كلما زاد نقص، ما هو؟", "answer": "العمر", "choices": ["العمر", "الحفرة", "الماء"]}
]

# قائمة لتخزين بيانات اللاعبين مؤقتًا
players_scores = {}

# الصفحة الرئيسية
@app.route('/')
def index():
    return render_template('index.html')

# بدء اللعبة واختيار ألغاز عشوائية
@app.route('/start_game', methods=['POST'])
def start_game():
    data = request.json
    player_name = data.get("player_name")
    player_email = data.get("player_email")

    # اختيار 5 ألغاز عشوائية للعبة الحالية
    selected_puzzles = random.sample(puzzles, 5)
    players_scores[player_name] = {
        "score": 0,
        "current_question": 0,
        "email": player_email,
        "puzzles": selected_puzzles
    }
    return jsonify({"message": f"مرحبًا {player_name}! بدأت اللعبة!"})

# إرسال السؤال التالي مع الخيارات
@app.route('/get_question', methods=['POST'])
def get_question():
    data = request.json
    player_name = data.get("player_name")
    player_info = players_scores.get(player_name)

    if not player_info:
        return jsonify({"error": "اللاعب غير موجود"}), 404

    question_index = player_info["current_question"]
    puzzles = player_info["puzzles"]

    if question_index < len(puzzles):
        question = puzzles[question_index]
        choices = question["choices"].copy()
        random.shuffle(choices)
        return jsonify({
            "question": question["question"],
            "choices": choices,
            "index": question_index
        })
    else:
        return jsonify({"message": f"تهانينا! أنهيت اللعبة برصيد {player_info['score']} نقطة"})

# التحقق من الإجابة
@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    player_name = data.get("player_name")
    selected_answer = data.get("answer").strip().lower()
    question_index = data.get("index")
    player_info = players_scores.get(player_name)
    
    if question_index < len(player_info["puzzles"]):
        correct_answer = player_info["puzzles"][question_index]["answer"]
        if selected_answer == correct_answer:
            player_info["score"] += 10  # إضافة النقاط
            player_info["current_question"] += 1
            return jsonify({"message": "إجابة صحيحة! 👏", "score": player_info["score"]})
        else:
            player_info["current_question"] += 1
            return jsonify({"message": "إجابة خاطئة! 😅", "score": player_info["score"]})
    return jsonify({"error": "طلب غير صحيح"}), 400

# مسار الخروج من اللعبة
@app.route('/exit_game', methods=['POST'])
def exit_game():
    data = request.json
    player_name = data.get("player_name")
    player_info = players_scores.get(player_name)

    if player_info:
        player_email = player_info["email"]
        score = player_info["score"]
        
        # إرسال البريد الإلكتروني عند الخروج
        send_exit_email(player_name, player_email, score)

        # حذف بيانات اللاعب من اللعبة
        players_scores.pop(player_name, None)
        
        return jsonify({"message": f"تم الخروج بنجاح، تم إرسال بريد إلكتروني إلى {player_email}!"})
    else:
        return jsonify({"error": "اللاعب غير موجود"}), 404

# دالة إرسال البريد الإلكتروني عند الخروج
def send_exit_email(player_name, player_email, score):
    subject = "خروج من لعبة الألغاز"
    body = f"مرحباً {player_name}!\n\nلقد خرجت من لعبة الألغاز. مجموع نقاطك هو: {score}.\nنتمنى لك العودة قريباً لإكمال التحدي! 🌟"
    
    # إعداد الرسالة
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = player_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # تأمين الاتصال
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, player_email, msg.as_string())
        server.quit()
        print(f"تم إرسال بريد إلكتروني إلى {player_email} بنقاطك الحالية!")
    except Exception as e:
        print(f"حدث خطأ أثناء إرسال البريد الإلكتروني: {e}")

if __name__ == '__main__':
    app.run(debug=True)
