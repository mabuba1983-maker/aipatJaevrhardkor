from nuwaa.conversation.chat import Chat
c = Chat()
sid = "cli"
print("اكتب رسالتك. /جديد = محادثة جديدة (تنتهي الذاكرة القصيرة) · /تطوير = طوّر نفسك · /ملف = اخرج ملف المطور")
while True:
    q = input("> ")
    if q == "/جديد": c.end(sid); print("(انتهت المحادثة)"); continue
    if q == "/تطوير": print(c.develop()); continue
    if q == "/ملف": open("dev_file.zip", "wb").write(c.dev_file()); print("dev_file.zip"); continue
    print(c.reply(q, sid))
