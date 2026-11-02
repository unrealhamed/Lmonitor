# Lmonitor 

Lmonitor puts a small, click-through bar over your game and a full dashboard in a separate window.
You choose what to show, how it looks and where it sits. Everything is saved automatically.

 Download and install
1. Open **Releases** and download `Lmonitor_Setup_x.y.z.exe`.
2. Run it and follow the wizard (Desktop and Start Menu shortcuts are optional/included).
3. Start **Lmonitor**. Windows asks for administrator rights (needed to read sensors) - choose *Yes*.
4. Uninstall from *Settings > Apps*. The uninstaller asks whether to delete your settings (default: keep them).

> The installer is not code-signed, so Windows SmartScreen or your antivirus may show a warning. Choose *More info > Run anyway* only if you trust the download source.

 What the overlay can show
| Group | Items |

| **FPS** | FPS, average, 1% low, frametime, live frametime graph |
| **GPU** | usage, temperature, power, clock, VRAM used/total |
| **CPU** | usage, temperature, power, clock |
| **RAM** | usage %, used / total, swap |
| **NET** | download and upload speed (MB/s or Mbps) |

Every single item can be switched on or off.

 Colors change with load and temperature
Values turn from white to warning colors automatically:

| Level | Usage (CPU / GPU / RAM / VRAM) | Temperature |
| Normal | below 30 % - white | below 40 °C - white |
| Warm | 30 % and up - yellow | 40 °C and up - yellow |
| High | 50 % and up - red | 60 °C and up - red |
| Critical | 70 % and up - dark red | 75 °C and up - dark red |

In the dashboard, a gauge ring turns red at 90 % and above.

 Customize the overlay
- **Two styles:** *Dark Transparent* and *Liquid Glass* (Windows blur-behind; needs Windows 10 version 1803 or newer, otherwise a translucent dark bar is used).
- **10 backgrounds:** Black, Graphite, Slate, Midnight, Ocean, Forest, Wine, Violet, Ember and *Accent* (follows the app accent).
- **6 label color palettes:** Auto (GPU/CPU brand colors), Mono, Neon, Sunset, Ocean, Candy.
- **Opacity** 40-100 %, **text size** 8-18 pt, **graph size** 50-200 %.
- **Layout:** horizontal or vertical. **Position:** Left, Center, Right or *Custom*.
- **Move with the mouse:** drag the bar anywhere; the position is saved and always kept inside the screen.
- **Drag & drop order:** reorder sections and items.
- **Multi-monitor:** pick the display for the bar; if it is unplugged the bar falls back to the primary display.
- Click-through: the bar never blocks your game input (except while you are moving it).

 Customize the app itself
- **4 app themes:** *Default*, *Night*, *Day* and *Aurora* (violet dusk with a mint glow).
- **7 accent options:** Auto (GPU brand: NVIDIA green, AMD red, otherwise blue), Green, Blue, Violet, Pink, Orange, Teal.
- The window title bar follows the theme (light/dark).

 The window
- **Dashboard:** CPU / RAM / GPU gauges with mini charts, a real-time chart with 1 min / 5 min / 1 hr / 24 hr ranges, hardware info, storage and network.
- **Performance:** live charts (usage, temperatures, network).
- **Hardware:** CPU / GPU, memory, storage, network, sensors and system details (OS, drivers, battery when present).
- **Quick settings panel** on every page: position, layout, text/graph size, opacity, overlay on/off, reset.
- Refresh rate 1 / 2 / 5 s. Live data is read only while the window is open on a live page, to keep the overhead low.
- **Sensor report:** save a text report of all sensors for troubleshooting.
- Tray icon: open the window, show/hide the overlay, save the sensor report, exit.

