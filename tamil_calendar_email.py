import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# ─────────────────────────────────────────
# CONFIG — reads from GitHub Secrets (env vars)
# For local testing, you can hardcode here temporarily
# ─────────────────────────────────────────
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL", "your_gmail@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your_app_password")
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL", "receiver@gmail.com")
RASI            = "MAKARAM"
# ─────────────────────────────────────────

BASE_URL = "https://www.tamildailycalendar.com"

def fetch_panel_text(url):
    """Fetch the Tamil text from panel-body > p[align=justify]"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=15, headers=headers)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.content, "html.parser")
        panel = soup.find("div", class_="panel-body")
        if panel:
            p = panel.find("p", attrs={"align": "justify"})
            if p:
                return p.get_text(separator="\n").strip()
        print(f"⚠️  Could not find panel-body in {url}")
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
    return ""

def fetch_calendar_image(day, month, year):
    """Fetch the daily calendar image as bytes"""
    img_url = f"{BASE_URL}/{year}/{day}{month}{year}.jpg"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(img_url, timeout=15, headers=headers)
        if r.status_code == 200:
            print(f"✅ Calendar image fetched: {img_url}")
            return r.content, img_url
        else:
            print(f"⚠️  Image not found (status {r.status_code}): {img_url}")
    except Exception as e:
        print(f"❌ Error fetching image: {e}")
    return None, img_url

def send_email(subject, body_html, image_bytes):
    """Send HTML email with embedded calendar image"""
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL

    html = f"""
    <html><body style="font-family: Arial; font-size: 14px; color: #333; max-width:700px; margin:auto;">
        <h2 style="color:#8B0000; border-bottom:2px solid #8B0000; padding-bottom:8px;">
            🗓 Tamil Daily Calendar &amp; மகரம் ராசி பலன்
        </h2>
        <img src="cid:calendar_image" style="max-width:100%; border:1px solid #ccc; border-radius:4px;"/><br/><br/>
        {body_html}
        <hr style="margin-top:20px; border-color:#eee;"/>
        <p style="color:#999; font-size:12px;">Source: tamildailycalendar.com</p>
    </body></html>
    """
    msg.attach(MIMEText(html, "html", "utf-8"))

    if image_bytes:
        img = MIMEImage(image_bytes)
        img.add_header("Content-ID", "<calendar_image>")
        img.add_header("Content-Disposition", "inline")
        msg.attach(img)

    print(f"📧 Sending email to {RECEIVER_EMAIL}...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("✅ Email sent successfully!")

def section(title, text, color="#004080"):
    """Format a section block in HTML"""
    if not text:
        return ""
    text_html = text.replace("\n", "<br/>")
    return f"""
    <div style="background:#f0f8ff; border-left:5px solid {color};
                padding:14px 16px; margin:12px 0; border-radius:4px;">
        <h3 style="color:{color}; margin-top:0; margin-bottom:8px;">{title}</h3>
        <p style="line-height:1.9; margin:0;">{text_html}</p>
    </div>
    """

def main():
    now      = datetime.now()
    day      = now.strftime("%d")
    month    = now.strftime("%m")
    year     = now.strftime("%Y")
    weekday  = now.weekday()        # 0 = Monday
    monthday = now.day
    yearday  = now.timetuple().tm_yday

    print(f"📅 Running for {day}-{month}-{year} | weekday={weekday} | monthday={monthday} | yearday={yearday}")

    # ── 1. Always: Daily Rasi Palan ──────────────────────────────
    daily_url  = f"{BASE_URL}/tamil_rasi_palan_today.php?msg=Tamil+Rasi+Palan+Today&&rasi={RASI}"
    daily_text = fetch_panel_text(daily_url)
    body_html  = section("📅 இன்றைய ராசி பலன் (Daily)", daily_text, "#004080")

    # ── 2. Monday: Add Weekly Rasi Palan ─────────────────────────
    if weekday == 0:
        print("📆 Monday — fetching Weekly Rasi Palan...")
        weekly_url  = f"{BASE_URL}/tamil_rasi_palan_weekly.php?msg=Tamil+Rasi+Palan+Weekly&&rasi={RASI}"
        weekly_text = fetch_panel_text(weekly_url)
        body_html  += section("📆 இந்த வார ராசி பலன் (Weekly)", weekly_text, "#006400")

    # ── 3. 1st of month: Add Monthly Rasi Palan ──────────────────
    if monthday == 1:
        print("🗓 1st of month — fetching Monthly Rasi Palan...")
        monthly_url  = f"{BASE_URL}/tamil_rasi_palan_monthly.php?msg=Tamil+Rasi+Palan+Monthly&&rasi={RASI}"
        monthly_text = fetch_panel_text(monthly_url)
        body_html   += section("🗓 இந்த மாத ராசி பலன் (Monthly)", monthly_text, "#8B4513")

    # ── 4. Jan 1st: Add Yearly Rasi Palan ────────────────────────
    if yearday == 1:
        print("🎊 Jan 1st — fetching Yearly Rasi Palan...")
        yearly_url  = f"{BASE_URL}/tamil_rasi_palan_yearly.php?msg=Tamil+Rasi+Palan+Yearly&&rasi={RASI}"
        yearly_text = fetch_panel_text(yearly_url)
        body_html  += section("🎊 இந்த ஆண்டு ராசி பலன் (Yearly)", yearly_text, "#8B0000")

    # ── 5. Always: Calendar Image ─────────────────────────────────
    image_bytes, img_url = fetch_calendar_image(day, month, year)

    # ── 6. Build subject line ─────────────────────────────────────
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
