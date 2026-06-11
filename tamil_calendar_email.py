import requests
from bs4 import BeautifulSoup
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# ─────────────────────────────────────────
# CONFIG — Fill these in
# ─────────────────────────────────────────
SENDER_EMAIL    = "your_gmail@gmail.com"
SENDER_PASSWORD = "your_app_password"       # Gmail App Password (not your login password)
RECEIVER_EMAIL  = "receiver@gmail.com"
RASI            = "MAKARAM"                 # Change to your Rasi if needed
# ─────────────────────────────────────────

BASE_URL = "https://www.tamildailycalendar.com"

def fetch_panel_text(url):
    """Fetch the Tamil text from panel-body > p[align=justify]"""
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        panel = soup.find("div", class_="panel-body")
        if panel:
            p = panel.find("p", attrs={"align": "justify"})
            if p:
                return p.get_text(separator="\n").strip()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return ""

def fetch_calendar_image(day, month, year):
    """Fetch the daily calendar image as bytes"""
    img_url = f"{BASE_URL}/{year}/{day}{month}{year}.jpg"
    try:
        r = requests.get(img_url, timeout=10)
        if r.status_code == 200:
            return r.content, img_url
    except Exception as e:
        print(f"Error fetching image: {e}")
    return None, img_url

def send_email(subject, body_html, image_bytes):
    """Send HTML email with embedded calendar image"""
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL

    # HTML body with embedded image
    html = f"""
    <html><body style="font-family: Arial; font-size: 14px; color: #333;">
        <h2 style="color:#8B0000;">🗓 Tamil Daily Calendar & மகரம் ராசி பலன்</h2>
        <img src="cid:calendar_image" style="max-width:100%; border:1px solid #ccc;"/><br/><br/>
        {body_html}
    </body></html>
    """
    msg.attach(MIMEText(html, "html", "utf-8"))

    if image_bytes:
        img = MIMEImage(image_bytes)
        img.add_header("Content-ID", "<calendar_image>")
        msg.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("✅ Email sent successfully!")

def section(title, text, color="#004080"):
    """Format a section in HTML"""
    if not text:
        return ""
    text_html = text.replace("\n", "<br/>")
    return f"""
    <div style="background:#f0f8ff; border-left:4px solid {color};
                padding:12px; margin:10px 0; border-radius:4px;">
        <h3 style="color:{color}; margin-top:0;">{title}</h3>
        <p style="line-height:1.8;">{text_html}</p>
    </div>
    """

def main():
    now       = datetime.now()
    day       = now.strftime("%d")
    month     = now.strftime("%m")
    year      = now.strftime("%Y")
    weekday   = now.weekday()   # 0=Monday
    monthday  = now.day
    yearday   = now.timetuple().tm_yday

    print(f"Running for {day}-{month}-{year}")

    # ── 1. Always: Daily Rasi Palan ──────────────────────────────
    daily_url  = f"{BASE_URL}/tamil_rasi_palan_today.php?msg=Tamil+Rasi+Palan+Today&&rasi={RASI}"
    daily_text = fetch_panel_text(daily_url)

    body_html  = section("📅 இன்றைய ராசி பலன் (Daily)", daily_text, "#004080")

    # ── 2. Monday: Add Weekly Rasi Palan ─────────────────────────
    if weekday == 0:
        weekly_url  = f"{BASE_URL}/tamil_rasi_palan_weekly.php?msg=Tamil+Rasi+Palan+Weekly&&rasi={RASI}"
        weekly_text = fetch_panel_text(weekly_url)
        body_html  += section("📆 இந்த வார ராசி பலன் (Weekly)", weekly_text, "#006400")

    # ── 3. 1st of month: Add Monthly Rasi Palan ──────────────────
    if monthday == 1:
        monthly_url  = f"{BASE_URL}/tamil_rasi_palan_monthly.php?msg=Tamil+Rasi+Palan+Monthly&&rasi={RASI}"
        monthly_text = fetch_panel_text(monthly_url)
        body_html   += section("🗓 இந்த மாத ராசி பலன் (Monthly)", monthly_text, "#8B4513")

    # ── 4. Jan 1st: Add Yearly Rasi Palan ────────────────────────
    if yearday == 1:
        yearly_url  = f"{BASE_URL}/tamil_rasi_palan_yearly.php?msg=Tamil+Rasi+Palan+Yearly&&rasi={RASI}"
        yearly_text = fetch_panel_text(yearly_url)
        body_html  += section("🎊 இந்த ஆண்டு ராசி பலன் (Yearly)", yearly_text, "#8B0000")

    # ── 5. Always: Calendar Image ─────────────────────────────────
    image_bytes, img_url = fetch_calendar_image(day, month, year)

    # ── 6. Build subject ─────────────────────────────────────────
    extras = []
    if weekday == 0:  extras.append("Weekly")
    if monthday == 1: extras.append("Monthly")
    if yearday == 1:  extras.append("Yearly")
    extra_str = " + " + " + ".join(extras) if extras else ""
    subject = f"🗓 Tamil Calendar{extra_str} | மகரம் ராசி பலன் | {day}-{month}-{year}"

    # ── 7. Send ───────────────────────────────────────────────────
    send_email(subject, body_html, image_bytes)

if __name__ == "__main__":
    main()
