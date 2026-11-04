# גרסאות וסביבת הרצה

החלטה משלב 1, 4 בנובמבר 2026.

## בחירה

- Node.js 24.22.2 ו־npm 11.19.1; קובץ .nvmrc, engines, קובץ נעילה ו־images משתמשים בגרסה זו.
- Python 3.13.16 ו־uv 0.13.1; .python-version ו־image תואמים. uv.lock נועל גם תלויות עקיפות.
- Express 5.3.0, React 19.3.1, Vite 8.3.5 ו־FastAPI 0.162.0.
- ESLint 10.14.0 עם תמיכת JSX המובנית ובדיקות hooks; נבחר קו ESLint הנתמך.
- MongoDB 8.0.34 ו־Redis 8.2.11 עבור Compose. nginx 1.30.6 משמש להגשת build ול־proxy.
- JavaScript ESM ו־Python רגיל, ללא build של backend. scikit-learn יתווסף בשלב המודלים ולא נדרש ל־health.

## נימוקים

Node 24 הוא קו LTS; Python 3.13 נבחר כדי להשתמש באותה גרסה זמינה דרך uv ובקונטיינר. הגרסאות אומתו מול מאגרי npm, PyPI ומפיצי images. עדכון גרסאות יבוצע בצורה מפורשת יחד עם נעילות ובדיקות.

במחשב קיימות התקנות ישנות יותר של Node וגרסת Python שונה. לצורך הבדיקות הותקנו גרסאות מבודדות תחת תיקיית העבודה; לא שונתה התקנה מערכתית. Docker אינו מותקן מקומית, ולכן הרצת Compose תיבדק ב־GitHub Actions, והרצת התהליכים תיבדק גם ב־Windows.

## השלכות

בדיקת הקונטיינרים רצה על runner מסוג Ubuntu 22.04 עם kernel מסדרת 6.8. בריצה הראשונה על Ubuntu 24.04, MongoDB עצר בזמן startup בשל kernel שאינו תואם. לפי [תיעוד MongoDB](https://www.mongodb.com/docs/v8.0/release-notes/8.0/), קיימת אי־תאימות בין MongoDB 8.x לבין Linux kernels בטווח 6.19–7.0.13. לא מבטלים את מנגנון ההגנה של MongoDB. בדיקת CI מתעדת את גרסת ה־kernel בפועל; להרצה מקומית נדרש host תואם. יש לבחון מחדש את בחירת ה־runner לפני ש־Ubuntu 22.04 יפסיק להיתמך ב־GitHub Actions.

npm ci ו־uv sync --frozen הם דרכי ההתקנה לשימוש רגיל. שינוי קובץ dependencies מחייב לעדכן את קובץ הנעילה שלו. הרשאות והגדרות localhost ב־Compose אינן הגדרות פריסה ציבורית.

אין הבטחה שה־images חסינים מכל חולשה. בשלב המסירה תיבדק עדכניות הגרסאות ותישקל נעילה ל־digest. Stage 1 אינו התקנת Docker Desktop במחשב המשתמש.

## מקורות

- [Node.js releases](https://nodejs.org/en/about/previous-releases)
- [Vite requirements](https://vite.dev/guide/)
- [uv lock and sync](https://docs.astral.sh/uv/concepts/projects/sync/)
