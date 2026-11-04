# AI Security Agent

מערכת לבדיקת אבטחת HTTPS ותעודות TLS, עם ממצאים מוסברים ולמידת מכונה לבחינת התרעות שווא.

**מצב נוכחי:** שלב 1 — שלד השירותים והסביבה נכתבו; האימות בתהליך. סריקות, אחסון ממצאים ומודל ML עדיין לא מומשו.

- [מסמך האפיון המתעדכן](docs/specification.md) — דרישות, המימוש הקיים והיסטוריית כל שלב.
- [הצעת הפרויקט ותוכנית הביצוע](docs/implementation-plan.md)
- [ארכיטקטורה](docs/architecture.md)
- [יומן שלבים ובדיקות](docs/stage-log.md)
- [החלטות סביבת הפיתוח](docs/decisions/0001-runtime-and-local-environment.md)

## דרישות מוקדמות

Node.js **24.22.2** עם npm **11.19.1**, וכלי uv **0.13.1**. uv יוריד את Python **3.13.16** בעת ההתקנה אם הגרסה אינה זמינה. הגרסאות נעולות ב־.nvmrc, .python-version וקובצי הנעילה.

להרצת קונטיינרים נדרש Docker עם Compose v2 וקונטיינרי Linux. בשלב 1 אפשר להריץ את ארבעת רכיבי היישום גם בלי Docker.

## הרצה מקומית

מתיקיית המאגר:

```sh
npm ci
uv sync --project services/ml --frozen
npm run dev
```

פתחו [http://127.0.0.1:5173](http://127.0.0.1:5173). הפקודה מפעילה יחד את web, api, scanner ו־ml. סיום עם Ctrl+C סוגר את התהליכים. לא נדרשים MongoDB ו־Redis להרצה המקומית בשלב זה; עדיין אין שמירת נתונים או עיבוד תור.

ברירות המחדל פועלות בלי קובץ סביבה. לשינוי פורטים אפשר להעתיק את .env.example ל־.env ולערוך אותו. אל תכניסו פרטים אמיתיים לקובץ הדוגמה ואל תעלו .env למאגר.

ב־PowerShell, אם מדיניות הרצת scripts חוסמת npm.ps1, השתמשו ב־npm.cmd במקום npm.

## הרצה עם Docker

```sh
docker compose up --build --wait
```

אותה כתובת מקומית תציג את היישום. Compose מפעיל גם MongoDB ו־Redis עם volumes עמידים, אך הם עדיין אינם מחוברים לפעולות עסקיות. הפורטים החשופים מוגבלים ל־127.0.0.1.

לעצירה תוך שמירת הנתונים:

```sh
docker compose down
```

## בדיקות

לאחר התקנת התלויות:

```sh
npm run lint
npm test
uv run --project services/ml --frozen ruff check services/ml
uv run --project services/ml --frozen pytest services/ml
npm run build
npm run smoke
npx playwright install chromium
npm run test:web
```

smoke מפעיל את השירותים, בודק health ואת ה־build של React, מאמת את ההעברה ל־API ומסיים את התהליכים. הריצו אותו כאשר סביבת dev או Compose אינה תופסת את הפורטים. בדיקות הדפדפן מפעילות סביבת בדיקה משלהן.

כאשר Compose כבר פועל:

```sh
npm run smoke:stack
```

GitHub Actions מפעיל בדיקות קוד, Python, build, smoke ודפדפן, ובנפרד build והרצה של Compose עם בדיקת כל השירותים. קומיטים שמשנים רק Markdown או docs אינם מפעילים מחדש בדיקות קוד.

## בדיקת זמינות ספקים

```sh
npm run check:providers
```

הפקודה מבצעת שאילתת DNS ל־example.com וקריאת info של SSL Labs. היא אינה מפעילה סריקה ואינה רושמת משתמש. חיבור assessment חי ל־SSL Labs הוא חלק משלב 6 וידרוש רישום מתאים.

## שירותים בשלב 1

| רכיב | כתובת מקומית | התנהגות |
| --- | --- | --- |
| web | http://127.0.0.1:5173 | דף פתיחה עם מצב חיבור אמיתי |
| api | http://127.0.0.1:3001/health | liveness; scanning=false |
| scanner | http://127.0.0.1:3002/health | liveness; queueConsumer=false |
| ml | http://127.0.0.1:8000/health | liveness; modelLoaded=false |

health תקין מעיד שהתהליך פועל. הוא אינו מעיד שכבר ניתן לסרוק אתר או לקבל הערכת אבטחה.

## מבנה הפרויקט

```text
apps/web/               React and Vite
services/api/           Express API
services/scanner/       Node.js scanner scaffold
services/ml/            Python FastAPI service
packages/runtime/      Shared Node.js service utilities
packages/contracts/    Contracts reserved for stage 2
scripts/               Development, smoke and provider checks
tests/                 Node.js and browser tests
docker/                Application images and web proxy
docs/                  Specification, plan and stage history
```

בכל שלב מעדכנים את האפיון ואת יומן השלבים ומעלים קומיט עם הבדיקות שבוצעו. השלב הבא הוא שלב 2 — חוזים ומעבדת TLS.
