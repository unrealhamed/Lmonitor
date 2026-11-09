.pragma library

// Persian text of the interface. The key is the English text.
var strings = {
    // ---- pages and navigation
    "Home": "خانه", "Graphs": "نمودارها", "Hardware": "سخت‌افزار", "Overlay": "اورلی",
    "Sessions": "جلسه‌ها", "Diagnostics": "عیب‌یابی", "Optimizer": "بهینه‌ساز", "Storage": "ذخیره‌سازی",
    "Reports": "گزارش‌ها", "Personalize": "شخصی‌سازی", "About": "درباره", "Performance": "عملکرد",
    "MAIN": "اصلی", "GAMING": "بازی", "TOOLS": "ابزارها", "Version": "نسخه", "Version ": "نسخهٔ ",
    "Update available: ": "نسخهٔ جدید: ", "This page could not be loaded": "این صفحه بارگذاری نشد",
    "See the console window.": "جزئیات در پنجرهٔ کنسول است.",

    // ---- status words
    "Optimal": "مطلوب", "Warm": "گرم", "Hot": "داغ", "High load": "بار زیاد", "Low space": "فضای کم",
    "Almost full": "تقریباً پر", "No data": "بدون داده", "OK": "خوب", "Info": "اطلاعات", "Notice": "توجه",
    "Notices": "نکته‌ها", "Warning": "هشدار", "Warnings": "هشدارها", "Unknown": "نامشخص", "Ready": "آماده",
    "Done": "تمام", "Yes": "بله", "No": "خیر", "On": "روشن", "Off": "خاموش", "Show": "نمایش", "Use": "استفاده",

    // ---- home
    "This PC": "این رایانه", "Welcome back": "خوش آمدی", "Gamer": "گیمر", "Temperatures": "دماها",
    "Memory": "حافظهٔ RAM", "Network": "شبکه", "FPS capture": "ثبت FPS", "Capture tool missing": "ابزار ثبت پیدا نشد",
    "Starts with a game": "با شروع بازی فعال می‌شود", "No temperature sensor": "سنسور دما پیدا نشد",
    "No drive data": "اطلاعات درایو نیست", "Utilization": "میزان مصرف", "Celsius": "سلسیوس", "no sensor": "بدون سنسور",
    " of ": " از ", " GB used": " GB مصرف‌شده", " GB free": " GB آزاد", " GB free on ": " GB آزاد در ",
    " free of ": " آزاد از ", "All overlay settings  ›": "همهٔ تنظیمات اورلی  ›",
    "Show the overlay in games": "نمایش اورلی در بازی", "Show only when I press F9": "فقط با فشردن F9 نشان بده",
    "Liquid glass look": "ظاهر شیشه‌ای", "1 min": "۱ دقیقه", "5 min": "۵ دقیقه", "10 min": "۱۰ دقیقه",
    "1 hr": "۱ ساعت", "24 hr": "۲۴ ساعت",

    // ---- graphs
    "Live while this window is open": "زنده تا وقتی این پنجره باز است", "CPU temperature": "دمای CPU",
    "GPU temperature": "دمای GPU", "CPU usage": "مصرف CPU", "GPU usage": "مصرف GPU", "RAM usage": "مصرف RAM",
    "Download": "دانلود", "Upload": "آپلود", "last ": "", "Click to enlarge": "برای بزرگ‌نمایی کلیک کن",
    "No sensor data": "داده‌ای از سنسور نیست", "Fan speed (RPM)": "سرعت فن (RPM)",
    "Click a name to add it to this graph or remove it": "روی هر نام بزن تا به این نمودار اضافه یا از آن حذف شود",
    "No fan speed sensor was found. Fan RPM needs administrator rights, and some laptops do not expose their fans to software. The graph starts when you open this page.": "سنسور سرعت فن پیدا نشد. خواندن دور فن به دسترسی ادمین نیاز دارد و بعضی لپ‌تاپ‌ها فن را در اختیار نرم‌افزار نمی‌گذارند. نمودار از لحظهٔ باز شدن این صفحه شروع می‌شود.",

    // ---- hardware rows
    "Everything about this PC": "همه‌چیز دربارهٔ این رایانه", "CPU / GPU": "CPU / GPU", "Sensors": "سنسورها", "System": "سیستم",
    "Model": "مدل", "Vendor": "سازنده", "Cores": "هسته‌ها", "Threads": "رشته‌ها", "Clock": "کلاک", "Usage": "مصرف",
    "Temperature": "دما", "Power": "توان", "Driver": "درایور", "Fan": "فن", "Fans": "فن‌ها", "Total": "کل", "Used": "مصرف‌شده",
    "Free": "آزاد", "Speed": "سرعت", "Voltage": "ولتاژ", "Battery": "باتری", "Charge": "شارژ", "Health": "سلامت", "Healthy": "سالم",
    "Unhealthy": "ناسالم", "Degradation": "فرسودگی", "Drives": "درایوها", "Drive health": "سلامت درایو", "Interfaces": "کارت‌های شبکه",
    "Motherboard": "مادربرد", "Motherboard sensors": "سنسورهای مادربرد", "Fans and sensors": "فن‌ها و سنسورها", "Memory (RAM)": "حافظه (RAM)",
    "Swap (page file)": "حافظهٔ مجازی", "Administrator": "دسترسی ادمین", "PawnIO driver": "درایور PawnIO", "Publisher": "ناشر",
    "Cooler": "خنک‌کننده", "Not detected": "شناسایی نشد", "Not set": "تنظیم نشده", "none connected": "چیزی وصل نیست",
    "none detected": "چیزی شناسایی نشد", "not provided by this drive": "این درایو ارائه نمی‌کند", "fully charged": "کاملاً شارژ",
    "on battery": "با باتری", "percentage used": "درصد مصرف‌شده", "power cycle": "دفعات روشن شدن", "power on": "ساعت کارکرد",
    "run as Administrator": "با دسترسی ادمین اجرا کن", "driver or board not supported": "درایور یا برد پشتیبانی نمی‌شود",
    "Average": "میانگین", "Frametime": "زمان فریم", "Graph": "نمودار", "Swap": "مجازی", "Temp": "دما",

    // ---- overlay page
    "Game bar": "نوار بازی", "Lmonitor overlay": "اورلی Lmonitor", "Live preview": "پیش‌نمایش زنده", "Appearance": "ظاهر",
    "Position and layout": "موقعیت و چیدمان", "What the bar shows": "نوار چه چیزی نشان دهد", "When is the bar visible": "نوار چه زمانی دیده شود",
    "Density": "تراکم", "Compact": "جمع‌وجور", "Balanced": "متعادل", "Detailed": "کامل", "Custom": "سفارشی",
    "Compact: FPS and usage only.": "جمع‌وجور: فقط FPS و مصرف.", "Balanced: usage, temperatures and FPS lows.": "متعادل: مصرف، دماها و افت FPS.",
    "Detailed: everything, plus the graph.": "کامل: همه‌چیز به‌همراه نمودار.", "Custom: you picked the metrics yourself (What the bar shows).": "سفارشی: موارد را خودت انتخاب کرده‌ای (بخش «نوار چه چیزی نشان دهد»).",
    "BACKGROUND": "پس‌زمینه", "LABELS": "برچسب‌ها", "VALUES": "مقدارها", "VALUE COLOR": "رنگ مقدار", "OPACITY": "شفافیت", "TEXT SIZE": "اندازهٔ متن",
    "SHOW ON": "نمایش در", "STAY ON SCREEN AFTER F9": "ماندن روی صفحه بعد از F9", "Bold": "ضخیم", "Dark transparent": "تیره و شفاف", "Always visible": "همیشه نمایش", "Gaming": "بازی", "Drive ": "درایو ", "Run as administrator for CPU temperature": "برای دمای CPU با دسترسی ادمین اجرا کن", "CPU sensor not available": "سنسور CPU در دسترس نیست", "Regular": "معمولی", "Liquid glass": "شیشه‌ای", "Center": "وسط",
    "Left": "چپ", "Right": "راست", "Top": "بالا", "Bottom": "پایین", "Horizontal": "افقی", "Vertical": "عمودی", "Primary (Windows)": "اصلی (ویندوز)",
    "F9 slides it in": "با F9 وارد می‌شود", "Always": "همیشه", "Move with mouse": "جابه‌جایی با ماوس",
    "Drag it anywhere - the position is saved": "هر جا خواستی بکش؛ موقعیت ذخیره می‌شود", "Drag the bar, then press Done": "نوار را بکش و بعد «تمام» را بزن",
    "Glass blurs the game behind the bar (visible in the game, not in this preview).": "حالت شیشه‌ای پشت نوار را تار می‌کند (در بازی دیده می‌شود، نه در این پیش‌نمایش).",
    "Windows blur is not available - a translucent bar is used.": "تاری ویندوز در دسترس نیست؛ نوار نیمه‌شفاف استفاده می‌شود.", "Reset overlay settings": "بازنشانی تنظیمات اورلی",

    // ---- sessions
    "Saved on this PC only": "فقط روی همین رایانه ذخیره می‌شود", "Record games": "ضبط بازی‌ها", "  ● recording": "  ● در حال ضبط", "  ·  1% low ": "  ·  1% پایین ",
    " FPS avg": " میانگین FPS", "FPS n/a": "FPS نامشخص", "Delete this session": "حذف این جلسه", "Delete it?": "حذف شود؟",
    "No sessions yet. Play a game while Lmonitor is running - sessions of one minute or longer are saved here with FPS, 1% lows, temperatures and what slowed the game down.": "هنوز جلسه‌ای نیست. وقتی Lmonitor باز است بازی کن؛ جلسه‌های یک دقیقه یا بیشتر با FPS، افت‌ها، دماها و دلیل کند شدن بازی اینجا ذخیره می‌شوند.",
    "Average FPS": "میانگین FPS", "Background apps": "برنامه‌های پس‌زمینه", "Frame-rate drops": "افت نرخ فریم", "Heavy background apps during the game": "برنامه‌های سنگین پس‌زمینه هنگام بازی",
    "Load": "بار", "No heavy background apps were seen": "برنامهٔ سنگینی در پس‌زمینه دیده نشد", "Select a session in the list above": "یک جلسه را از فهرست بالا انتخاب کن",
    "Temperature and clocks": "دما و کلاک", "Frame rate (from PresentMon frame times)": "نرخ فریم (از زمان فریم‌های PresentMon)", "clock dip": "افت کلاک", "hot, no drop": "داغ، بدون افت", "none seen": "دیده نشد",
    "possible throttle": "احتمال افت کارایی از گرما", "Shown only when the sensors prove it. 'Unknown' = a sensor was missing, not 'fine'.": "فقط وقتی نشان داده می‌شود که سنسورها ثابتش کنند. «نامشخص» یعنی سنسور نبوده، نه اینکه مشکلی نیست.",

    // ---- diagnostics
    "Health score": "امتیاز سلامت", "out of 100 - ": "از ۱۰۰ - ", " checks answered": " بررسی پاسخ داده شد", "Scan now": "اسکن کن", "Re-scan": "اسکن دوباره", "Scanning…": "در حال اسکن…", "Scanning ": "در حال اسکن ",
    "Last scan: ": "آخرین اسکن: ", "No scan yet": "هنوز اسکن نشده", "WHAT WAS SEEN": "چه چیزی دیده شد", "WHY IT MATTERS": "چرا مهم است", "WHAT YOU CAN DO": "چه کاری می‌توانی بکنی", "Fix in ": "رفع در ",
    "Press “Scan now”. The scan only reads Windows settings - it changes nothing.": "روی «اسکن کن» بزن. اسکن فقط تنظیمات ویندوز را می‌خواند و چیزی را تغییر نمی‌دهد.",
    "Run a scan in Diagnostics first.": "اول در بخش عیب‌یابی یک اسکن انجام بده.",

    // ---- optimizer
    "Every change can be undone": "هر تغییری قابل برگشت است", "Quick presets": "تنظیمات آماده", "Power plan": "طرح مصرف انرژی", "Startup programs": "برنامه‌های شروع ویندوز", "Windows game settings": "تنظیمات بازی ویندوز", "History": "تاریخچه",
    "Nothing changed yet.": "هنوز چیزی تغییر نکرده.", "Undo": "برگرداندن", "Apply": "اعمال", "Apply ": "اعمال ", "Are you sure?": "مطمئنی؟", "Change it?": "تغییر کند؟", "Switch plan?": "طرح عوض شود؟", " change(s)?": " تغییر؟",
    "Already set - nothing to change.": "از قبل تنظیم است؛ چیزی برای تغییر نیست.", "No startup programs found.": "برنامهٔ شروعی پیدا نشد.", "Windows did not list its power plans.": "ویندوز فهرست طرح‌های انرژی را نداد.", "Working…": "در حال انجام…",
    "Switching one off only stops it from starting with Windows. Nothing is deleted.": "خاموش کردن فقط جلوی اجرا با ویندوز را می‌گیرد و چیزی حذف نمی‌شود.",
    "Disable": "غیرفعال کن", "Disabled": "غیرفعال", "Enable": "فعال کن", "Enabled": "فعال", "Turn off": "خاموش کن", "Turn on": "روشن کن", "Game Mode": "حالت بازی", "Background game recording": "ضبط پس‌زمینهٔ بازی",
    "Not set (Windows default)": "تنظیم نشده (پیش‌فرض ویندوز)", "Lets Windows favour the game you play": "ویندوز به بازی در حال اجرا اولویت می‌دهد", "Stops Windows from recording your game in the background": "جلوی ضبط پس‌زمینهٔ بازی توسط ویندوز را می‌گیرد",
    "Everything is already set.": "همه‌چیز از قبل تنظیم است.", "You can undo this in History.": "می‌توانی از تاریخچه برگردانی.", "Back to how it was.": "به حالت قبل برگشت.", "Action failed": "انجام نشد", "This change cannot be undone.": "این تغییر قابل برگشت نیست.",
    "Windows did not keep the change - it was put back.": "ویندوز تغییر را نگه نداشت و برگردانده شد.", "Windows did not switch - the old plan was kept.": "ویندوز تغییر نداد و طرح قبلی ماند.", "Windows did not list that plan.": "ویندوز آن طرح را فهرست نکرد.", "Startup item not found": "مورد شروع پیدا نشد",
    "It is no longer in the list.": "دیگر در فهرست نیست.", "Something went wrong. Nothing was changed that could not be undone - see error.log.": "مشکلی پیش آمد. چیزی که قابل برگشت نباشد تغییر نکرد؛ فایل error.log را ببین.", "partly applied": "نیمه‌کاره اعمال شد",
    "High performance is not offered by this PC, so it is skipped.": "این رایانه طرح High performance ندارد، پس رد شد.",

    // ---- storage
    "Find what takes space and clean safely": "ببین چه چیزی فضا گرفته و امن پاکش کن", "Cache and temp folders": "پوشه‌های کش و موقت", "Big folders and large files": "پوشه‌ها و فایل‌های بزرگ", "BIGGEST FOLDERS": "بزرگ‌ترین پوشه‌ها", "LARGE FILES": "فایل‌های بزرگ",
    "Find big folders": "پیدا کردن پوشه‌های بزرگ", "Find large files (500 MB+)": "پیدا کردن فایل‌های بزرگ (بیش از ۵۰۰ مگابایت)", "No file of 500 MB or more was found.": "فایلی با حجم ۵۰۰ مگابایت یا بیشتر پیدا نشد.", "Open folder": "باز کردن پوشه", "Rebuild": "ساخت دوباره", "Recycle": "به سطل بازیافت", "Refresh": "تازه‌سازی",
    "Clean selected (": "پاک‌سازی انتخاب‌شده‌ها (", "Can free about ": "حدود این مقدار آزاد می‌شود: ", "Delete old files?": "فایل‌های قدیمی حذف شوند؟", "Move to Recycle Bin?": "به سطل بازیافت برود؟", " old\n(": " قدیمی\n(", " total)": " کل)",
    "Measuring only. Windows, Program Files and system folders are never offered for deletion.": "فقط اندازه‌گیری است. ویندوز، Program Files و پوشه‌های سیستمی هرگز برای حذف پیشنهاد نمی‌شوند.", "Only files older than a day are removed. This cannot be undone; the folders are rebuilt as needed.": "فقط فایل‌های قدیمی‌تر از یک روز حذف می‌شوند. برگشت‌پذیر نیست و پوشه‌ها در صورت نیاز دوباره ساخته می‌شوند.",
    "Chrome cache": "کش Chrome", "Edge cache": "کش Edge", "Crash dumps": "فایل‌های خطای برنامه", "DirectX shader cache": "کش سایه‌زن DirectX", "NVIDIA OpenGL cache": "کش OpenGL انویدیا", "NVIDIA shader cache": "کش سایه‌زن انویدیا", "Windows temp folder": "پوشهٔ موقت ویندوز", "Your temp folder": "پوشهٔ موقت شما",
    "Only useful when debugging a crash": "فقط برای بررسی خطای برنامه مفید است", "Pages load slower once; sign-ins are kept": "صفحه‌ها یک بار کندتر باز می‌شوند؛ ورود به حساب‌ها می‌ماند", "Rebuilt by games": "بازی‌ها دوباره می‌سازند", "Rebuilt by games; first launch may stutter a little": "بازی‌ها دوباره می‌سازند؛ اجرای اول ممکن است کمی لگ بزند", "Windows recreates them as needed": "ویندوز در صورت نیاز دوباره می‌سازد",
    "Nothing was selected.": "چیزی انتخاب نشده.", "Not deleted": "حذف نشد", "Opened in Explorer": "در Explorer باز شد", "Recycle Bin": "سطل بازیافت", "That path is no longer there.": "این مسیر دیگر وجود ندارد.", "This file is not one Lmonitor may delete.": "Lmonitor اجازهٔ حذف این فایل را ندارد.", "Windows did not move the file - it was left where it is.": "ویندوز فایل را منتقل نکرد و سر جایش ماند.", "Something went wrong; nothing was deleted - see error.log.": "مشکلی پیش آمد و چیزی حذف نشد؛ فایل error.log را ببین.",

    // ---- reports, personalize, about
    "Save HTML report": "ذخیرهٔ گزارش HTML", "Save JSON": "ذخیرهٔ JSON", "What the report contains": "گزارش شامل چیست",
    "Look and feel": "ظاهر برنامه", "App theme": "پوستهٔ برنامه", "Accent color": "رنگ اصلی", "Language": "زبان", "Auto = the theme's own color.": "خودکار = رنگ خود پوسته.",
    "Default": "پیش‌فرض", "Auto": "خودکار", "Night": "شب", "Day": "روز", "Black": "مشکی", "White": "سفید", "Blue": "آبی", "Green": "سبز", "Orange": "نارنجی", "Pink": "صورتی", "Violet": "بنفش", "Cyan": "فیروزه‌ای", "Teal": "سبزآبی", "Lime": "لیمویی", "Amber": "کهربایی",
    "Neutral dark, accent follows your GPU": "تیرهٔ خنثی، رنگ اصلی بر اساس GPU", "Deep blue-black, easy on the eyes": "آبی‌مشکی عمیق، راحت برای چشم", "Bright and clean for daylight": "روشن و تمیز برای روز", "Violet dusk with a mint glow (my own design)": "غروب بنفش با درخشش نعنایی",
    "Gaming overlay and system monitor": "اورلی بازی و مانیتور سیستم", "Lmonitor is a gaming overlay and system monitor for Windows. It shows FPS, CPU, GPU, RAM and network readings on top of your game, and keeps a record of your play sessions.": "Lmonitor یک اورلی بازی و مانیتور سیستم برای ویندوز است. FPS و وضعیت CPU، GPU، RAM و شبکه را روی بازی نشان می‌دهد و جلسه‌های بازی‌ات را ثبت می‌کند.",
    "Made by a new developer named unrealhamed.": "ساخته‌شده توسط توسعه‌دهنده‌ای تازه‌کار به نام unrealhamed.", "A new version is available": "نسخهٔ جدید آماده است", "You have the latest version": "آخرین نسخه را داری", "Check for updates": "بررسی به‌روزرسانی", "Checking...": "در حال بررسی...", "Could not check: ": "بررسی نشد: ", "Download and install ": "دانلود و نصب ", "Downloading...": "در حال دانلود...", "Installing - Lmonitor will restart": "در حال نصب؛ Lmonitor دوباره باز می‌شود", "Try it now": "همین حالا امتحان کن", "not found": "پیدا نشد", "none yet": "هنوز چیزی نیست"
};
