# AI Security Agent

מערכת לבדיקת אבטחת HTTPS ותעודות TLS, עם ממצאים מוסברים ולמידת מכונה לבחינת התרעות שווא.

**מצב נוכחי:** שלב 2 מומש ונבדק מקומית; אימות GitHub Actions בתהליך. קיימים שלד שירותים, חוזי נתונים ומעבדת TLS. סריקות, אחסון ממצאים ומודל ML שייכים לשלבים הבאים.

- [מסמך האפיון המתעדכן](docs/specification.md) — דרישות, המימוש הקיים והיסטוריית כל שלב.
- [הצעת הפרויקט ותוכנית הביצוע](docs/implementation-plan.md)
- [ארכיטקטורה](docs/architecture.md)
- [יומן שלבים ובדיקות](docs/stage-log.md)
- [החלטות סביבת הפיתוח](docs/decisions/0001-runtime-and-local-environment.md)
- [חוזי הנתונים ו־OpenAPI](packages/contracts/README.md)
- [כללי הבדיקה ומדיניות TLS](docs/rules-and-policy.md)
- [מדריך תיוג ממצאים](docs/labeling-guide.md)

## דרישות מוקדמות

Node.js **24.22.2** עם npm **11.19.1**, וכלי uv **0.13.1**. uv יוריד את Python **3.13.16** בעת ההתקנה אם הגרסה אינה זמינה. הגרסאות נעולות ב־.nvmrc, .python-version וקובצי הנעילה.

להרצת קונטיינרים נדרש Docker עם Compose v2 וקונטיינרי Linux. בשלב 1 אפשר להריץ את ארבעת רכיבי היישום גם בלי Docker.

למעבדת שלב 2 נדרש גם OpenSSL 3 ב־PATH, או נתיב אליו במשתנה OPENSSL_BIN. ב־Windows אפשר להשתמש ב־OpenSSL המצורף ל־Git for Windows. הוא משמש להפקת תעודת SHA-1 לבדיקת קובץ מקומית; תלויות Python למעבדה מותקנות עם uv sync.

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

נדרש Linux kernel התואם ל־MongoDB. סביבת הבדיקות משתמשת ב־Ubuntu 22.04 עם kernel מסדרת 6.8; מגבלת התאימות לגרסאות kernel אחרות מתועדת ב־[החלטות הסביבה](docs/decisions/0001-runtime-and-local-environment.md).

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
npm run check:openapi
npm run test:lab
uv run --project services/ml --frozen ruff check --config services/ml/pyproject.toml services/ml tests/fixtures/tls
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

GitHub Actions מפעיל בדיקות קוד, חוזים בשתי השפות, OpenAPI, מעבדת TLS, Python, build, smoke ודפדפן, ובנפרד build והרצה של Compose עם בדיקת כל השירותים. קומיטים שמשנים רק Markdown או docs אינם מפעילים מחדש בדיקות קוד.

## מעבדת TLS

```sh
npm run lab:generate
npm run lab
```

הפקודה הראשונה מייצרת תעודות חדשות בלבד. השנייה מייצרת אותן מחדש ומפעילה 18 מאזינים על 127.0.0.1 בפורטים פנויים; כתובותיהם מודפסות ונשמרות בקובץ endpoints.json בתיקיית generated. יציאה עם Ctrl+C סוגרת אותם. אין צורך לשנות DNS או להתקין CA במערכת ההפעלה.

התעודות נוצרות ביחס למועד ההרצה: תקינות, פגות תוקף, עתידיות, קרובות לפקיעה, שם שגוי, שרשרת חסרה ו־CA פרטי. קיימים גם תרחישי SNI, גרסאות TLS, הפניית HTTP, כותרת HSTS ו־timeout. מפתח חלש וחתימת SHA-1 נבדקים בקבצים בלבד. מפתחות הניסוי ותעודות שנוצרו מוחרגים מ־Git ומ־Docker. [הוראות ומגבלות המעבדה](tests/fixtures/tls/README.md).

## בדיקת זמינות ספקים

```sh
npm run check:providers
```

הפקודה מבצעת שאילתת DNS ל־example.com וקריאת info של SSL Labs. היא אינה מפעילה סריקה ואינה רושמת משתמש. חיבור assessment חי ל־SSL Labs הוא חלק משלב 6 וידרוש רישום מתאים.

## שירותים קיימים

| רכיב | כתובת מקומית | התנהגות |
| --- | --- | --- |
| web | http://127.0.0.1:5173 | דף פתיחה עם מצב חיבור אמיתי |
| api | http://127.0.0.1:3001/health | liveness; scanning=false |
| scanner | http://127.0.0.1:3002/health | liveness; queueConsumer=false |
| ml | http://127.0.0.1:8000/health | liveness; modelLoaded=false |

health תקין מעיד שהתהליך פועל. הוא אינו מעיד שכבר ניתן לסרוק אתר או לקבל הערכת אבטחה.

המסך ו־health ממשיכים לתאר את שלד שלב 1. שלב 2 מוסיף חוזים וכלי בדיקה, ואינו מוסיף פעולות סריקה לממשק.

## מבנה הפרויקט

```text
apps/web/               React and Vite
services/api/           Express API
services/scanner/       Node.js scanner scaffold
services/ml/            Python FastAPI service
packages/runtime/      Shared Node.js service utilities
packages/contracts/    JSON Schema, OpenAPI, examples and rule policy
scripts/               Development, lab, smoke and provider checks
tests/                 Unit, browser and live local TLS tests
tests/fixtures/tls/     Certificate generator and laboratory
docker/                Application images and web proxy
docs/                  Specification, plan and stage history
```

בכל שלב מעדכנים את האפיון ואת יומן השלבים ומעלים קומיט עם הבדיקות שבוצעו. אחרי אימות שלב 2, השלב הבא הוא שלב 3 — יעדים, סריקות, אחסון ותור.