Requirements and notes
- Windows 10 / 11, 64-bit.
- **CPU temperature and power** need the *PawnIO* driver on many CPUs. The installer bundles PawnIO's official setup; Lmonitor offers to install it on first run.
- **FPS** is captured with the bundled *PresentMon*. Anti-cheat software in some online games may block or dislike overlays and hardware drivers - use at your own risk.
- Settings live in `%APPDATA%\Lmonitor` and survive updates and re-installs.
- Lmonitor has no telemetry: the only web address it contains is the PawnIO download link, opened in your browser if the bundled installer is missing.
- Early release: it has been developed for NVIDIA + Intel and AMD + Intel PCs; some sensors may show *n/a* on other hardware. Bug reports are welcome in *Issues*.

 Credits
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (sensors), [PresentMon](https://github.com/GameTechDev/PresentMon) (FPS), [PawnIO](https://pawnio.eu/) (driver). Please read their licenses before redistributing.

---

Lmonitor یک نوار کوچک و بدون مزاحمت روی بازی شما قرار می‌دهد و یک داشبورد کامل در پنجرهٔ جداگانه دارد.
شما انتخاب می‌کنید چه چیزی نشان داده شود، ظاهرش چطور باشد و کجا قرار بگیرد. همه‌چیز خودکار ذخیره می‌شود.

دانلود و نصب
۱. در بخش **Releases** فایل `Lmonitor_Setup_x.y.z.exe` را دانلود کنید.
۲. اجرا کنید و مراحل نصب را بروید (میان‌بر دسکتاپ و Start Menu ساخته می‌شود).
۳. برنامه را باز کنید. ویندوز دسترسی ادمین می‌خواهد (برای خواندن سنسورها لازم است) - *Yes* را بزنید.
۴. حذف از *Settings > Apps*. هنگام حذف می‌پرسد تنظیمات هم پاک شود یا نه (پیش‌فرض: نگه داشتن).

> فایل نصبی امضای دیجیتال ندارد؛ پس ممکن است SmartScreen یا آنتی‌ویروس هشدار بدهد. فقط اگر به منبع دانلود اعتماد دارید *More info > Run anyway* را بزنید.

اورلی چه چیزهایی نشان می‌دهد
| گروه | موارد |
| **FPS** | FPS، میانگین، 1% Low، فریم‌تایم، نمودار زندهٔ فریم‌تایم |
| **GPU** | مصرف، دما، توان، کلاک، VRAM |
| **CPU** | مصرف، دما، توان، کلاک |
| **RAM** | درصد مصرف، مقدار مصرفی/کل، Swap |
| **NET** | سرعت دانلود و آپلود (MB/s یا Mbps) |

هر مورد را می‌توانید جداگانه روشن یا خاموش کنید.

 تغییر رنگ با بار و دما
مقدارها خودکار از سفید به رنگ‌های هشدار تغییر می‌کنند:

| سطح | مصرف (CPU / GPU / RAM / VRAM) | دما |
| عادی | کمتر از ۳۰٪ - سفید | کمتر از ۴۰ درجه - سفید |
| گرم | از ۳۰٪ - زرد | از ۴۰ درجه - زرد |
| بالا | از ۵۰٪ - قرمز | از ۶۰ درجه - قرمز |
| بحرانی | از ۷۰٪ - قرمز تیره | از ۷۵ درجه - قرمز تیره |

در داشبورد، حلقهٔ گیج از ۹۰٪ به بالا قرمز می‌شود.

 شخصی‌سازی اورلی
- **دو استایل:** *Dark Transparent* و *Liquid Glass* (تاری پشت‌نما در ویندوز؛ به ویندوز ۱۰ نسخهٔ 1803 یا جدیدتر نیاز دارد، وگرنه نوار تیرهٔ نیمه‌شفاف استفاده می‌شود).
- **۱۰ پس‌زمینه:** Black، Graphite، Slate، Midnight، Ocean، Forest، Wine، Violet، Ember و *Accent* (هماهنگ با رنگ تأکید برنامه).
- **۶ پالت رنگ برچسب‌ها:** Auto (رنگ برند GPU/CPU)، Mono، Neon، Sunset، Ocean، Candy.
- **شفافیت** ۴۰ تا ۱۰۰٪، **اندازهٔ متن** ۸ تا ۱۸، **اندازهٔ نمودار** ۵۰ تا ۲۰۰٪.
- **چیدمان:** افقی یا عمودی. **موقعیت:** چپ، وسط، راست یا *Custom*.
- **جابه‌جایی با ماوس:** نوار را هرجا بکشید؛ موقعیت ذخیره می‌شود و همیشه داخل صفحه می‌ماند.
- **ترتیب با Drag & Drop:** بخش‌ها و موارد را جابه‌جا کنید.
- **چندمانیتوره:** نمایشگر دلخواه را انتخاب کنید؛ اگر قطع شود نوار به نمایشگر اصلی برمی‌گردد.
- نوار کلیک را رد می‌کند و جلوی کنترل بازی را نمی‌گیرد (به‌جز زمان جابه‌جایی).

 شخصی‌سازی خود برنامه
- **۴ تم:** *Default*، *Night*، *Day* و *Aurora* (غروب بنفش با درخشش نعنایی).
- **۷ گزینهٔ رنگ تأکید:** Auto (رنگ برند GPU: انویدیا سبز، AMD قرمز، بقیه آبی)، سبز، آبی، بنفش، صورتی، نارنجی، فیروزه‌ای.
- نوار عنوان پنجره هم با تم (روشن/تیره) هماهنگ می‌شود.

پنجرهٔ برنامه
- **Dashboard:** گیج CPU / RAM / GPU با نمودار کوچک، نمودار لحظه‌ای با بازه‌های ۱ دقیقه / ۵ دقیقه / ۱ ساعت / ۲۴ ساعت، اطلاعات سخت‌افزار، فضای ذخیره‌سازی و شبکه.
- **Performance:** نمودارهای زنده (مصرف، دما، شبکه).
- **Hardware:** جزئیات CPU / GPU، حافظه، ذخیره‌سازی، شبکه، سنسورها و سیستم (ویندوز، درایورها، باتری در صورت وجود).
- **پنل تنظیمات سریع** در همهٔ صفحه‌ها: موقعیت، چیدمان، اندازهٔ متن و نمودار، شفافیت، روشن/خاموش اورلی، بازنشانی.
- نرخ به‌روزرسانی ۱ / ۲ / ۵ ثانیه. داده‌های زنده فقط وقتی پنجره روی صفحهٔ زنده باز است خوانده می‌شوند تا مصرف کم بماند.
- **گزارش سنسورها:** ذخیرهٔ یک گزارش متنی از همهٔ سنسورها برای عیب‌یابی.
- آیکون Tray: باز کردن پنجره، نمایش/مخفی کردن اورلی، ذخیرهٔ گزارش سنسورها، خروج.

 نیازمندی‌ها و نکته‌ها
- ویندوز ۱۰ / ۱۱، ۶۴ بیتی.
- **دما و توان CPU** در بسیاری از پردازنده‌ها به درایور *PawnIO* نیاز دارد. نصب‌کنندهٔ رسمی آن همراه برنامه است و Lmonitor در اولین اجرا پیشنهاد نصب می‌دهد.
- **FPS** با *PresentMon* همراه برنامه گرفته می‌شود. ضدتقلب بعضی بازی‌های آنلاین ممکن است اورلی و درایور سخت‌افزار را نپذیرد - مسئولیت استفاده با خودتان است.
- تنظیمات در `%APPDATA%\Lmonitor` ذخیره می‌شود و با آپدیت و نصب مجدد باقی می‌ماند.
- Lmonitor تله‌متری ندارد: تنها آدرس اینترنتی داخل برنامه لینک دانلود PawnIO است که فقط در صورت نبودن نصب‌کنندهٔ همراه، در مرورگر باز می‌شود.
- نسخهٔ اولیه است: روی سیستم‌های انویدیا + اینتل و AMD + اینتل توسعه یافته؛ روی سخت‌افزارهای دیگر ممکن است بعضی سنسورها *n/a* باشند. گزارش باگ را در بخش *Issues* بنویسید.

منابع  قبل از بازتوزیع، مجوز آن‌ها را بخوانید.

[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (سنسورها)، [PresentMon](https://github.com/GameTechDev/PresentMon) (FPS)، [PawnIO](https://pawnio.eu/) . قبل از بازتوزیع، مجوز آن‌ها را بخوانید.



<img width="1226" height="831" alt="Screenshot 2026-11-02 110218" src="https://github.com/user-attachments/assets/9d20c817-f68c-4790-9d1e-950014ae1e0b" />
<img width="1103" height="722" alt="Screenshot 2026-11-02 110235" src="https://github.com/user-attachments/assets/5e3659bb-0ffd-49d4-aa1a-5ff3b9323b8f" />
<img width="1093" height="693" alt="Screenshot 2026-11-02 110245" src="https://github.com/user-attachments/assets/01dcf6b9-35a4-4df8-bf69-c0a661aeb950" />
<img width="1078" height="702" alt="Screenshot 2026-11-02 110301" src="https://github.com/user-attachments/assets/8188f238-2145-487b-8533-f9199cf5dfb9" />
<img width="1077" height="698" alt="Screenshot 2026-11-02 110307" src="https://github.com/user-attachments/assets/6037a5b7-539b-4d08-b1cc-e1cd807c08cb" />
<img width="1085" height="698" alt="Screenshot 2026-11-02 110313" src="https://github.com/user-attachments/assets/af2374a1-2e73-4164-8fba-bd94c2ed346e" />
<img width="1059" height="667" alt="Screenshot 2026-11-02 110328" src="https://github.com/user-attachments/assets/28c14271-00af-4622-815c-e261fdb67e49" />
<img width="1137" height="709" alt="Screenshot 2026-11-02 110333" src="https://github.com/user-attachments/assets/fe0a094f-5181-44e4-9779-d602e9b7f927" />
