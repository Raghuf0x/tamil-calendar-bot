import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders

# ─────────────────────────────────────────
# CONFIG — reads from GitHub Secrets
# ─────────────────────────────────────────
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL", "your_gmail@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your_app_password")
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL", "receiver@gmail.com")
RASI            = "MAKARAM"
# ─────────────────────────────────────────

BASE_URL = "https://www.tamildailycalendar.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

def fetch_panel_text(url):
    """Fetch Tamil text from panel-body > p[align=justify]"""
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
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
    """
    Try multiple URL patterns to fetch the calendar image.
    Pattern from HTML inspector: /YYYY/DDMMYYYY.jpg
    """
    candidates = [
        f"{BASE_URL}/{year}/{day}{month}{year}.jpg",
        f"{BASE_URL}/images/{year}/{day}{month}{year}.jpg",
        f"{BASE_URL}/tamil_daily_calendar/{year}/{day}{month}{year}.jpg",
    ]

    session = requests.Session()
    # Warm up session with a homepage visit
    try:
        session.get(BASE_URL + "/tamil_daily_calendar.php", headers=HEADERS, timeout=15)
    except:
        pass

    for img_url in candidates:
        try:
            print(f"🔍 Trying image URL: {img_url}")
            r = session.get(img_url, headers={**HEADERS, "Referer": BASE_URL}, timeout=20)
            print(f"   Status: {r.status_code} | Content-Type: {r.headers.get('Content-Type','?')} | Size: {len(r.content)} bytes")

            if r.status_code == 200 and len(r.content) > 5000:  # valid image is > 5KB
                print(f"✅ Image fetched successfully: {img_url}")
                return r.content, img_url
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("⚠️  All image URL attempts failed — sending email without image")
    return None, candidates[0]

def send_email(subject, body_html, image_bytes, image_filename):
    """Send HTML email with calendar image as both inline + attachment"""
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL

    # ── HTML body ────────────────────────────────────────────────
    if image_bytes:
        img_tag = '<img src="cid:calendar_image" style="max-width:100%; border:1px solid #ccc; border-radius:4px;"/>'
    else:
        img_tag = '<p style="color:red;">⚠️ Calendar image could not be fetched today.</p>'

    html = f"""
    <html><body style="font-family: Arial; font-size: 14px; color: #333; max-width:700px; margin:auto;">
        <h2 style="color:#8B0000; border-bottom:2px solid #8B0000; padding-bottom:8px;">
            🗓 Tamil Daily Calendar &amp; மகரம் ராசி பலன்
        </h2>
        {img_tag}
        <br/><br/>
        {body_html}
        <hr style="margin-top:20px; border-color:#eee;"/>
        <p style="color:#999; font-size:12px;">Source: tamildailycalendar.com</p>
    </body></html>
    """

    # Related part for inline image
    related = MIMEMultipart("related")
    related.attach(MIMEText(html, "html", "utf-8"))

    if image_bytes:
        # Inline embedded image
        img_inline = MIMEImage(image_bytes, _subtype="jpeg")
        img_inline.add_header("Content-ID", "<calendar_image>")
        img_inline.add_header("Content-Disposition", "inline", filename=image_filename)
        related.attach(img_inline)

        # Also attach as downloadable file
        img_attach = MIMEBase("image", "jpeg")
        img_attach.set_payload(image_bytes)
        encoders.encode_base64(img_attach)
        img_attach.add_header("Content-Disposition", "attachment", filename=image_filename)
        msg.attach(img_attach)

    msg.attach(related)

    print(f"📧 Sending email to {RECEIVER_EMAIL}...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("✅ Email sent successfully!")

def section(title, text, color="#004080"):
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
    weekday  = now.weekday()
    monthday = now.day
    yearday  = now.timetuple().tm_yday

    print(f"📅 Running for {day}-{month}-{year} | weekday={weekday} | monthday={monthday} | yearday={yearday}")

    # ── 1. Always: Daily Rasi Palan ──────────────────────────────
    daily_url  = f"{BASE_URL}/tamil_rasi_palan_today.php?msg=Tamil+Rasi+Palan+Today&&rasi={RASI}"
    daily_text = fetch_panel_text(daily_url)
    body_html  = section("📅 இன்றைய ராசி பலன் (Daily)", daily_text, "#004080")

    # ── 2. Monday: Weekly ────────────────────────────────────────
    if weekday == 0:
        print("📆 Monday — fetching Weekly Rasi Palan...")
        weekly_url  = f"{BASE_URL}/tamil_rasi_palan_weekly.php?msg=Tamil+Rasi+Palan+Weekly&&rasi={RASI}"
        weekly_text = fetch_panel_text(weekly_url)
        body_html  += section("📆 இந்த வார ராசி பலன் (Weekly)", weekly_text, "#006400")

    # ── 3. 1st of month: Monthly ─────────────────────────────────
    if monthday == 1:
        print("🗓 1st of month — fetching Monthly Rasi Palan...")
        monthly_url  = f"{BASE_URL}/tamil_rasi_palan_monthly.php?msg=Tamil+Rasi+Palan+Monthly&&rasi={RASI}"
        monthly_text = fetch_panel_text(monthly_url)
        body_html   += section("🗓 இந்த மாத ராசி பலன் (Monthly)", monthly_text, "#8B4513")

    # ── 4. Jan 1st: Yearly ───────────────────────────────────────
    if yearday == 1:
        print("🎊 Jan 1st — fetching Yearly Rasi Palan...")
        yearly_url  = f"{BASE_URL}/tamil_rasi_palan_yearly.php?msg=Tamil+Rasi+Palan+Yearly&&rasi={RASI}"
        yearly_text = fetch_panel_text(yearly_url)
        body_html  += section("🎊 இந்த ஆண்டு ராசி பலன் (Yearly)", yearly_text, "#8B0000")

    # ── 5. Calendar Image ─────────────────────────────────────────
    image_bytes, img_url = fetch_calendar_image(day, month, year)
    image_filename = f"{day}{month}{year}.jpg"

    # ── 6. Subject ────────────────────────────────────────────────
    extras = []
    if weekday == 0:  extras.append("Weekly")
    if monthday == 1: extras.append("Monthly")
    if yearday == 1:  extras.append("Yearly")
    extra_str = " + " + " + ".join(extras) if extras else ""
    subject = f"🗓 Tamil Calendar{extra_str} | மகரம் ராசி பலன் | {day}-{month}-{year}"

    # ── 7. Send ───────────────────────────────────────────────────
    send_email(subject, body_html, image_bytes, image_filename)

if __name__ == "__main__":
    main()
